# Tilbudssystem i Notion

Systemet ligger på den private Notion-side **Tilbud** og består af fire databaser:

| Database | Indhold |
|---|---|
| **Kunder** | Kunder med kontaktperson, adresse og CVR |
| **Prisliste** | Varekatalog og timer med kostpris, listepris, avance og salgspris |
| **Tilbud** | Ét tilbud pr. række: kunde, beskrivelse, datoer, rabat, moms og total |
| **Tilbudslinjer** | Varer og timer på et tilbud (antal, enhedspris, linjesum) |

Tilbudsnummeret er årstal + løbenummer, fx `2026-003`. Løbenummeret fortsætter på tværs af år og nulstilles ikke ved årsskifte.

## Sådan laver du et tilbud

1. Opret en ny række i **Tilbud**. Giv det en titel.
2. Vælg **Kunde** (fra Kunder), skriv en **Beskrivelse** og vælg **Betalingsbetingelser** og datoer. Længere tekst, fx forudsætninger, skriver du på selve tilbudssiden. Den kommer med på PDF'en.
3. Tilføj **linjer** i tabellen på tilbudssiden: vælg en **Vare** fra Prisliste (udstyr eller en timepost som *Montørtime*), skriv **Antal** (fx antal timer) og eventuelt en beskrivelse. Prisen hentes fra prislisten. Skriv **Enhedspris manuel** for at bruge en anden pris på linjen.
4. Sæt **Rabat %** hvis der gives rabat. Subtotal, moms og total regnes automatisk.
5. Lav PDF'en (se nedenfor), send den til kunden, og sæt **Status** til *Sendt* og **Opfølgning** til en dato.

## PDF til kunden

`lav_tilbud_pdf.py` henter tilbuddet, kunden og linjerne fra Notion og laver en PDF med dine firmaoplysninger. Udfyld `firma.json` først (adresse, CVR, telefon, mail og eventuelt en logo-adresse).

**Fra GitHub:** gå til **Actions → Lav tilbuds-PDF → Run workflow**, skriv tilbudsnummeret (fx `2026-003`), og hent PDF'en under *Artifacts* på kørslen. Kræver hemmelighederne `NOTION_TOKEN` og `NOTION_TILBUD_ID` (databasens ID, `3df4444f431d48c0ad320e064fe83f45`).

**Lokalt:**

```bash
export NOTION_TOKEN=... NOTION_TILBUD_ID=3df4444f431d48c0ad320e064fe83f45
python3 tilbud/lav_tilbud_pdf.py --nr 2026-003 --ud pdf
```

Scriptet kræver Chrome eller Chromium (findes på GitHubs servere). Totalerne regnes efter og sammenlignes med Notions tal, og en forskel vises som advarsel.

## Prisliste: to måder at fylde den på

### 1. Manuel CSV-import

I Notion: åbn Prisliste → `···` → **Merge with CSV**. Secpro-filen har semikolon som skilletegn og danske decimaler, så åbn den i et regneark og gem som kommasepareret CSV med disse kolonner, før du importerer:

`Varenavn, Varenr, EAN, Producent, Produkttype, Listepris, Kostpris, Lagerstatus, Lager antal, Link, Opdateret hos leverandør`

Kostpris er filens "Din nettopris ekskl. moms". Det er nemmere at bruge scriptet nedenfor, som gør det hele selv.

### 2. Automatisk opdatering med `sync_prisliste.py`

Scriptet henter leverandørens CSV, opretter nye varer, opdaterer priser og lagerstatus og sætter varer, der er forsvundet fra filen, til inaktive. Det rører ikke din Avance %, Salgspris manuel eller Enhed.

**Opsætning (en gang):**
1. Opret en intern integration på <https://www.notion.so/profile/integrations> og kopiér dens token.
2. Åbn siden **Tilbud** i Notion → `···` → **Connections** → tilføj integrationen. Så får den adgang til Prisliste.
3. I GitHub-repoet: **Settings → Secrets and variables → Actions**. Opret disse hemmeligheder:
   - `NOTION_TOKEN`: integrationens token.
   - `NOTION_PRISLISTE_ID`: databasens ID `0e7ac0f74e084ffa97b5ee8c37a70408`.
   - `PRISFIL_URL`: adressen på leverandørens prisfil. Den indeholder en privat nøgle, så den må ikke ligge i koden eller i en commit.
4. Valgfrit, under **Variables**: `STANDARD_AVANCE` (fx `30`), som sættes på nye varer.

Workflowet kører hverdage tidligt om morgenen og kan startes manuelt under fanen **Actions**.

**Kør lokalt:**

```bash
# Kun læse og tælle, uden at røre Notion
python3 tilbud/sync_prisliste.py --fil prisfil.csv --tør

# Live-kørsel
export NOTION_TOKEN=... NOTION_PRISLISTE_ID=... PRISFIL_URL=...
python3 tilbud/sync_prisliste.py
```

## Salgspris

`Salgspris` beregnes sådan:
1. Hvis **Salgspris manuel** er udfyldt, bruges den.
2. Ellers, hvis **Avance %** er udfyldt: `Kostpris × (1 + Avance/100)`.
3. Ellers bruges **Listepris**.
