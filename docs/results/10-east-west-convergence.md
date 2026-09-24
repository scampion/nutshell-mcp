# Example 10 — East–West convergence

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> How have Poland, Romania, Czechia and Hungary converged with the rest of the EU since 2014? For their capital regions and one other NUTS2 region per country of your choice, show GDP per capita and unemployment over 2014-2024 and summarise the trend. Point out breaks in series and provisional values.

## Tool calls

**1. `search_indicators(query="GDP per capita", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
```

**2. `search_indicators(query="unemployment rate", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**3. `list_zones(level="NUTS2", parent="PL")`**

```
geo_code | name | level | parent
PL21 | Małopolskie | NUTS2 | PL2
PL22 | Śląskie | NUTS2 | PL2
PL41 | Wielkopolskie | NUTS2 | PL4
PL42 | Zachodniopomorskie | NUTS2 | PL4
PL43 | Lubuskie | NUTS2 | PL4
PL51 | Dolnośląskie | NUTS2 | PL5
PL52 | Opolskie | NUTS2 | PL5
PL61 | Kujawsko-pomorskie | NUTS2 | PL6
PL62 | Warmińsko-mazurskie | NUTS2 | PL6
PL63 | Pomorskie | NUTS2 | PL6
PL71 | Łódzkie | NUTS2 | PL7
PL72 | Świętokrzyskie | NUTS2 | PL7
PL81 | Lubelskie | NUTS2 | PL8
PL82 | Podkarpackie | NUTS2 | PL8
PL84 | Podlaskie | NUTS2 | PL8
PL91 | Warszawski stołeczny | NUTS2 | PL9
PL92 | Mazowiecki regionalny | NUTS2 | PL9
```

**4. `list_zones(level="NUTS2", parent="RO")`**

```
geo_code | name | level | parent
RO11 | Nord-Vest | NUTS2 | RO1
RO12 | Centru | NUTS2 | RO1
RO21 | Nord-Est | NUTS2 | RO2
RO22 | Sud-Est | NUTS2 | RO2
RO31 | Sud-Muntenia | NUTS2 | RO3
RO32 | Bucureşti-Ilfov | NUTS2 | RO3
RO41 | Sud-Vest Oltenia | NUTS2 | RO4
RO42 | Vest | NUTS2 | RO4
```

**5. `list_zones(level="NUTS2", parent="CZ")`**

```
geo_code | name | level | parent
CZ01 | Praha | NUTS2 | CZ0
CZ02 | Střední Čechy | NUTS2 | CZ0
CZ03 | Jihozápad | NUTS2 | CZ0
CZ04 | Severozápad | NUTS2 | CZ0
CZ05 | Severovýchod | NUTS2 | CZ0
CZ06 | Jihovýchod | NUTS2 | CZ0
CZ07 | Střední Morava | NUTS2 | CZ0
CZ08 | Moravskoslezsko | NUTS2 | CZ0
```

**6. `list_zones(level="NUTS2", parent="HU")`**

```
geo_code | name | level | parent
HU11 | Budapest | NUTS2 | HU1
HU12 | Pest | NUTS2 | HU1
HU21 | Közép-Dunántúl | NUTS2 | HU2
HU22 | Nyugat-Dunántúl | NUTS2 | HU2
HU23 | Dél-Dunántúl | NUTS2 | HU2
HU31 | Észak-Magyarország | NUTS2 | HU3
HU32 | Észak-Alföld | NUTS2 | HU3
HU33 | Dél-Alföld | NUTS2 | HU3
```

**7. `get_indicators(indicators=["gdp_per_capita", "unemployment_rate"], zones=["PL91", "PL92", "RO32", "RO31", "CZ01", "CZ02", "HU11", "HU12"], time_from="2014", time_to="2024")`**

```
geo_code | time | gdp_per_capita | unemployment_rate
CZ01 | 2024 | 62400 | 1.8
CZ01 | 2023 | 63500 | 2.1
CZ01 | 2022 | 59400 | 1.6
CZ01 | 2021 | 52600 | 2.3 [b]
CZ01 | 2020 | 46300 | 2.3
CZ01 | 2019 | 48000 | 1.3
CZ01 | 2018 | 44900 | 1.3
CZ01 | 2017 | 40800 | 1.7
CZ01 | 2016 | 37500 | 2.2
CZ01 | 2015 | 35700 | 2.8
CZ01 | 2014 | 33200 | 2.5
CZ02 | 2024 | 27200 | 1.3
CZ02 | 2023 | 26400 | 1.7
CZ02 | 2022 | 23800 | 1.2
CZ02 | 2021 | 21100 | 2.5 [b]
CZ02 | 2020 | 19000 | 1.9
CZ02 | 2019 | 20500 | 1.3
CZ02 | 2018 | 18500 | 2
CZ02 | 2017 | 17500 | 2.1
CZ02 | 2016 | 15900 | 3.1
CZ02 | 2015 | 14900 | 3.5
CZ02 | 2014 | 13900 | 5.1
HU11 | 2024 | 47600 [p] | 2.6
HU11 | 2023 | 44700 | 2.3
HU11 | 2022 | 37200 | 2.3
HU11 | 2021 | 34100 | 2.9 [b]
HU11 | 2020 | 30300 | 3.3
HU11 | 2019 | 32300 | 2.4
HU11 | 2018 | 28800 | 3 [b]
HU11 | 2017 | 26800 | 2.9
HU11 | 2016 | 24200 | 4.3
HU11 | 2015 | 23400 | 5.1
HU11 | 2014 | 22700 | 6
HU12 | 2024 | 18100 [p] | 3.1
HU12 | 2023 | 17600 | 3.2
HU12 | 2022 | 15100 | 2.2
HU12 | 2021 | 13200 | 2.9 [b]
HU12 | 2020 | 11500 | 3.3
HU12 | 2019 | 12000 | 2.4
HU12 | 2018 | 11000 | 2.2 [b]
HU12 | 2017 | 10300 | 2.6
HU12 | 2016 | 9600 | 3.1
HU12 | 2015 | 9600 | 5.7
HU12 | 2014 | 8900 | 6.5
PL91 | 2024 | 45300 [p] | 2.5
PL91 | 2023 | 40200 | 1.9
PL91 | 2022 | 33900 [b] | 2
PL91 | 2021 | 30900 | 2.1 [b]
PL91 | 2020 | 28900 [b] | 2.6
PL91 | 2019 | 30600 | 2.1 [b]
PL91 | 2018 | 28500 | 2.4
PL91 | 2017 | 26300 | 3.5
PL91 | 2016 | 23800 | 3.7 [b]
PL91 | 2015 | 24200 | 4.9
PL91 | 2014 | 23000 | 5.8
PL92 | 2024 | 20600 [p] | 3.5
PL92 | 2023 | 18100 | 3.1
PL92 | 2022 | 16500 [b] | 3.7
PL92 | 2021 | 14000 | 3.8 [b]
PL92 | 2020 | 12600 [b] | 4.7
PL92 | 2019 | 12500 | 4.5 [b]
PL92 | 2018 | 11500 | 5.7
PL92 | 2017 | 10800 | 6.4
PL92 | 2016 | 9900 | 7.8 [b]
PL92 | 2015 | 10000 | 8.3
PL92 | 2014 | 9300 | 8.9
RO31 | 2024 | 13200 [p] | 7.3
RO31 | 2023 | 12100 | 7.8
RO31 | 2022 | 11400 | 7.9
RO31 | 2021 | 9500 | 7.7 [b]
RO31 | 2020 | 8600 | 5.9
RO31 | 2019 | 8700 | 4.7
RO31 | 2018 | 8200 | 5.5
RO31 | 2017 | 7300 | 6.8
RO31 | 2016 | 6800 | 8.9
RO31 | 2015 | 6400 | 10.3
RO31 | 2014 | 6400 | 9
RO32 | 2024 | 45200 [p] | 2.2
RO32 | 2023 | 40800 | 2.8
RO32 | 2022 | 35900 | 2.7
RO32 | 2021 | 29500 | 3.5 [b]
RO32 | 2020 | 26200 | 4.7
RO32 | 2019 | 26500 | 2.5
RO32 | 2018 | 23800 | 3.6
RO32 | 2017 | 22000 | 4.3
RO32 | 2016 | 19900 | 4.7
RO32 | 2015 | 19300 | 5.3
RO32 | 2014 | 17300 | 7.2
[Source : eurostat (gdp_per_capita 10.02.2026, unemployment_rate 30.06.2026)]
```

**8. `list_zones(level="NUTS0", contains="EU")`**

```
geo_code | name | level | parent
DE | Deutschland | NUTS0 | 
```

**9. `list_zones(level="NUTS0")`**

```
geo_code | name | level | parent
AL | Shqipëria | NUTS0 | 
AT | Österreich | NUTS0 | 
BA | Bosna I Hercegovina | NUTS0 | 
BE | Belgique/België | NUTS0 | 
BG | Bulgaria | NUTS0 | 
CH | Schweiz/Suisse/Svizzera | NUTS0 | 
CY | Kýpros | NUTS0 | 
CZ | Česko | NUTS0 | 
DE | Deutschland | NUTS0 | 
DK | Danmark | NUTS0 | 
EE | Eesti | NUTS0 | 
EL | Elláda | NUTS0 | 
ES | España | NUTS0 | 
FI | Suomi/Finland | NUTS0 | 
FR | France | NUTS0 | 
HR | Hrvatska | NUTS0 | 
HU | Magyarország | NUTS0 | 
IE | Éire/Ireland | NUTS0 | 
IS | Ísland | NUTS0 | 
IT | Italia | NUTS0 | 
LI | Liechtenstein | NUTS0 | 
LT | Lietuva | NUTS0 | 
LU | Luxembourg | NUTS0 | 
LV | Latvija | NUTS0 | 
ME | Crna Gora | NUTS0 | 
MK | Severna Makedonija  | NUTS0 | 
MT | Malta | NUTS0 | 
NL | Nederland | NUTS0 | 
NO | Norge | NUTS0 | 
PL | Polska | NUTS0 | 
PT | Portugal | NUTS0 | 
RO | România | NUTS0 | 
RS | Serbia | NUTS0 | 
SE | Sverige | NUTS0 | 
SI | Slovenija | NUTS0 | 
SK | Slovensko | NUTS0 | 
TR | Türkiye | NUTS0 | 
UA | Ukraina | NUTS0 | 
XK | Kosovo* | NUTS0 | 
```

**10. `get_indicators(indicators=["gdp_per_capita", "unemployment_rate"], zones=["AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", "NL", "PL", "PT", "RO", "SE", "SI", "SK"], time_from="2014", time_to="2024")`**

```
geo_code | time | gdp_per_capita | unemployment_rate
AT | 2024 | 53800 | 5.2
AT | 2023 | 52300 | 5.1
AT | 2022 | 49600 | 4.8
AT | 2021 | 45400 | 6.2 [b]
AT | 2020 | 42700 | 5.4
AT | 2019 | 44600 | 4.5
AT | 2018 | 43400 | 4.9
AT | 2017 | 41800 | 5.5
AT | 2016 | 40700 | 6
AT | 2015 | 39600 | 5.7
AT | 2014 | 38600 | 5.6
BE | 2024 | 52300 [p] | 5.7
BE | 2023 | 51100 | 5.5
BE | 2022 | 48100 | 5.6
BE | 2021 | 43700 | 6.3 [b]
BE | 2020 | 40200 | 5.6
BE | 2019 | 41700 | 5.4
BE | 2018 | 40200 | 6
BE | 2017 | 39000 | 7.1 [b]
BE | 2016 | 37800 | 7.8
BE | 2015 | 36900 | 8.5
BE | 2014 | 36100 | 8.5
BG | 2024 | 16300 | 4.2 [b]
BG | 2023 | 14700 | 4.3
BG | 2022 | 13300 | 4.2
BG | 2021 | 11000 | 5.2 [b]
BG | 2020 | 9400 | 5
BG | 2019 | 9200 | 4.2 [b]
BG | 2018 | 8300 | 5.2
BG | 2017 | 7700 | 6.2
BG | 2016 | 7100 | 7.6
BG | 2015 | 6600 | 9.2
BG | 2014 | 6100 | 11.4
CY | 2024 | 35700 [p] | 4.8
CY | 2023 | 33900 | 5.8
CY | 2022 | 31600 | 6.3
CY | 2021 | 27800 | 7.2 [b]
CY | 2020 | 24600 | 7.6
CY | 2019 | 26100 | 7.2
CY | 2018 | 24700 | 8.4
CY | 2017 | 23200 | 11.1
CY | 2016 | 21900 | 13
CY | 2015 | 20800 | 15
CY | 2014 | 20300 | 16.1
CZ | 2024 | 29400 | 2.6
CZ | 2023 | 29300 | 2.6
CZ | 2022 | 26700 | 2.2
CZ | 2021 | 23400 | 2.8 [b]
CZ | 2020 | 21000 | 2.6
CZ | 2019 | 21700 | 2
CZ | 2018 | 20300 | 2.2
CZ | 2017 | 18700 | 2.9
CZ | 2016 | 17000 | 4
CZ | 2015 | 16200 | 5.1
CZ | 2014 | 15100 | 6.1
DE | 2024 | 51800 [p] | 3.5
DE | 2023 | 50700 [p] | 3.1
DE | 2022 | 48300 [p] | 3.1
DE | 2021 | 44900 | 3.6 [b]
DE | 2020 | 42000 | 3.9 [b]
DE | 2019 | 43000 | 3.1
DE | 2018 | 41800 | 3.4
DE | 2017 | 40600 | 3.8
DE | 2016 | 39000 | 4.1
DE | 2015 | 37900 | 4.6
DE | 2014 | 37000 | 5
DK | 2024 | 65700 | 6.2
DK | 2023 | 62900 | 5.1 [b]
DK | 2022 | 64400 | 4.5
DK | 2021 | 58600 | 5.1 [b]
DK | 2020 | 53500 | 5.6
DK | 2019 | 53000 | 5
DK | 2018 | 52000 | 5.1
DK | 2017 | 51100 | 5.8 [b]
DK | 2016 | 49300 | 6 [b]
DK | 2015 | 47900 | 6.3
DK | 2014 | 47100 | 6.9
EE | 2024 | 29000 | 7.6
EE | 2023 | 28100 | 6.4
EE | 2022 | 27300 | 5.6
EE | 2021 | 23600 | 6.2 [b]
EE | 2020 | 21000 | 7
EE | 2019 | 21500 | 4.5
EE | 2018 | 20000 | 5.4
EE | 2017 | 18500 | 5.8
EE | 2016 | 16900 | 6.9
EE | 2015 | 16000 | 6.4
EE | 2014 | 15500 | 7.4
EL | 2024 | 22500 [p] | 10.1
EL | 2023 | 21300 [p] | 11.1
EL | 2022 | 19600 [p] | 12.5
EL | 2021 | 17300 [p] | 14.7 [b]
EL | 2020 | 15700 [p] | 16.3
EL | 2019 | 17300 [p] | 17.3
EL | 2018 | 16800 [p] | 19.3
EL | 2017 | 16500 [p] | 21.5
EL | 2016 | 16200 [p] | 23.6
EL | 2015 | 16200 [p] | 24.9
EL | 2014 | 16200 [p] | 26.5
ES | 2024 | 32600 [p] | 11.4 [d]
ES | 2023 | 31000 [p] | 12.2 [d]
ES | 2022 | 28800 | 13 [d]
ES | 2021 | 26100 | 14.9 [bd]
ES | 2020 | 23900 | 15.5
ES | 2019 | 26600 | 14.1
ES | 2018 | 26000 | 15.3
ES | 2017 | 25200 | 17.2
ES | 2016 | 24200 | 19.6
ES | 2015 | 23400 | 22.1
ES | 2014 | 22400 | 24.5
FI | 2024 | 49100 | 8.4
FI | 2023 | 48900 | 7.2
FI | 2022 | 47900 | 6.8
FI | 2021 | 44900 | 7.7 [b]
FI | 2020 | 42700 | 7.8
FI | 2019 | 43200 | 6.7
FI | 2018 | 42000 | 7.4
FI | 2017 | 40800 | 8.6
FI | 2016 | 39300 | 8.8
FI | 2015 | 38400 | 9.4
FI | 2014 | 37700 | 8.7
FR | 2024 | 42600 [p] | 7.4 [bd]
FR | 2023 | 41300 [p] | 7.3 [d]
FR | 2022 | 38900 | 7.3 [d]
FR | 2021 | 36900 | 7.9 [bd]
FR | 2020 | 34300 | 8.1
FR | 2019 | 36100 | 8.5
FR | 2018 | 35100 | 9.1
FR | 2017 | 34300 | 9.5
FR | 2016 | 33500 | 10.1
FR | 2015 | 33200 | 10.4
FR | 2014 | 32600 | 10.3
HR | 2024 | 22200 [p] | 5
HR | 2023 | 20500 | 6.1
HR | 2022 | 17500 | 6.8
HR | 2021 | 15100 | 7.5 [b]
HR | 2020 | 13000 | 7.4
HR | 2019 | 14100 | 6.6
HR | 2018 | 13300 | 8.3
HR | 2017 | 12400 | 11.1
HR | 2016 | 11600 | 13
HR | 2015 | 11000 | 16.2
HR | 2014 | 10600 | 17.3
HU | 2024 | 21500 [p] | 4.5
HU | 2023 | 20600 | 4.1
HU | 2022 | 17500 | 3.6
HU | 2021 | 16100 | 4 [b]
HU | 2020 | 14400 | 4.2
HU | 2019 | 15200 | 3.4
HU | 2018 | 14100 | 3.7 [b]
HU | 2017 | 13100 | 4.2
HU | 2016 | 11900 | 5.1
HU | 2015 | 11500 | 6.8
HU | 2014 | 10800 | 7.7
IE | 2024 | 104500 [e] | 4.3
IE | 2023 | 99100 | 4.3
IE | 2022 | 100100 | 4.5
IE | 2021 | 88100 | 6.2 [b]
IE | 2020 | 75800 | 5.7
IE | 2019 | 73200 | 5
IE | 2018 | 68500 | 5.8
IE | 2017 | 64000 | 6.7 [b]
IE | 2016 | 58100 | 8.4
IE | 2015 | 58000 | 10
IE | 2014 | 43100 | 11.9
IT | 2024 | 37300 | 6.5
IT | 2023 | 36300 | 7.7
IT | 2022 | 33900 | 8.1
IT | 2021 | 31200 | 9.5 [b]
IT | 2020 | 28100 | 9.2
IT | 2019 | 30200 | 9.9
IT | 2018 | 29700 | 10.6 [b]
IT | 2017 | 29100 | 11.2
IT | 2016 | 28400 | 11.7
IT | 2015 | 27600 | 11.9
IT | 2014 | 27100 | 12.7
LT | 2024 | 27400 | 7.1
LT | 2023 | 25900 | 6.9
LT | 2022 | 23700 | 6
LT | 2021 | 20200 | 7.1 [b]
LT | 2020 | 17900 | 8.5
LT | 2019 | 17500 | 6.3
LT | 2018 | 16300 | 6.2
LT | 2017 | 14900 | 7.1
LT | 2016 | 13500 | 7.9
LT | 2015 | 12900 | 9.1
LT | 2014 | 12400 | 10.7
LU | 2024 | 127000 [p] | 6.4
LU | 2023 | 123000 | 5.2
LU | 2022 | 117100 | 4.6
LU | 2021 | 113900 | 5.3 [b]
LU | 2020 | 102200 | 6.8
LU | 2019 | 100400 | 5.6
LU | 2018 | 98900 | 5.6
LU | 2017 | 97400 | 5.5
LU | 2016 | 96200 | 6.3
LU | 2015 | 95100 | 6.7 [b]
LU | 2014 | 92800 | 5.9
LV | 2024 | 21600 | 6.9
LV | 2023 | 21000 | 6.5
LV | 2022 | 19100 | 6.9
LV | 2021 | 17100 | 7.6 [b]
LV | 2020 | 15400 | 8.1
LV | 2019 | 15500 | 6.3
LV | 2018 | 14600 | 7.4
LV | 2017 | 13400 | 8.7
LV | 2016 | 12500 | 9.6
LV | 2015 | 12000 | 9.9
LV | 2014 | 11400 | 10.8
MT | 2024 | 40600 | 3.2
MT | 2023 | 37800 | 3.5
MT | 2022 | 33800 | 3.5
MT | 2021 | 32200 | 3.8 [b]
MT | 2020 | 27900 | 4.9
MT | 2019 | 28900 | 4.1
MT | 2018 | 28200 | 4
MT | 2017 | 26800 | 4
MT | 2016 | 23900 | 4.7
MT | 2015 | 23000 | 5.4
MT | 2014 | 20600 | 5.7
NL | 2024 | 62400 [p] | 3.7
NL | 2023 | 58700 | 3.6
NL | 2022 | 56100 | 3.5
NL | 2021 | 50800 | 4.2 [b]
NL | 2020 | 46800 | 3.8
NL | 2019 | 47800 | 3.4
NL | 2018 | 45700 | 3.8
NL | 2017 | 43800 | 4.9
NL | 2016 | 42300 | 6
NL | 2015 | 41300 | 6.9
NL | 2014 | 40200 | 7.4
PL | 2024 | 22600 [p] | 2.9
PL | 2023 | 20000 | 2.8
PL | 2022 | 17500 [b] | 2.9
PL | 2021 | 15800 | 3.4 [b]
PL | 2020 | 14300 [b] | 3.2
PL | 2019 | 14200 | 3.2 [b]
PL | 2018 | 13300 | 3.9
PL | 2017 | 12400 | 4.9
PL | 2016 | 11300 | 6.2 [b]
PL | 2015 | 11400 | 7.5
PL | 2014 | 10800 | 9
PT | 2024 | 27100 [p] | 6.5
PT | 2023 | 25600 | 6.5
PT | 2022 | 23300 | 6.2
PT | 2021 | 20800 | 6.7 [b]
PT | 2020 | 19400 | 6.9
PT | 2019 | 20700 | 6.5
PT | 2018 | 19800 | 7.1
PT | 2017 | 18900 | 9
PT | 2016 | 18000 | 11.2
PT | 2015 | 17300 | 12.6
PT | 2014 | 16600 | 14.1
RO | 2024 | 18600 [p] | 5.4
RO | 2023 | 16900 | 5.6
RO | 2022 | 14700 | 5.6
RO | 2021 | 12600 | 5.6 [b]
RO | 2020 | 11400 | 5
RO | 2019 | 11500 | 3.9
RO | 2018 | 10500 | 4.2
RO | 2017 | 9500 | 4.9
RO | 2016 | 8500 | 5.9
RO | 2015 | 8100 | 6.8
RO | 2014 | 7600 | 6.8
SE | 2024 | 52600 | 8.4
SE | 2023 | 50500 | 7.7
SE | 2022 | 52000 | 7.5
SE | 2021 | 51300 | 8.9 [b]
SE | 2020 | 46200 | 8.3
SE | 2019 | 46100 | 6.8
SE | 2018 | 45800 | 6.4 [b]
SE | 2017 | 47200 | 6.7
SE | 2016 | 46800 | 7
SE | 2015 | 46200 | 7.4
SE | 2014 | 44900 | 8
SI | 2024 | 31700 | 3.7
SI | 2023 | 30200 | 3.7
SI | 2022 | 27000 | 4
SI | 2021 | 24700 | 4.8 [b]
SI | 2020 | 22200 | 5
SI | 2019 | 23100 | 4.5
SI | 2018 | 21900 | 5.1
SI | 2017 | 20600 | 6.6
SI | 2016 | 19400 | 8
SI | 2015 | 18700 | 9
SI | 2014 | 18100 | 9.7
SK | 2024 | 23900 | 5.3
SK | 2023 | 22600 | 5.8
SK | 2022 | 20100 | 6.1
SK | 2021 | 18700 [b] | 6.8 [b]
SK | 2020 | 17300 | 6.7
SK | 2019 | 17300 | 5.8
SK | 2018 | 16600 | 6.5
SK | 2017 | 15600 | 8.1
SK | 2016 | 15000 | 9.7
SK | 2015 | 14800 | 11.5
SK | 2014 | 14100 | 13.2
[Source : eurostat (gdp_per_capita 10.02.2026, unemployment_rate 30.06.2026)]
```

## Answer

I now have everything I need — the eight target regions plus the EU27 (NUTS0) countries to build a reference line. Here's the convergence picture.

## Convergence of PL, RO, CZ, HU capitals + one regional region each, 2014–2024

**Region choice:** each capital region plus a contrasting *non-metropolitan* NUTS2 region — PL92 Mazowiecki (rural part of Mazovia), RO31 Sud‑Muntenia, CZ02 Střední Čechy, HU12 Pest. These illustrate both the converging capitals and the persistent within‑country gap.

### GDP per capita (€, current prices)

| Region | 2014 | 2020 | 2024* | % of EU27 avg '14 → '24 |
|---|---|---|---|---|
| **PL91** Warszawa (cap) | 23,000 | 28,900 | **45,300** | 88% → **109%** |
| **PL92** Mazowiecki reg. | 9,300 | 12,600 | **20,600** | 36% → 50% |
| **RO32** București‑Ilfov (cap) | 17,300 | 26,200 | **45,200** | 66% → **109%** |
| **RO31** Sud‑Muntenia | 6,400 | 8,600 | **13,200** | 24% → 32% |
| **CZ01** Praha (cap) | 33,200 | 46,300 | **62,400** | 127% → **150%** |
| **CZ02** Střední Čechy | 13,900 | 19,000 | **27,200** | 53% → 65% |
| **HU11** Budapest (cap) | 22,700 | 30,300 | **47,600** | 87% → **115%** |
| **HU12** Pest | 8,900 | 11,500 | **18,100** | 34% → 44% |
| *EU27 unweighted mean* | ~26,100 | ~27,000 | **~41,500** | 100% → 100% |

\* 2024 GDP figures are **provisional [p]** for PL91, PL92, RO31, RO32, HU11, HU12. The EU27 mean is a simple (unweighted) average of 27 members and is **upward‑skewed by Ireland and Luxembourg** (see data caveats), so treat "% of EU27 avg" as indicative, not the official PPS‑based ratio.

### Unemployment rate, 15–74 yrs (%)

| Region | 2014 | 2020 | 2024 | EU27 mean '14 → '24 |
|---|---|---|---|---|
| **PL91** Warszawa | 5.8 | 2.6 | **2.5** | 10.7 → 5.8 |
| **PL92** Mazowiecki reg. | 8.9 | 4.7 | **3.5** | |
| **RO32** București‑Ilfov | 7.2 | 4.7 | **2.2** | |
| **RO31** Sud‑Muntenia | 9.0 | 5.9 | **7.3** | |
| **CZ01** Praha | 2.5 | 2.3 | **1.8** | |
| **CZ02** Střední Čechy | 5.1 | 1.9 | **1.3** | |
| **HU11** Budapest | 6.0 | 3.3 | **2.6** | |
| **HU12** Pest | 6.5 | 3.3 | **3.1** | |

## Trend summary

- **All eight regions out‑grew the EU27 average** in GDP per capita (×1.9–2.6 vs ×1.6 for the EU27 mean). The convergence is real but concentrated.
- **Capitals have essentially reached or passed the EU average.** Warszawa, București‑Ilfov and Budapest all sit at ~109–115% of the (skewed) EU27 mean in 2024, having started at 66–88%. **Praha was already above the EU average in 2014 (127%) and diverged further upward to 150%** — it is a "frontier" region, not a converging one.
- **Non‑capital regions converged more slowly and remain far below the EU level** (32–65% of the mean by 2024). The **within‑country gap is the standout feature**: Romania's capital is at 109% of the EU mean while Sud‑Muntenia is at 32%; Hungary's Pest at 44% vs Budapest 115%.
- **Unemployment converged broadly.** Every region fell sharply (roughly to 1.3–7.3%), and all but one now sit **at or below the EU27 average (~5.8%)**. The Czech regions were already among the lowest in Europe and got still lower. The one clear exception is **Sud‑Muntenia (RO31) at 7.3%**, still above the EU mean — the laggard on the labour‑market side.
- **Dip then recovery:** all regions show the 2020 pandemic dip in GDP (e.g. Praha €46.3k → from €48.0k in 2019) and a rebound by 2022–2024.

## Breaks in series and provisional values

- **Break in series [b]** — the mark is heavily concentrated around **2020–2021**, consistent with pandemic‑era statistical revisions (and, for GDP, the 2021 reference‑year rebase). In the eight target regions:
  - *GDP per capita:* **PL91** flagged [b] for 2020, 2021 and 2022 (the cleanest break in this set).
  - *Unemployment:* [b] on the **2021** values of CZ01, CZ02, HU11, HU12, RO31, RO32 (and country‑wide for most EU members); plus isolated earlier breaks (HU11/HU12 2018; PL91/PL92 2016, 2019, 2020).
  - Practical effect: **values immediately around 2020–2021 are not strictly comparable** to neighbouring years; the 2014→2024 endpoint comparison is the robust one.
- **Provisional [p]** — **all 2024 GDP per‑capita figures are provisional** (PL91, PL92, RO31, RO32, HU11, HU12). 2024 values may still shift on revision; unemployment 2024 values are final.
- **Estimate [e] / outlier caveat** — at NUTS0 level, **Ireland's 2024 GDP per capita is flagged [e] (estimated, €104,500)** and Luxembourg's €127,000; both distort the EU27 mean used above. Greece's (EL) GDP series is marked [p] for the entire 2014–2024 window. If you want a cleaner benchmark, I can recompute the EU reference **excluding IE and LU**, or switch to the official **PPS, % of EU average** indicator instead of current‑€ unweighted means.

Want me to (a) rebase the reference to PPS‑%‑of‑EU‑average, (b) drop IE/LU from the benchmark, or (c) add the whole‑country NUTS0 lines for PL/RO/CZ/HU alongside the regions?

