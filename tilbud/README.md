# Tilbudssystem i Notion

Systemet ligger på den private Notion-side **Tilbud** og består af tre databaser:

| Database | Indhold |
|---|---|
| **Prisliste** | Varekatalog med kostpris, listepris, avance og salgspris |
| **Tilbud** | Ét tilbud pr. række: nummer, status, datoer, rabat, moms og total |
| **Tilbudslinjer** | Varer og timer på et tilbud (antal, enhedspris, linjesum) |

Tilbudsnumre vises som `2026-1`, `2026-2` osv. Notion kan ikke udfylde med nuller foran. Ved årsskifte ændrer du præfikset på **Tilbudsnr.** til det nye år. Tælleren fortsætter, den nulstilles ikke.

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
