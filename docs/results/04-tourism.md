# Example 4 — Tourism, beyond the registry

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> Find in Eurostat a dataset on nights spent at tourist accommodation by region. Which five NUTS2 regions of Spain and Italy had the most nights in the latest year available? Tell me which filters you used.

## Tool calls

**1. `search_datasets(query="nights spent tourist accommodation NUTS", limit=10)`**

```
tour_occ_nin2 | Nights spent at tourist accommodation establishments by NUTS 3 region | 1990–2025
tour_occ_nin3 | Nights spent at tourist accommodation establishments by NUTS 3 region (from 2020 onwards) | 2020–2025
tour_occ_nin2m | Nights spent at tourist accommodation establishments by month and NUTS 2 region (from 2020 onwards) | 2020–2025
tour_occ_nin2dc | Nights spent at tourist accommodation establishments by degree of urbanisation and coastal/non-coastal area and NUTS 2 region | 2012–2025
```

**2. `search_datasets(query="nights spent tourist accommodation NUTS 2 region", limit=10)`**

```
tour_occ_nin2 | Nights spent at tourist accommodation establishments by NUTS 3 region | 1990–2025
tour_occ_nin3 | Nights spent at tourist accommodation establishments by NUTS 3 region (from 2020 onwards) | 2020–2025
tour_occ_nin2m | Nights spent at tourist accommodation establishments by month and NUTS 2 region (from 2020 onwards) | 2020–2025
tour_occ_nin2dc | Nights spent at tourist accommodation establishments by degree of urbanisation and coastal/non-coastal area and NUTS 2 region | 2012–2025
```

**3. `search_datasets(query="tour_occ nights accommodation NUTS 2 annual", limit=15)`**

```
Aucun dataset ne contient tous les termes de 'tour_occ nights accommodation NUTS 2 annual' ; résultats contenant au moins l'un d'eux :
tour_occ_nin2 | Nights spent at tourist accommodation establishments by NUTS 3 region | 1990–2025
tour_occ_ninat | Nights spent at tourist accommodation establishments | 1990–2025
tour_occ_nin3 | Nights spent at tourist accommodation establishments by NUTS 3 region (from 2020 onwards) | 2020–2025
tour_occ_nin2m | Nights spent at tourist accommodation establishments by month and NUTS 2 region (from 2020 onwards) | 2020–2025
enps_tour_occ_ninat | Nights spent at tourism accommodation establishments - ENP-South countries | 2005–2024
tour_occ_nim | Nights spent at tourist accommodation establishments - monthly data | 1990-01–2026-05
tour_occ_nin2dc | Nights spent at tourist accommodation establishments by degree of urbanisation and coastal/non-coastal area and NUTS 2 region | 2012–2025
tour_occ_ninc | Nights spent at tourist accommodation establishments for selected cities (from 2020 onwards) | 2020–2025
tour_occ_ninraw | Nights spent at tourist accommodation establishments  by country of origin of the tourist | 1990–2025
tour_occ_ninatdc | Nights spent at tourist accommodation establishments by degree of urbanisation and coastal/non-coastal area | 2012–2025
tour_occ_ninats | Nights spent at hotels and similar accommodation (NACE Rev.2 activity I55.1) by size class | 2012–2025
tour_occ_arn2 | Arrivals at tourist accommodation establishments by NUTS 2 region | 1990–2025
tour_occ_ninrmw | Nights spent at tourist accommodation establishments by country of origin of the tourist - monthly data (1990-2011) | 1990-01–2011-12
tour_occ_arnat | Arrivals at tourist accommodation establishments | 1990–2025
enps_tour_occ_arnat | Arrivals at tourism accommodation establishments by type of accommodation - ENP-South countries | 2005–2024
```

**4. `get_structure(dataset="tour_occ_nin2")`**

```
Dataset tour_occ_nin2 — dimensions :
- freq [Time frequency] : A (Annual)
- c_resid [Country of residence] : DOM (Domestic country), FOR (Foreign country), TOTAL (Total)
- unit [Unit of measure] : NR (Number), P_THAB (Per thousand inhabitants), P_KM2 (Per square kilometre), PC_TOT (Percentage of total), PCH_PRE (Percentage change on previous period)
- nace_r2 [Statistical classification of economic activities in the European Community (NACE Rev. 2)] : I551-I553 (Hotels; holiday and other short-stay accommodation; camping grounds, recreational vehicle parks and trailer parks), I551 (Hotels and similar accommodation), I552_I553 (Holiday and other short-stay accommodation; camping grounds, recreational vehicle parks and trailer parks), I552 (Holiday and other short-stay accommodation), I553 (Camping grounds, recreational vehicle parks and trailer parks)
- geo [Geopolitical entity (reporting)] : EU27_2020 (European Union - 27 countries (from 2020)), EU28 (European Union - 28 countries (2013-2020)), EU27_2007 (European Union - 27 countries (2007-2013)), EU25 (European Union - 25 countries (2004-2006)), EA (Euro area (EA11-1999, EA12-2001, EA13-2007, EA15-2008, EA16-2009, EA17-2011, EA18-2014, EA19-2015, EA20-2023, EA21-2026)), EA20 (Euro area – 20 countries (2023-2025)), BE (Belgium), BE1 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE10 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE100 (Arr. de Bruxelles-Capitale/Arr. Brussel-Hoofdstad), BE2 (Vlaams Gewest), BE21 (Prov. Antwerpen), BE211 (Arr. Antwerpen), BE212 (Arr. Mechelen), BE213 (Arr. Turnhout), BE22 (Prov. Limburg (BE)), BE223 (Arr. Tongeren), BE224 (Arr. Hasselt), BE225 (Arr. Maaseik), BE23 (Prov. Oost-Vlaanderen), BE231 (Arr. Aalst), BE232 (Arr. Dendermonde), BE233 (Arr. Eeklo), BE234 (Arr. Gent), BE235 (Arr. Oudenaarde) … et 1845 autres (voir list_codes)
- time [Time] : 1990 → 2025 (filtrer avec time_from / time_to)
```

**5. `get_structure(dataset="tour_occ_nin2dc")`**

```
Dataset tour_occ_nin2dc — dimensions :
- freq [Time frequency] : A (Annual)
- c_resid [Country of residence] : DOM (Domestic country), FOR (Foreign country), TOTAL (Total)
- terrtypo [Territorial typology] : TOTAL (Total), DEG1 (Cities), DEG2 (Towns and suburbs), DEG3 (Rural areas), CST_A (Coastal areas), NCST_A (Non-coastal areas), DEG1_CST_A (Cities in coastal areas), DEG2_CST_A (Towns and suburbs in coastal areas), DEG3_CST_A (Rural areas in coastal areas), DEG1_NCST_A (Cities in non-coastal areas), DEG2_NCST_A (Towns and suburbs in non-coastal areas), DEG3_NCST_A (Rural areas in coastal non-coastal areas)
- nace_r2 [Statistical classification of economic activities in the European Community (NACE Rev. 2)] : I551-I553 (Hotels; holiday and other short-stay accommodation; camping grounds, recreational vehicle parks and trailer parks), I551 (Hotels and similar accommodation), I552_I553 (Holiday and other short-stay accommodation; camping grounds, recreational vehicle parks and trailer parks), I552 (Holiday and other short-stay accommodation), I553 (Camping grounds, recreational vehicle parks and trailer parks)
- unit [Unit of measure] : NR (Number), PCH_PRE (Percentage change on previous period)
- geo [Geopolitical entity (reporting)] : EU27_2020 (European Union - 27 countries (from 2020)), EU28 (European Union - 28 countries (2013-2020)), EU27_2007 (European Union - 27 countries (2007-2013)), EU25 (European Union - 25 countries (2004-2006)), EA (Euro area (EA11-1999, EA12-2001, EA13-2007, EA15-2008, EA16-2009, EA17-2011, EA18-2014, EA19-2015, EA20-2023, EA21-2026)), EA20 (Euro area – 20 countries (2023-2025)), BE (Belgium), BE1 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE10 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE2 (Vlaams Gewest), BE21 (Prov. Antwerpen), BE22 (Prov. Limburg (BE)), BE23 (Prov. Oost-Vlaanderen), BE24 (Prov. Vlaams-Brabant), BE25 (Prov. West-Vlaanderen), BE3 (Région wallonne), BE31 (Prov. Brabant wallon), BE32 (Prov. Hainaut), BE33 (Prov. Liège), BE34 (Prov. Luxembourg (BE)), BE35 (Prov. Namur), BG (Bulgaria), BG3 (Severna i Yugoiztochna Bulgaria), BG31 (Severozapaden), BG32 (Severen tsentralen) … et 440 autres (voir list_codes)
- time [Time] : 2012 → 2025 (filtrer avec time_from / time_to)
```

**6. `list_codes(dataset="tour_occ_nin2", dimension="geo", contains="ES")`**

```
ES : Spain
ES1 : Noroeste
ES2 : Noreste
ES3 : Comunidad de Madrid
ES4 : Centro (ES)
ES5 : Este
ES6 : Sur
ES7 : Canarias
ES11 : Galicia
ES12 : Principado de Asturias
ES13 : Cantabria
ES21 : País Vasco
ES22 : Comunidad Foral de Navarra
ES23 : La Rioja
ES24 : Aragón
ES30 : Comunidad de Madrid
ES41 : Castilla y León
ES42 : Castilla-La Mancha
ES43 : Extremadura
ES51 : Cataluña
ES52 : Comunitat Valenciana
ES53 : Illes Balears
ES61 : Andalucía
ES62 : Región de Murcia
ES63 : Ciudad de Ceuta
ES64 : Ciudad de Melilla
ES70 : Canarias
ES111 : A Coruña
ES112 : Lugo
ES113 : Ourense
ES114 : Pontevedra
ES120 : Asturias
ES130 : Cantabria
ES211 : Araba/Álava
ES212 : Gipuzkoa
ES213 : Bizkaia
ES220 : Navarra
ES230 : La Rioja
ES241 : Huesca
ES242 : Teruel
ES243 : Zaragoza
ES300 : Madrid
ES411 : Ávila
ES412 : Burgos
ES413 : León
ES414 : Palencia
ES415 : Salamanca
ES416 : Segovia
ES417 : Soria
ES418 : Valladolid
ES419 : Zamora
ES421 : Albacete
ES422 : Ciudad Real
ES423 : Cuenca
ES424 : Guadalajara
ES425 : Toledo
ES431 : Badajoz
ES432 : Cáceres
ES511 : Barcelona
ES512 : Girona
… et 230 autres, affinez 'contains'.
```

**7. `list_codes(dataset="tour_occ_nin2", dimension="geo", contains="IT")`**

```
IT : Italy
ITC : Nord-Ovest
ITF : Sud
ITG : Isole
ITH : Nord-Est
ITI : Centro (IT)
ITC1 : Piemonte
ITC2 : Valle d’Aosta/Vallée d’Aoste
ITC3 : Liguria
ITC4 : Lombardia
ITF1 : Abruzzo
ITF2 : Molise
ITF3 : Campania
ITF4 : Puglia
ITF5 : Basilicata
ITF6 : Calabria
ITG1 : Sicilia
ITG2 : Sardegna
ITH1 : Provincia Autonoma di Bolzano/Bozen
ITH2 : Provincia Autonoma di Trento
ITH3 : Veneto
ITH4 : Friuli-Venezia Giulia
ITH5 : Emilia-Romagna
ITI1 : Toscana
ITI2 : Umbria
ITI3 : Marche
ITI4 : Lazio
ITC11 : Torino
ITC12 : Vercelli
ITC13 : Biella
ITC14 : Verbano-Cusio-Ossola
ITC15 : Novara
ITC16 : Cuneo
ITC17 : Asti
ITC18 : Alessandria
ITC20 : Valle d’Aosta/Vallée d’Aoste
ITC31 : Imperia
ITC32 : Savona
ITC33 : Genova
ITC34 : La Spezia
ITC41 : Varese
ITC42 : Como
ITC43 : Lecco
ITC44 : Sondrio
ITC46 : Bergamo
ITC47 : Brescia
ITC48 : Pavia
ITC49 : Lodi
ITC4A : Cremona
ITC4B : Mantova
ITC4C : Milano
ITC4D : Monza e della Brianza
ITF11 : L’Aquila
ITF12 : Teramo
ITF13 : Pescara
ITF14 : Chieti
ITF21 : Isernia
ITF22 : Campobasso
ITF31 : Caserta
ITF32 : Benevento
… et 143 autres, affinez 'contains'.
```

**8. `query_data(dataset="tour_occ_nin2", filters={"geo": "ES11+ES12+ES13+ES21+ES22+ES23+ES24+ES30+ES41+ES42+ES43+ES51+ES52+ES53+ES61+ES62+ES63+ES64+ES70+ITC1+ITC2+ITC3+ITC4+ITH1+ITH2+ITH3+ITH4+ITH5+ITI1+ITI2+ITI3+ITI4+ITF1+ITF2+ITF3+ITF4+ITF5+ITF6+ITG1+ITG2", "unit": "NR", "c_resid": "TOTAL", "nace_r2": "I551-I553", "freq": "A"}, time_from="2023", time_to="2025")`**

```
freq | c_resid | unit | nace_r2 | geo | time | value | flag
A | TOTAL | NR | I551-I553 | ITH5 | 2023 | 39176137.0 | 
A | TOTAL | NR | I551-I553 | ES12 | 2023 | 6672748.0 | 
A | TOTAL | NR | I551-I553 | ITF3 | 2023 | 20695842.0 | 
A | TOTAL | NR | I551-I553 | ES64 | 2023 | 132824.0 | 
A | TOTAL | NR | I551-I553 | ITH4 | 2023 | 9946875.0 | 
A | TOTAL | NR | I551-I553 | ES61 | 2023 | 73900351.0 | 
A | TOTAL | NR | I551-I553 | ITG1 | 2023 | 16448284.0 | 
A | TOTAL | NR | I551-I553 | ITC2 | 2023 | 3692878.0 | 
A | TOTAL | NR | I551-I553 | ES70 | 2023 | 95574956.0 | 
A | TOTAL | NR | I551-I553 | ES43 | 2023 | 3784158.0 | 
A | TOTAL | NR | I551-I553 | ES41 | 2023 | 12926756.0 | 
A | TOTAL | NR | I551-I553 | ITF4 | 2023 | 16822144.0 | 
A | TOTAL | NR | I551-I553 | ITC4 | 2023 | 41795073.0 | 
A | TOTAL | NR | I551-I553 | ITF5 | 2023 | 2537324.0 | 
A | TOTAL | NR | I551-I553 | ES23 | 2023 | 1716159.0 | 
A | TOTAL | NR | I551-I553 | ES30 | 2023 | 30238007.0 | 
A | TOTAL | NR | I551-I553 | ITI3 | 2023 | 10660677.0 | 
A | TOTAL | NR | I551-I553 | ITC1 | 2023 | 14410448.0 | 
A | TOTAL | NR | I551-I553 | ES62 | 2023 | 5493664.0 | 
A | TOTAL | NR | I551-I553 | ITI1 | 2023 | 46019310.0 | 
A | TOTAL | NR | I551-I553 | ITC3 | 2023 | 16084210.0 | 
A | TOTAL | NR | I551-I553 | ES42 | 2023 | 5874181.0 | 
A | TOTAL | NR | I551-I553 | ITH1 | 2023 | 36085187.0 | 
A | TOTAL | NR | I551-I553 | ES51 | 2023 | 85635851.0 | 
A | TOTAL | NR | I551-I553 | ITH3 | 2023 | 71896863.0 | 
A | TOTAL | NR | I551-I553 | ITI2 | 2023 | 6428948.0 | 
A | TOTAL | NR | I551-I553 | ES11 | 2023 | 13514998.0 | 
A | TOTAL | NR | I551-I553 | ITG2 | 2023 | 14200536.0 | 
A | TOTAL | NR | I551-I553 | ES52 | 2023 | 52449694.0 | 
A | TOTAL | NR | I551-I553 | ITF1 | 2023 | 6804820.0 | 
A | TOTAL | NR | I551-I553 | ITF6 | 2023 | 8100594.0 | 
A | TOTAL | NR | I551-I553 | ES24 | 2023 | 8566961.0 | 
A | TOTAL | NR | I551-I553 | ES22 | 2023 | 4032325.0 | 
A | TOTAL | NR | I551-I553 | ITH2 | 2023 | 19141944.0 | 
A | TOTAL | NR | I551-I553 | ITF2 | 2023 | 494786.0 | 
A | TOTAL | NR | I551-I553 | ES53 | 2023 | 68791810.0 | 
A | TOTAL | NR | I551-I553 | ES63 | 2023 | 144427.0 | 
A | TOTAL | NR | I551-I553 | ITI4 | 2023 | 45727169.0 | 
A | TOTAL | NR | I551-I553 | ES13 | 2023 | 5811506.0 | 
A | TOTAL | NR | I551-I553 | ES21 | 2023 | 9726106.0 | 
A | TOTAL | NR | I551-I553 | ES22 | 2024 | 4082631.0 | 
A | TOTAL | NR | I551-I553 | ITG2 | 2024 | 15610251.0 | 
A | TOTAL | NR | I551-I553 | ITH3 | 2024 | 73472377.0 | 
A | TOTAL | NR | I551-I553 | ITH1 | 2024 | 37046803.0 | 
A | TOTAL | NR | I551-I553 | ES41 | 2024 | 13063897.0 | 
A | TOTAL | NR | I551-I553 | ITI1 | 2024 | 46220821.0 | 
A | TOTAL | NR | I551-I553 | ITG1 | 2024 | 17348238.0 | 
A | TOTAL | NR | I551-I553 | ITF5 | 2024 | 2511372.0 | 
A | TOTAL | NR | I551-I553 | ITF2 | 2024 | 456284.0 | 
A | TOTAL | NR | I551-I553 | ES64 | 2024 | 133821.0 | 
A | TOTAL | NR | I551-I553 | ITF3 | 2024 | 21369462.0 | 
A | TOTAL | NR | I551-I553 | ES61 | 2024 | 77308673.0 | 
A | TOTAL | NR | I551-I553 | ITC1 | 2024 | 14395737.0 | 
A | TOTAL | NR | I551-I553 | ES21 | 2024 | 10253106.0 | 
A | TOTAL | NR | I551-I553 | ITC4 | 2024 | 45130529.0 | 
A | TOTAL | NR | I551-I553 | ES23 | 2024 | 1675862.0 | 
A | TOTAL | NR | I551-I553 | ES53 | 2024 | 73845222.0 | 
A | TOTAL | NR | I551-I553 | ES63 | 2024 | 134584.0 | 
A | TOTAL | NR | I551-I553 | ES51 | 2024 | 88670191.0 | 
A | TOTAL | NR | I551-I553 | ITC2 | 2024 | 3695059.0 | 
A | TOTAL | NR | I551-I553 | ES42 | 2024 | 5956715.0 | 
A | TOTAL | NR | I551-I553 | ITH5 | 2024 | 40782820.0 | 
A | TOTAL | NR | I551-I553 | ITF6 | 2024 | 8143970.0 | 
A | TOTAL | NR | I551-I553 | ES11 | 2024 | 13305882.0 | 
A | TOTAL | NR | I551-I553 | ES13 | 2024 | 6117130.0 | 
A | TOTAL | NR | I551-I553 | ES30 | 2024 | 32320997.0 | 
A | TOTAL | NR | I551-I553 | ES52 | 2024 | 53662343.0 | 
A | TOTAL | NR | I551-I553 | ES24 | 2024 | 8664390.0 | 
A | TOTAL | NR | I551-I553 | ES43 | 2024 | 4081510.0 | 
A | TOTAL | NR | I551-I553 | ITI4 | 2024 | 51753567.0 | 
A | TOTAL | NR | I551-I553 | ITI2 | 2024 | 6751042.0 | 
A | TOTAL | NR | I551-I553 | ES62 | 2024 | 5710567.0 | 
A | TOTAL | NR | I551-I553 | ITF1 | 2024 | 7176204.0 | 
A | TOTAL | NR | I551-I553 | ITC3 | 2024 | 16128866.0 | 
A | TOTAL | NR | I551-I553 | ES70 | 2024 | 99488821.0 | 
A | TOTAL | NR | I551-I553 | ITH2 | 2024 | 19644628.0 | 
A | TOTAL | NR | I551-I553 | ITH4 | 2024 | 10143980.0 | 
A | TOTAL | NR | I551-I553 | ES12 | 2024 | 6689670.0 | 
A | TOTAL | NR | I551-I553 | ITI3 | 2024 | 10481674.0 | 
A | TOTAL | NR | I551-I553 | ITF4 | 2024 | 17894361.0 | 
A | TOTAL | NR | I551-I553 | ITG1 | 2025 | 23351923.0 | 
A | TOTAL | NR | I551-I553 | ITH3 | 2025 | 74157131.0 | 
A | TOTAL | NR | I551-I553 | ITG2 | 2025 | 21720511.0 | 
A | TOTAL | NR | I551-I553 | ITH1 | 2025 | 38239379.0 | 
A | TOTAL | NR | I551-I553 | ITC1 | 2025 | 18167867.0 | 
A | TOTAL | NR | I551-I553 | ITI2 | 2025 | 7942202.0 | 
A | TOTAL | NR | I551-I553 | ITH2 | 2025 | 22669069.0 | 
A | TOTAL | NR | I551-I553 | ITH5 | 2025 | 44170468.0 | 
A | TOTAL | NR | I551-I553 | ITF6 | 2025 | 9287632.0 | 
A | TOTAL | NR | I551-I553 | ITF5 | 2025 | 2827146.0 | 
A | TOTAL | NR | I551-I553 | ITH4 | 2025 | 11032685.0 | 
A | TOTAL | NR | I551-I553 | ITC3 | 2025 | 15972514.0 | 
A | TOTAL | NR | I551-I553 | ITF2 | 2025 | 474764.0 | 
A | TOTAL | NR | I551-I553 | ITC4 | 2025 | 56693078.0 | 
A | TOTAL | NR | I551-I553 | ITI3 | 2025 | 11803145.0 | 
A | TOTAL | NR | I551-I553 | ITI1 | 2025 | 55475875.0 | 
A | TOTAL | NR | I551-I553 | ITI4 | 2025 | 61532691.0 | 
A | TOTAL | NR | I551-I553 | ITF1 | 2025 | 8709404.0 | 
A | TOTAL | NR | I551-I553 | ITC2 | 2025 | 4519068.0 | 
A | TOTAL | NR | I551-I553 | ITF3 | 2025 | 24038339.0 | 
A | TOTAL | NR | I551-I553 | ITF4 | 2025 | 22678354.0 | 
[Source : miroir local, données Eurostat du 02.07.2026]
```

## Answer

I have everything I need. Here are the results.

## Dataset
**`tour_occ_nin2`** — *Nights spent at tourist accommodation establishments by NUTS region* (Eurostat, 1990–2025). Despite the "nin2" suffix, the `geo` dimension carries all NUTS levels (NUTS0–3), so NUTS2 codes work directly.

## Filters used
| Dimension | Value | Meaning |
|---|---|---|
| `geo` | all NUTS2 codes of Spain (ES11…ES70) + Italy (ITC1…ITG2) | the regions in scope |
| `unit` | `NR` | Number of nights |
| `c_resid` | `TOTAL` | Domestic + foreign combined |
| `nace_r2` | `I551-I553` | All tourist accommodation (hotels, short-stay, camping) |
| `freq` | `A` | Annual |
| `time` | 2023–2025 | to locate the latest year |

⚠️ **Data-lag caveat:** the latest available year differs by country — **Spain ends at 2024**, **Italy at 2025**. So "latest year available" is 2024 for ES regions and 2025 for IT regions (a cross-year comparison). A strict same-year (2024) comparison gives essentially the same top 5.

## Top 5 NUTS2 regions by nights (each at its own latest year)

| Rank | Region | Code | Country | Year | Nights |
|---|---|---|---|---|---|
| 1 | Canarias | ES70 | 🇪🇸 | 2024 | 99,488,821 |
| 2 | Cataluña | ES51 | 🇪🇸 | 2024 | 88,670,191 |
| 3 | Andalucía | ES61 | 🇪🇸 | 2024 | 77,308,673 |
| 4 | Veneto | ITH3 | 🇮🇹 | 2025 | 74,157,131 |
| 5 | Illes Balears | ES53 | 🇪🇸 | 2024 | 73,845,222 |

**Observation:** 4 of the top 5 are Spanish. The only Italian region in the top 5 is **Veneto** (ITH3). The next Italian regions down (for 2025) are Lazio (ITI4, 61.5M), Lombardia (ITC4, 56.7M) and Toscana (ITI1, 55.5M) — all below the Spanish coastal/insular leaders.

*Runner-up note:* if you force a single common year (2024), the top 5 is identical in membership, with Veneto (73.47M) just edging below Illes Balears (73.85M).

