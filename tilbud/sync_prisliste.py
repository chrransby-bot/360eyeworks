#!/usr/bin/env python3
"""Opdater Notion-databasen "Prisliste" fra en leverandørs CSV-prisfil (fx Secpro).

Filen hentes fra PRISFIL_URL, eller læses lokalt med --fil. Varer matches på
Producent + Varenr. Nye varer oprettes, ændrede varer opdateres, og varer der
ikke længere står i filen sættes til Aktiv = nej, hvis de kom fra Secpro (de
slettes aldrig, og varer du har oprettet selv røres ikke).

Felter som du selv vedligeholder (Avance %, Salgspris manuel, Enhed og en
Kategori du har rettet) overskrives aldrig.

Miljøvariabler:
  NOTION_TOKEN          Notion-integrationens token (kun til live-kørsel)
  NOTION_PRISLISTE_ID   ID på databasen Prisliste
  PRISFIL_URL           Adresse på CSV-filen (kan indeholde en privat nøgle)
  STANDARD_AVANCE       Valgfri. Avance % på nye varer, fx 30

Kør uden at røre Notion:  python3 sync_prisliste.py --fil prisfil.csv --tør
"""
import argparse
import csv
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

# Nøgleord i leverandørens Type -> Kategori i Prisliste. Første match vinder.
KATEGORIER = [
    ("Video", ["kamera", "nvr", "dvr", "optager", "videoovervåg", "cctv", "monitor", "ir-belysning", "skærmbeslag"]),
    ("Adgangskontrol", ["adgang", "kortlæser", "dørtelefon", "dørcontroller", "lås", "intercom", "rfid",
                        "dørstation", "exit-knap", "el-slutblik", "dørlukker", "kort & brikker", "tastatur"]),
    ("Alarm", ["detektor", "sirene", "alarm", "central", "sensor", "perimeter", "panic", "laserhegn"]),
]


def tal(tekst):
    """Dansk tal ('2302,93', '1.234,50') -> float, eller None."""
    tekst = (tekst or "").strip().replace(".", "").replace(",", ".")
    try:
        return float(tekst)
    except ValueError:
        return None


def kategori(produkttype):
    t = (produkttype or "").lower()
    for navn, ord_ in KATEGORIER:
        if any(o in t for o in ord_):
            return navn
    return None


def hent_csv(fil, url):
    if fil:
        with open(fil, "rb") as f:
            data = f.read()
    else:
        if not url:
            sys.exit("Angiv PRISFIL_URL eller --fil")
        with urllib.request.urlopen(url, timeout=120) as r:
            data = r.read()
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"), newline=""), delimiter=";"))


def vare_fra_række(r):
    return {
        "Varenavn": r["Varenavn"].strip(),
        "Varenr": r["Varenr"].strip(),
        "EAN": r["EAN"].strip(),
        "Producent": r["Producent"].strip(),
        "Produkttype": r["Type"].strip(),
        "Listepris": tal(r["Listepris ekskl. moms"]),
        "Kostpris": tal(r["Din nettopris ekskl. moms"]),
        "Lagerstatus": r["Lagerstatus"].strip(),
        "Lager antal": tal(r["Lager antal"]),
        "Link": r["Link"].strip() or None,
        "Opdateret hos leverandør": r["Opdateret"].strip(),
    }


def tekst(v):
    return {"rich_text": [{"text": {"content": v}}] if v else []}


def egenskaber(v, ny, standard_avance):
    p = {
        "Varenavn": {"title": [{"text": {"content": v["Varenavn"]}}]},
        "Varenr": tekst(v["Varenr"]),
        "EAN": tekst(v["EAN"]),
        "Producent": {"select": {"name": v["Producent"]} if v["Producent"] else None},
        "Produkttype": tekst(v["Produkttype"]),
        "Listepris": {"number": v["Listepris"]},
        "Kostpris": {"number": v["Kostpris"]},
        "Lagerstatus": {"select": {"name": v["Lagerstatus"]} if v["Lagerstatus"] else None},
        "Lager antal": {"number": v["Lager antal"]},
        "Link": {"url": v["Link"]},
        "Opdateret hos leverandør": tekst(v["Opdateret hos leverandør"]),
        "Kilde": {"select": {"name": "Secpro"}},
        "Aktiv": {"checkbox": True},
    }
    if ny:
        p["Kategori"] = {"select": {"name": kategori(v["Produkttype"]) or "Andet"}}
        if standard_avance is not None:
            p["Avance %"] = {"number": standard_avance}
    return p


class Notion:
    def __init__(self, token):
        self.token = token
        self.sidst = 0.0

    def kald(self, metode, sti, krop=None):
        for forsøg in range(5):
            pause = 0.35 - (time.time() - self.sidst)  # ca. 3 kald i sekundet
            if pause > 0:
                time.sleep(pause)
            self.sidst = time.time()
            req = urllib.request.Request(
                API + sti,
                method=metode,
                data=json.dumps(krop).encode() if krop is not None else None,
                headers={
                    "Authorization": "Bearer " + self.token,
                    "Notion-Version": NOTION_VERSION,
                    "Content-Type": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 502, 503, 504) and forsøg < 4:
                    time.sleep(2 ** forsøg)
                    continue
                sys.exit(f"Notion {e.code} på {metode} {sti}: {e.read().decode()[:300]}")

    def eksisterende(self, db):
        """Alle sider i Prisliste: (Producent, Varenr) -> (side-id, aktiv, pris, lager)."""
        fundet, cursor = {}, None
        while True:
            svar = self.kald("POST", f"/databases/{db}/query", {"page_size": 100, **({"start_cursor": cursor} if cursor else {})})
            for s in svar["results"]:
                e = s["properties"]
                varenr = "".join(t["plain_text"] for t in e["Varenr"]["rich_text"])
                prod = (e["Producent"]["select"] or {}).get("name", "")
                fundet[(prod, varenr)] = {
                    "id": s["id"],
                    "aktiv": e["Aktiv"]["checkbox"],
                    "kost": e["Kostpris"]["number"],
                    "liste": e["Listepris"]["number"],
                    "lager": e["Lagerstatus"]["select"] and e["Lagerstatus"]["select"]["name"],
                    "antal": e["Lager antal"]["number"],
                    "opd": "".join(t["plain_text"] for t in e["Opdateret hos leverandør"]["rich_text"]),
                    "navn": "".join(t["plain_text"] for t in e["Varenavn"]["title"]),
                    "kilde": (e["Kilde"]["select"] or {}).get("name"),
                }
            if not svar["has_more"]:
                return fundet
            cursor = svar["next_cursor"]


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    a.add_argument("--fil", help="læs CSV lokalt i stedet for at hente PRISFIL_URL")
    a.add_argument("--tør", action="store_true", help="vis kun hvad der ville ske, uden at røre Notion")
    args = a.parse_args()

    rækker = hent_csv(args.fil, os.environ.get("PRISFIL_URL"))
    varer = {}
    for r in rækker:
        v = vare_fra_række(r)
        if v["Varenr"] and v["Varenavn"]:
            varer[(v["Producent"], v["Varenr"])] = v
    ukategoriseret = sum(1 for v in varer.values() if not kategori(v["Produkttype"]))
    print(f"CSV: {len(rækker)} rækker, {len(varer)} varer, {ukategoriseret} uden automatisk kategori")

    if args.tør:
        return

    token, db = os.environ.get("NOTION_TOKEN"), os.environ.get("NOTION_PRISLISTE_ID")
    if not token or not db:
        sys.exit("NOTION_TOKEN og NOTION_PRISLISTE_ID skal være sat")
    avance = os.environ.get("STANDARD_AVANCE")
    avance = float(avance.replace(",", ".")) if avance else None

    notion = Notion(token)
    nu = notion.eksisterende(db)
    print(f"Notion: {len(nu)} varer i Prisliste")

    nye = ændret = deaktiveret = uændret = 0
    for nøgle, v in varer.items():
        side = nu.get(nøgle)
        if not side:
            notion.kald("POST", "/pages", {"parent": {"database_id": db}, "properties": egenskaber(v, True, avance)})
            nye += 1
        elif (not side["aktiv"] or side["kost"] != v["Kostpris"] or side["liste"] != v["Listepris"]
              or side["lager"] != v["Lagerstatus"] or side["antal"] != v["Lager antal"]
              or side["opd"] != v["Opdateret hos leverandør"] or side["navn"] != v["Varenavn"]):
            notion.kald("PATCH", f"/pages/{side['id']}", {"properties": egenskaber(v, False, None)})
            ændret += 1
        else:
            uændret += 1
    for nøgle, side in nu.items():
        if nøgle not in varer and side["aktiv"] and side["kilde"] == "Secpro":
            notion.kald("PATCH", f"/pages/{side['id']}", {"properties": {"Aktiv": {"checkbox": False}}})
            deaktiveret += 1
    print(f"Nye: {nye}, opdateret: {ændret}, uændret: {uændret}, deaktiveret: {deaktiveret}")


if __name__ == "__main__":
    main()
