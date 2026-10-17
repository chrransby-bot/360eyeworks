# Second brain i Notion (PARA, dansk)

Denne mappe indeholder 9 CSV-filer til import i Notion og en guide til resten af opsætningen. Filerne har eksempeldata. Slet eller overskriv dem, når du har dine egne.

## Antagelser

Du svarede ikke på alle afklarende spørgsmål, så jeg har valgt standarder. Ret dem frit:

- **Områder:** Virksomhed, Økonomi, Sundhed, Familie, Læring, Hjem
- **Vaner (i Dagbog):** Motion, Læsning, Planlagt dagen, Sovet 7+ timer, Skærmfri aften
- **Virksomhed:** 360eyeworks sælger, servicerer og installerer tyverialarmer, adgangskontrol og videoovervågning og laver midlertidig overvågning på festivaler. Kunderne Frode Laursen (Unilock, Ajax, Hikvision, Milestone, kontakt Jacob Nicolaisen), Heartland og Copenhell er lagt ind. Kontaktpersoner, datoer og tjenester er tomme, indtil de bliver udfyldt.

## Filer

| Fil | Database i Notion |
|---|---|
| `01-omraader.csv` | Områder |
| `02-projekter.csv` | Projekter |
| `03-opgaver.csv` | Opgaver |
| `04-ressourcer-noter.csv` | Ressourcer / Noter |
| `05-kunder-kontakter.csv` | Kunder & kontakter |
| `06-dagbog.csv` | Dagbog |
| `07-indbakke.csv` | Indbakke |
| `08-maal.csv` | Mål |
| `09-oekonomi.csv` | Økonomi |

## Trin 1: Opret en forside

1. Opret en ny side i Notion kaldet **Second Brain**. Alt det følgende ligger under den.
2. Opret en underside kaldet **Hjem**. Den bygger du til sidst.

## Trin 2: Importér CSV-filerne

1. I venstre sidebjælke: **Import** (nederst) → **CSV**.
2. Vælg én fil ad gangen. Notion laver en ny database for hver.
3. Flyt hver database ind under siden **Second Brain** og omdøb den (fx "Projekter" i stedet for filnavnet).

Notion gætter ikke kolonnetyperne, så de fleste kommer ind som tekst. Næste trin retter det.

## Trin 3: Ret egenskabstyper

Klik på kolonneoverskriften → **Edit property** → **Type**. Brug denne tabel:

| Database | Egenskab | Skal være |
|---|---|---|
| Projekter | Status | Status (Planlagt, Aktiv, Færdig) |
| Projekter | Deadline | Date |
| Opgaver | Status | Status (Ikke startet, I gang, Færdig) |
| Opgaver | Dato | Date |
| Opgaver | Prioritet | Select (Høj, Mellem, Lav) |
| Ressourcer / Noter | Type | Select (Note, Mødenote, Bog, Artikel, Link) |
| Ressourcer / Noter | Tags | Multi-select |
| Ressourcer / Noter | Dato | Date |
| Kunder & kontakter | Kundetype | Select (Fast kunde, Festival, Privat, Andet) |
| Kunder & kontakter | Tjenester | Multi-select (Tyverialarm, Adgangskontrol, Videoovervågning, Midlertidig overvågning, Service) |
| Kunder & kontakter | Systemer | Tekst (installeret udstyr og platforme, fx Unilock, Ajax, Hikvision, Milestone) |
| Kunder & kontakter | Status | Select (Lead, Aktiv kunde, Pause, Afsluttet) |
| Projekter | Tjeneste | Multi-select (samme værdier som Tjenester) |
| Kunder & kontakter | Mail | Email |
| Kunder & kontakter | Telefon | Phone |
| Kunder & kontakter | Seneste kontakt, Næste opfølgning | Date |
| Dagbog | Dato | Date |
| Dagbog | Humør, Energi | Select (1-5) |
| Dagbog | Motion, Læsning, Planlagt dagen, Sovet 7+ timer, Skærmfri aften | Checkbox. Sæt flueben på rækker, hvor der står "Ja" |
| Indbakke | Type | Select (Idé, Opgave, Link, Note) |
| Indbakke | Oprettet | Created time (opretter en ny, og du kan slette den gamle) |
| Indbakke | Behandlet | Checkbox |
| Mål | Kvartal | Select |
| Mål | Status | Status (Aktiv, Opnået, Droppet) |
| Økonomi | Dato | Date |
| Økonomi | Beløb | Number (format: Danske kroner) |
| Økonomi | Type | Select (Indtægt, Udgift) |
| Økonomi | Betalt | Checkbox |

## Trin 4: Lav relationerne

Relationer er det, der gør det til en second brain. Metoden er den samme hver gang:

1. Klik på tekstkolonnen (fx **Område** i Projekter) → **Edit property** → **Type: Relation**.
2. Vælg måldatabasen (fx Områder).
3. Slå **Show on Områder** til, så der også kommer en bagudrelation.

Notion matcher teksten mod titlerne i måldatabasen. Eksemplerne herfra matcher, så de linkes automatisk.

| Fra | Egenskab | Til |
|---|---|---|
| Projekter | Område | Områder |
| Projekter | Kunde | Kunder & kontakter |
| Projekter | Mål | Mål |
| Opgaver | Projekt | Projekter |
| Ressourcer / Noter | Projekt | Projekter |
| Ressourcer / Noter | Område | Områder |
| Mål | Område | Områder |
| Økonomi | Område | Områder |
| Økonomi | Kunde | Kunder & kontakter |

**Rollups (valgfrit, men nyttigt):**
- I **Projekter**: tilføj **Fremdrift** som Rollup over Opgaver → egenskab Status → *Percent per group* → Færdig.
- I **Mål**: tilføj **Fremdrift** som Rollup over Projekter → Status → *Percent per group* → Færdig.
- I **Kunder & kontakter**: tilføj **Omsætning** som Rollup over Økonomi → Beløb → *Sum*.

## Trin 5: Opret views

Opret disse views med **+** ved siden af visningsfanerne:

- **Opgaver:** *I dag* (filter: Dato = i dag, Status ≠ Færdig), *Denne uge* (Dato i denne uge), *Kalender*.
- **Projekter:** *Aktive* (Status = Aktiv), *Tavle* grupperet efter Status.
- **Kunder & kontakter:** *Opfølgning* (Næste opfølgning er før eller lig med i dag).
- **Indbakke:** *Ubehandlet* (Behandlet = ikke afkrydset).
- **Ressourcer / Noter:** galleri-view grupperet efter Type.
- **Dagbog:** *Kalender* efter Dato.

## Trin 6: Skabeloner

Tilføj via **New ▾ → New template** i databasen:

- **Dagbog, daglig:** overskrifterne *Taknemmelig for*, *Dagens 3 vigtigste*, *Hvad lærte jeg?*
- **Mødenote (Ressourcer / Noter):** *Deltagere*, *Dagsorden*, *Beslutninger*, *Næste handlinger*. Sæt Type = Mødenote.
- **Ugentlig review:** punkterne i afsnittet "Rytmer" nedenfor. Gem den i Ressourcer / Noter med Type = Note.

## Trin 7: Byg Hjem-siden

På siden **Hjem**, brug `/linked view of database` og vælg view-navnet:

1. **Øverst, to kolonner:** *I dag* (Opgaver) til venstre, *Kalender* (Opgaver) til højre.
2. **Midten:** *Aktive projekter* (Projekter) og *Opfølgning* (Kunder & kontakter).
3. **Under det:** *Aktive mål* (Mål), og en lille tabel over *Dagbog* for de seneste 7 dage med vaner.
4. **Nederst:** *Seneste noter* (Ressourcer / Noter, sorteret efter Dato faldende, vis 5) og *Ubehandlet* (Indbakke).
5. Tilføj en knap (`/button`) med **Ny i indbakke**, som opretter en ny række i Indbakke.

Sæt Hjem som favorit (stjerne øverst) og træk den øverst i sidebjælken.

## Trin 8: Mobil-indsamling

1. Installer Notion-appen og log ind.
2. Tilføj **Notion-widget** på hjemmeskærmen og peg den på Indbakke.
3. Brug deleknappen i andre apps (browser m.m.) → **Notion** → vælg Indbakke.
4. Aktivér Notion-genvejen til hurtig note, hvis din telefon har den.

## Rytmer

**Dagligt (5-15 min)**
1. Tøm Indbakke: flyt til Opgaver, Ressourcer, Projekter eller slet. Sæt Behandlet = ✔.
2. Vælg dagens 3 vigtigste opgaver og sæt dato = i dag.
3. Udfyld Dagbog med vaner og kort refleksion.

**Ugentligt (30 min)**
1. Gennemgå Projekter: opdatér status og deadlines.
2. Gennemgå Kunder & kontakter: tag de opfølgninger, der er forfaldne.
3. Planlæg næste uge i Opgaver.
4. Skriv en kort ugentlig review.

**Månedligt**
1. Gennemgå Mål og Økonomi (indtægter mod udgifter, ubetalte fakturaer).
2. Arkivér afsluttede projekter (sæt Status = Færdig, så de forsvinder fra Aktive).
3. Ryd op i tags i Ressourcer.

## Tips til at holde det i live

- Start småt. Du behøver ikke udfylde alle databaser fra dag ét. Brug Indbakke, Opgaver og Projekter i en uge, og tilføj resten løbende.
- Opret aldrig nye sider uden for en database. Alt skal hænge sammen.
- Slet eksempeldata, når du har dine egne.
