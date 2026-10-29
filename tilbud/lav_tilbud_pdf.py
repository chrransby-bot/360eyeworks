#!/usr/bin/env python3
"""Lav en PDF med et tilbud fra Notion, klar til at sende til kunden.

Tilbuddet, kunden og linjerne hentes fra Notion (Tilbud, Kunder, Tilbudslinjer).
Firmaoplysninger læses fra firma.json ved siden af scriptet. PDF'en tegnes som
HTML og udskrives med Chrome/Chromium, så der ikke skal installeres noget.

Eksempler:
  export NOTION_TOKEN=...  NOTION_TILBUD_ID=<id på databasen Tilbud>
  python3 lav_tilbud_pdf.py --nr 2026-003
  python3 lav_tilbud_pdf.py --side https://www.notion.so/...      # direkte på siden
  python3 lav_tilbud_pdf.py --json eksempel.json                  # uden Notion
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import date

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"
MAPPE = os.path.dirname(os.path.abspath(__file__))
MÅNEDER = ["januar", "februar", "marts", "april", "maj", "juni", "juli", "august",
           "september", "oktober", "november", "december"]


# --- Notion --------------------------------------------------------------------------------

class Notion:
    def __init__(self, token):
        self.token, self.sidst = token, 0.0

    def kald(self, metode, sti, krop=None):
        for forsøg in range(5):
            pause = 0.35 - (time.time() - self.sidst)
            if pause > 0:
                time.sleep(pause)
            self.sidst = time.time()
            req = urllib.request.Request(
                API + sti, method=metode,
                data=json.dumps(krop).encode() if krop is not None else None,
                headers={"Authorization": "Bearer " + self.token, "Notion-Version": NOTION_VERSION,
                         "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504) and forsøg < 4:
                    time.sleep(2 ** forsøg)
                    continue
                sys.exit(f"Notion {e.code} på {metode} {sti}: {e.read().decode()[:300]}")

    def side(self, id_):
        return self.kald("GET", f"/pages/{id_}")

    def børn(self, id_):
        ud, cursor = [], None
        while True:
            sti = f"/blocks/{id_}/children?page_size=100" + (f"&start_cursor={cursor}" if cursor else "")
            svar = self.kald("GET", sti)
            ud += svar["results"]
            if not svar["has_more"]:
                return ud
            cursor = svar["next_cursor"]

    def relation(self, side, navn):
        """Alle ID'er i en relation. Notion sender højst 25 med på siden, resten hentes her."""
        egenskab = side["properties"][navn]
        if not egenskab.get("has_more"):
            return [r["id"] for r in egenskab["relation"]]
        ud, cursor = [], None
        while True:
            sti = f"/pages/{side['id']}/properties/{egenskab['id']}?page_size=100"
            svar = self.kald("GET", sti + (f"&start_cursor={cursor}" if cursor else ""))
            ud += [r["relation"]["id"] for r in svar["results"]]
            if not svar.get("has_more"):
                return ud
            cursor = svar["next_cursor"]


def tekst(egenskab):
    """Almindelig tekst fra en title- eller rich_text-egenskab."""
    dele = egenskab.get("title") or egenskab.get("rich_text") or []
    return "".join(d["plain_text"] for d in dele).strip()


def tal(egenskab):
    """Tal fra number, formula eller rollup. None hvis tomt."""
    t = egenskab["type"]
    v = egenskab[t]
    if t == "number":
        return v
    if t in ("formula", "rollup") and v and v["type"] == "number":
        return v["number"]
    return None


def valg(egenskab):
    t = egenskab["type"]
    v = egenskab[t]
    if t in ("select", "status"):
        return v["name"] if v else ""
    if t == "rollup" and v and v["type"] == "array":
        navne = []
        for e in v["array"]:
            s = e.get("select")
            if s:
                navne.append(s["name"])
        return ", ".join(dict.fromkeys(navne))
    return ""


def dato(egenskab):
    v = egenskab["date"]
    return v["start"][:10] if v else ""


def hent_tilbud(notion, args):
    if args.side:
        side_id = re.sub(r"[^0-9a-f]", "", args.side.split("?")[0].split("-")[-1].lower())[-32:]
        t = notion.side(side_id)
    else:
        db = os.environ.get("NOTION_TILBUD_ID")
        if not db:
            sys.exit("NOTION_TILBUD_ID skal være sat (eller brug --side)")
        m = re.fullmatch(r"(?:\d{4}-)?0*(\d+)", args.nr.strip())
        if not m:
            sys.exit(f"Kunne ikke læse tilbudsnummeret '{args.nr}'. Brug fx 2026-003")
        svar = notion.kald("POST", f"/databases/{db}/query",
                           {"filter": {"property": "Løbenr.", "unique_id": {"equals": int(m.group(1))}}})
        if not svar["results"]:
            sys.exit(f"Fandt intet tilbud med nummer {args.nr}")
        t = svar["results"][0]
    p = t["properties"]

    kunde = {}
    rel = p["Kunde"]["relation"]
    if rel:
        k = notion.side(rel[0]["id"])["properties"]
        kunde = {"navn": tekst(k["Navn"]), "adresse": tekst(k["Adresse"]), "postnr_by": tekst(k["Postnr. og by"]),
                 "cvr": tekst(k["CVR"]), "kontaktperson": tekst(k["Kontaktperson"]), "mail": k["Mail"]["email"] or ""}

    linjer = []
    for linje_id in notion.relation(t, "Linjer"):
        l = notion.side(linje_id)["properties"]
        vare = ""
        if l["Vare"]["relation"]:
            vare = tekst(notion.side(l["Vare"]["relation"][0]["id"])["properties"]["Varenavn"])
        linjer.append({"tekst": tekst(l["Beskrivelse"]), "vare": vare, "antal": tal(l["Antal"]) or 0,
                       "enhed": valg(l["Enhed"]), "enhedspris": tal(l["Enhedspris"]) or 0,
                       "sum": tal(l["Linjesum"])})

    noter = []
    for b in notion.børn(t["id"]):
        typ = b["type"]
        if typ in ("paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"):
            tx = "".join(d["plain_text"] for d in b[typ]["rich_text"]).strip()
            if tx:
                noter.append({"type": typ, "tekst": tx})

    return {
        "nr": tekst({"rich_text": [{"plain_text": p["Tilbudsnr."]["formula"]["string"] or ""}]}),
        "titel": tekst(p["Titel"]), "dato": dato(p["Dato"]), "gyldig_til": dato(p["Gyldig til"]),
        "beskrivelse": tekst(p["Beskrivelse"]), "betaling": valg(p["Betalingsbetingelser"]),
        "kontakt": tekst(p["Kontaktperson"]) or kunde.get("kontaktperson", ""),
        "rabat_pct": tal(p["Rabat %"]) or 0, "kunde": kunde, "linjer": linjer, "noter": noter,
        "sub": tal(p["Subtotal"]), "rabat": tal(p["Rabat beløb"]), "efter": tal(p["Subtotal efter rabat"]),
        "moms": tal(p["Moms 25%"]), "total": tal(p["Total inkl. moms"]),
    }


# --- Beregning og formatering --------------------------------------------------------------

def beregn(t):
    """Regn totalerne selv og sammenlign med Notions tal. Returnerer advarsler."""
    for l in t["linjer"]:
        l["_sum"] = round(l["antal"] * l["enhedspris"], 2)
    sub = round(sum(l["_sum"] for l in t["linjer"]), 2)
    rabat = round(sub * (t["rabat_pct"] or 0) / 100, 2)
    efter = round(sub - rabat, 2)
    moms = round(efter * 0.25, 2)
    egne = {"sub": sub, "rabat": rabat, "efter": efter, "moms": moms, "total": round(efter + moms, 2)}
    advarsler = []
    for l in t["linjer"]:
        if l.get("sum") is not None and abs(l["sum"] - l["_sum"]) > 0.01:
            advarsler.append(f"linjen '{l['tekst'] or l['vare']}': Notion siger {l['sum']}, men antal × pris giver {l['_sum']}")
    for k, v in egne.items():
        if t.get(k) is None:
            t[k] = v
        elif abs(t[k] - v) > 0.01:
            advarsler.append(f"{k}: Notion siger {t[k]}, men linjerne giver {v}")
    return advarsler


def kr(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") + " kr."


def antal(v):
    return (f"{v:g}").replace(".", ",")


FLERTAL = {"time": "timer", "dag": "dage", "måned": "måneder"}


def enhed(navn, mængde):
    return FLERTAL.get(navn, navn) if mængde != 1 else navn


def dansk_dato(d):
    if not d:
        return ""
    å, m, dag = d.split("-")
    return f"{int(dag)}. {MÅNEDER[int(m) - 1]} {å}"


def e(s):
    return html.escape(s or "").replace("\n", "<br>")


# --- HTML og PDF ---------------------------------------------------------------------------

CSS = """
@page { size: A4; margin: 18mm 16mm 22mm 16mm; }
* { box-sizing: border-box; }
body { font-family: "Helvetica Neue", Arial, sans-serif; font-size: 10pt; color: #1d2433; line-height: 1.45; margin: 0; }
h1 { font-size: 22pt; margin: 0 0 2px; letter-spacing: -0.3px; }
h2 { font-size: 11pt; margin: 22px 0 6px; text-transform: uppercase; letter-spacing: .6px; color: #5b6578; }
.top { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 3px solid #0b5fff; padding-bottom: 14px; }
.firma { text-align: right; font-size: 9pt; color: #4a5568; }
.firma b { font-size: 12pt; color: #1d2433; }
.logo { max-height: 46px; margin-bottom: 6px; }
.meta { display: flex; gap: 28px; margin-top: 18px; }
.meta > div { flex: 1; }
.meta .label { font-size: 8pt; text-transform: uppercase; letter-spacing: .6px; color: #5b6578; }
.titel { font-size: 14pt; font-weight: 600; margin: 22px 0 4px; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; }
th { text-align: left; font-size: 8pt; text-transform: uppercase; letter-spacing: .6px; color: #5b6578; border-bottom: 1.5px solid #1d2433; padding: 6px 8px; }
td { padding: 8px; border-bottom: 1px solid #e3e7ee; vertical-align: top; }
tr { page-break-inside: avoid; }
.r { text-align: right; white-space: nowrap; }
.sub { color: #5b6578; font-size: 8.5pt; }
.totaler { margin-left: auto; width: 62%; margin-top: 14px; page-break-inside: avoid; }
.totaler td { border: 0; padding: 3px 8px; }
.totaler .total td { border-top: 2px solid #1d2433; font-weight: 700; font-size: 12pt; padding-top: 8px; }
.note p, .note li { margin: 3px 0; }
.note h3 { font-size: 10.5pt; margin: 12px 0 2px; }
.vilkår { font-size: 8.5pt; color: #4a5568; border-top: 1px solid #e3e7ee; margin-top: 22px; padding-top: 10px; page-break-inside: avoid; }
.fod { position: fixed; bottom: 0; left: 0; right: 0; font-size: 8pt; color: #7a8497; text-align: center; border-top: 1px solid #e3e7ee; padding-top: 6px; }
"""


def lav_html(t, f):
    k = t["kunde"]
    kunde_html = "<br>".join(e(x) for x in [k.get("navn"), k.get("adresse"), k.get("postnr_by"),
                                              ("CVR " + k["cvr"]) if k.get("cvr") else ""] if x)
    række = []
    for l in t["linjer"]:
        navn = l["tekst"] or l["vare"]
        under = f'<div class="sub">{e(l["vare"])}</div>' if l["tekst"] and l["vare"] and l["vare"] != l["tekst"] else ""
        række.append(f'<tr><td>{e(navn)}{under}</td><td class="r">{antal(l["antal"])} {e(enhed(l["enhed"], l["antal"]))}</td>'
                     f'<td class="r">{kr(l["enhedspris"])}</td><td class="r">{kr(l["_sum"])}</td></tr>')
    rabat_række = ""
    if t["rabat"]:
        rabat_række = f'<tr><td>Rabat ({antal(t["rabat_pct"])} %)</td><td class="r">−{kr(t["rabat"])}</td></tr>'
    noter = ""
    if t["noter"]:
        dele = []
        for n in t["noter"]:
            if n["type"].startswith("heading"):
                dele.append(f"<h3>{e(n['tekst'])}</h3>")
            elif "list_item" in n["type"]:
                dele.append(f"<p>• {e(n['tekst'])}</p>")
            else:
                dele.append(f"<p>{e(n['tekst'])}</p>")
        noter = '<div class="note">' + "".join(dele) + "</div>"
    logo = f'<img class="logo" src="{e(f["logo"])}"><br>' if f.get("logo") else ""
    fod = " · ".join(x for x in [f.get("navn"), f.get("adresse"), f.get("postnr_by"),
                                 ("CVR " + f["cvr"]) if f.get("cvr") else "", f.get("telefon"), f.get("mail"),
                                 f.get("web")] if x)
    vilkår = ""
    if f.get("vilkår"):
        vilkår = f'<div class="vilkår">{e(f["vilkår"])}</div>'
    return f"""<!doctype html><html lang="da"><head><meta charset="utf-8"><title>Tilbud {e(t['nr'])}</title>
<style>{CSS}</style></head><body>
<div class="top">
  <div><h1>Tilbud</h1><div class="sub">Nr. {e(t['nr'])}</div></div>
  <div class="firma">{logo}<b>{e(f.get('navn'))}</b><br>{e(f.get('adresse'))}<br>{e(f.get('postnr_by'))}<br>
    {e(f.get('telefon'))}{' · ' if f.get('telefon') and f.get('mail') else ''}{e(f.get('mail'))}</div>
</div>
<div class="meta">
  <div><div class="label">Til</div>{kunde_html}</div>
  <div><div class="label">Att.</div>{e(t['kontakt']) or '&nbsp;'}</div>
  <div><div class="label">Dato</div>{dansk_dato(t['dato'])}
       <div class="label" style="margin-top:8px">Gyldigt til</div>{dansk_dato(t['gyldig_til'])}</div>
</div>
<div class="titel">{e(t['titel'])}</div>
<div>{e(t['beskrivelse'])}</div>
<h2>Specifikation</h2>
<table><thead><tr><th>Beskrivelse</th><th class="r">Antal</th><th class="r">Pris</th><th class="r">Beløb</th></tr></thead>
<tbody>{''.join(række)}</tbody></table>
<table class="totaler">
  <tr><td>Subtotal</td><td class="r">{kr(t['sub'])}</td></tr>{rabat_række}
  <tr><td>I alt ekskl. moms</td><td class="r">{kr(t['efter'])}</td></tr>
  <tr><td>Moms 25 %</td><td class="r">{kr(t['moms'])}</td></tr>
  <tr class="total"><td>Total inkl. moms</td><td class="r">{kr(t['total'])}</td></tr>
</table>
{('<h2>Betaling</h2><div>' + e(t['betaling']) + '</div>') if t['betaling'] else ''}
{('<h2>Bemærkninger</h2>' + noter) if noter else ''}
{vilkår}
<div class="fod">{e(fod)}</div>
</body></html>"""


def find_chrome():
    if os.environ.get("CHROME"):
        return os.environ["CHROME"]
    for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        if shutil.which(n):
            return shutil.which(n)
    import glob
    fund = sorted(glob.glob("/opt/pw-browsers/chromium*/chrome-linux*/chrome"))
    if fund:
        return fund[-1]
    sys.exit("Fandt ikke Chrome/Chromium. Sæt miljøvariablen CHROME til programmet.")


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = a.add_mutually_exclusive_group(required=True)
    g.add_argument("--nr", help="tilbudsnummer, fx 2026-003")
    g.add_argument("--side", help="Notion-adresse eller ID på tilbudssiden")
    g.add_argument("--json", help="læs tilbuddet fra en JSON-fil i stedet for Notion")
    a.add_argument("--firma", default=os.path.join(MAPPE, "firma.json"))
    a.add_argument("--ud", default=".", help="mappe til PDF'en (standard: nuværende)")
    args = a.parse_args()

    with open(args.firma, encoding="utf-8") as fh:
        firma = json.load(fh)
    if args.json:
        with open(args.json, encoding="utf-8") as fh:
            t = json.load(fh)
    else:
        token = os.environ.get("NOTION_TOKEN")
        if not token:
            sys.exit("NOTION_TOKEN skal være sat")
        t = hent_tilbud(Notion(token), args)

    # I GitHub Actions bliver ::warning:: vist øverst på kørslen i stedet for at gemme sig i loggen
    forstavelse = "::warning::" if os.environ.get("GITHUB_ACTIONS") else "ADVARSEL: "
    for w in beregn(t):
        print(forstavelse + w, file=sys.stderr)
    mangler = [k for k, v in firma.items() if isinstance(v, str) and v.startswith("UDFYLD")]
    if mangler:
        print("ADVARSEL: udfyld firma.json: " + ", ".join(mangler), file=sys.stderr)

    os.makedirs(args.ud, exist_ok=True)
    navn = re.sub(r"[^\w.-]+", "_", f"Tilbud_{t['nr']}_{t['kunde'].get('navn', '')}").strip("_")
    pdf = os.path.abspath(os.path.join(args.ud, navn + ".pdf"))
    with tempfile.TemporaryDirectory() as tmp:
        fil = os.path.join(tmp, "tilbud.html")
        with open(fil, "w", encoding="utf-8") as fh:
            fh.write(lav_html(t, {k: v for k, v in firma.items() if not str(v).startswith("UDFYLD")}))
        cmd = [find_chrome(), "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
               f"--print-to-pdf={pdf}", "file://" + fil]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(pdf):
            sys.exit("Chrome kunne ikke lave PDF'en:\n" + r.stderr[-500:])
    print(pdf)


if __name__ == "__main__":
    main()
