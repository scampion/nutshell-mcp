# Example 9 — Schools and children

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> Where in France and Germany are schools scarcest relative to the number of children? Compare NUTS2 regions using the population aged under 15 and the number of schools. Give the 5 regions with the fewest schools per 1,000 children and the 5 with the most, and explain the limits of this comparison.

## Tool calls

**1. `search_indicators(query="population under 15")`**

```
id | label | unité | freq | niveaux geo | source
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**2. `search_indicators(query="number of schools")`**

```
id | label | unité | freq | niveaux geo | source
schools_count | Établissements scolaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
```

**3. `search_indicators(query="population 0-14")`**

```
id | label | unité | freq | niveaux geo | source
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**4. `search_indicators(query="jeunes enfants age")`**

```
id | label | unité | freq | niveaux geo | source
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
```

**5. `search_datasets(query="population by age NUTS2")`**

```
Aucun dataset ne contient tous les termes de 'population by age NUTS2' ; résultats contenant au moins l'un d'eux :
sbs_r_nuts2021 | Enterprises by NUTS 2 region and NACE Rev.2 activity | 2021–2023
tour_cap_nuts2 | Establishments, bedrooms and bed-places in tourist accommodation, by NUTS 2 region | 1990–2026
tour_cap_nuts2dc | Establishments, bedrooms and bed-places in tourist accommodation, by degree of urbanisation and coastal/non-coastal area and NUTS 2 region | 2012–2026
tps00010 | Population by age group | 2014–2025
ilc_lvps03 | Distribution of population by work intensity of the household (population aged 0 to 64 years) | 2014–2025
ilc_lvps15 | Distribution of population by group of citizenship and tenure status (population aged 18 and over) | 2003–2025
cens_hnmga | Population by sex and age | 1981–2001
ilc_lvps16 | Distribution of population by group of country of birth and tenure status (population aged 18 and over) | 2003–2025
cens_21m | Population by age and marital status | 2021–2021
cens_hnctz | Population by sex, age and citizenship | 1991–2001
```

**6. `list_zones(level="NUTS2", parent="FR")`**

```
geo_code | name | level | parent
FR10 | Ile-de-France | NUTS2 | FR1
FRB0 | Centre — Val de Loire | NUTS2 | FRB
FRC1 | Bourgogne | NUTS2 | FRC
FRC2 | Franche-Comté | NUTS2 | FRC
FRD1 | Basse-Normandie  | NUTS2 | FRD
FRD2 | Haute-Normandie  | NUTS2 | FRD
FRE1 | Nord-Pas de Calais | NUTS2 | FRE
FRE2 | Picardie | NUTS2 | FRE
FRF1 | Alsace | NUTS2 | FRF
FRF2 | Champagne-Ardenne | NUTS2 | FRF
FRF3 | Lorraine | NUTS2 | FRF
FRG0 | Pays de la Loire | NUTS2 | FRG
FRH0 | Bretagne | NUTS2 | FRH
FRI1 | Aquitaine | NUTS2 | FRI
FRI2 | Limousin | NUTS2 | FRI
FRI3 | Poitou-Charentes | NUTS2 | FRI
FRJ1 | Languedoc-Roussillon | NUTS2 | FRJ
FRJ2 | Midi-Pyrénées | NUTS2 | FRJ
FRK1 | Auvergne | NUTS2 | FRK
FRK2 | Rhône-Alpes | NUTS2 | FRK
FRL0 | Provence-Alpes-Côte d’Azur | NUTS2 | FRL
FRM0 | Corse | NUTS2 | FRM
FRY1 | Guadeloupe | NUTS2 | FRY
FRY2 | Martinique  | NUTS2 | FRY
FRY3 | Guyane | NUTS2 | FRY
FRY4 | La Réunion  | NUTS2 | FRY
FRY5 | Mayotte | NUTS2 | FRY
```

**7. `list_zones(level="NUTS2", parent="DE")`**

```
geo_code | name | level | parent
DE11 | Stuttgart | NUTS2 | DE1
DE12 | Karlsruhe | NUTS2 | DE1
DE13 | Freiburg | NUTS2 | DE1
DE14 | Tübingen | NUTS2 | DE1
DE21 | Oberbayern | NUTS2 | DE2
DE22 | Niederbayern | NUTS2 | DE2
DE23 | Oberpfalz | NUTS2 | DE2
DE24 | Oberfranken | NUTS2 | DE2
DE25 | Mittelfranken | NUTS2 | DE2
DE26 | Unterfranken | NUTS2 | DE2
DE27 | Schwaben | NUTS2 | DE2
DE30 | Berlin | NUTS2 | DE3
DE40 | Brandenburg | NUTS2 | DE4
DE50 | Bremen | NUTS2 | DE5
DE60 | Hamburg | NUTS2 | DE6
DE71 | Darmstadt | NUTS2 | DE7
DE72 | Gießen | NUTS2 | DE7
DE73 | Kassel | NUTS2 | DE7
DE80 | Mecklenburg-Vorpommern | NUTS2 | DE8
DE91 | Braunschweig | NUTS2 | DE9
DE92 | Hannover | NUTS2 | DE9
DE93 | Lüneburg | NUTS2 | DE9
DE94 | Weser-Ems | NUTS2 | DE9
DEA1 | Düsseldorf | NUTS2 | DEA
DEA2 | Köln | NUTS2 | DEA
DEA3 | Münster | NUTS2 | DEA
DEA4 | Detmold | NUTS2 | DEA
DEA5 | Arnsberg | NUTS2 | DEA
DEB1 | Koblenz | NUTS2 | DEB
DEB2 | Trier | NUTS2 | DEB
DEB3 | Rheinhessen-Pfalz | NUTS2 | DEB
DEC0 | Saarland | NUTS2 | DEC
DED2 | Dresden | NUTS2 | DED
DED4 | Chemnitz | NUTS2 | DED
DED5 | Leipzig | NUTS2 | DED
DEE0 | Sachsen-Anhalt | NUTS2 | DEE
DEF0 | Schleswig-Holstein | NUTS2 | DEF
DEG0 | Thüringen | NUTS2 | DEG
```

**8. `get_structure(dataset="demo_pjanage")`**

```
Structure de 'demo_pjanage' absente du cache et mode offline actif. Lancer : python -m nutshell_mcp.mirror --datasets demo_pjanage
```

**9. `search_datasets(query="annual population age groups", limit=15)`**

```
Aucun dataset ne contient tous les termes de 'annual population age groups' ; résultats contenant au moins l'un d'eux :
tps00010 | Population by age group | 2014–2025
cens_21ah | Population by groups of current activity status, age groups and household status | 2021–2021
ilc_caindother | Other types of childcare by age group and duration - % over the population of each age group | 2005–2025
ilc_caparents | Children cared only by their parents by age group - % over the population of each age group | 2005–2025
eq_pop03 | Population structure by detailed age group | 2014–2025
ilc_caindformal | Children in formal childcare or education by age group and duration - % over the population of each age group | 2005–2025
cens_91sctz | Population by sex, age group and citizenship | 1991–1991
cens_91actz | Active population by citizenship and age group | 1991–1991
cens_21ctza_r2 | Population by groups of country of citizenship, age groups, groups of current activity status and NUTS 2 region | 2021–2021
cens_21coba_r2 | Population by groups of country of birth, age groups, groups of current activity status and NUTS 2 region | 2021–2021
cens_21ctzo_r2 | Population by groups of country of citizenship, age groups, occupation and NUTS 2 region | 2021–2021
cens_21cobo_r2 | Population by groups of country of birth, age groups, occupation and NUTS 2 region | 2021–2021
ilc_lvps15 | Distribution of population by group of citizenship and tenure status (population aged 18 and over) | 2003–2025
cens_01nsctz | Population by sex, age group and country of citizenship | 2001–2001
cens_01nscbirth | Population by sex, age group and country of birth | 2001–2001
```

**10. `get_structure(dataset="tps00010")`**

```
Dataset tps00010 — dimensions :
- freq [Time frequency] : A (Annual)
- indic_de [Demographic indicator] : PC_Y0_14 (Proportion of population aged 0-14 years), PC_Y15_24 (Proportion of population aged 15-24 years), PC_Y25_49 (Proportion of population aged 25-49 years), PC_Y50_64 (Proportion of population aged 50-64 years), PC_Y65_79 (Proportion of population aged 65-79 years), PC_Y80_MAX (Proportion of population aged 80 years and more)
- geo [Geopolitical entity (reporting)] : EU27_2020 (European Union - 27 countries (from 2020)), EA21 (Euro area – 21 countries (from 2026)), EA20 (Euro area – 20 countries (2023-2025)), EA19 (Euro area - 19 countries  (2015-2022)), BE (Belgium), BG (Bulgaria), CZ (Czechia), DK (Denmark), DE (Germany), EE (Estonia), IE (Ireland), EL (Greece), ES (Spain), FR (France), HR (Croatia), IT (Italy), CY (Cyprus), LV (Latvia), LT (Lithuania), LU (Luxembourg), HU (Hungary), MT (Malta), NL (Netherlands), AT (Austria), PL (Poland) … et 28 autres (voir list_codes)
- time [Time] : 2014 → 2025 (filtrer avec time_from / time_to)
```

**11. `get_structure(dataset="eq_pop03")`**

```
Dataset eq_pop03 — dimensions :
- freq [Time frequency] : A (Annual)
- indic_de [Demographic indicator] : PC_Y0_17 (Proportion of population aged 0-17 years), PC_Y15_24 (Proportion of population aged 15-24 years), PC_Y25_49 (Proportion of population aged 25-49 years), PC_Y50_64 (Proportion of population aged 50-64 years), PC_Y65_MAX (Proportion of population aged 65 years and more)
- geo [Geopolitical entity (reporting)] : EU27_2020 (European Union - 27 countries (from 2020)), EA21 (Euro area – 21 countries (from 2026)), EA20 (Euro area – 20 countries (2023-2025)), EA19 (Euro area - 19 countries  (2015-2022)), BE (Belgium), BG (Bulgaria), CZ (Czechia), DK (Denmark), DE (Germany), EE (Estonia), IE (Ireland), EL (Greece), ES (Spain), FR (France), HR (Croatia), IT (Italy), CY (Cyprus), LV (Latvia), LT (Lithuania), LU (Luxembourg), HU (Hungary), MT (Malta), NL (Netherlands), AT (Austria), PL (Poland) … et 28 autres (voir list_codes)
- time [Time] : 2014 → 2025 (filtrer avec time_from / time_to)
```

**12. `search_datasets(query="population age NUTS", limit=15)`**

```
cens_21agr2 | Population by age and NUTS 2 region | 2021–2021
cens_11ag_r3 | Population by single year of age and NUTS 3 region | 2011–2011
cens_01rhtype | Population by sex, age group, household status and NUTS 3 region | 2001–2001
cens_21a_r2 | Population by current activity status, age and NUTS 2 region | 2021–2021
cens_21ua_ar3 | Population with Ukrainian citizenship by age and NUTS 3 region | 2021–2021
demo_r_d2jan | Population on 1 January by age, sex and NUTS 2 region | 1990–2025
cens_01rapop | Population by sex, age group, current activity status and NUTS 3 region | 2001–2001
cens_01rhsize | Population by sex, age group, size of household and NUTS 3 region | 2001–2001
cens_21ctz_r3 | Population by country of citizenship, age groups and NUTS 3 region | 2021–2021
cens_21cob_r3 | Population by country of birth, age groups and NUTS 3 region | 2021–2021
cens_21m_r3 | Population by marital status, broad age groups and NUTS 3 region | 2021–2021
cens_21f_r3 | Population by family status, broad age groups and NUTS 3 region | 2021–2021
demo_r_pjangroup | Population on 1 January by age group, sex and NUTS 2 region | 1990–2025
demo_r_pjangrp3 | Population on 1 January by age group, sex and NUTS 3 region | 2014–2025
cens_21cobe_r2 | Population by country of birth, age groups, education and NUTS 2 region | 2021–2021
```

**13. `search_datasets(query="population by 5 years age", limit=15)`**

```
cens_21ua_a5 | Population with Ukrainian citizenship by 5-year age group | 2021–2021
cens_21ua_yae | Population with Ukrainian citizenship by 5-year age group and year of arrival in the country | 2021–2021
cens_21ua_ms | Population with Ukrainian citizenship by 5-year age group and marital status | 2021–2021
cens_21ua_a5r3 | Population with Ukrainian citizenship by 5-year age group and NUTS 3 region | 2021–2021
cens_21ua_msr3 | Population with Ukrainian citizenship by 5-year age group, marital status and NUTS 3 region | 2021–2021
ilc_lvhl11 | Persons living in households with very low work intensity by age and sex (population aged 0 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl17 | Persons living in households with very low work intensity by tenure status (population aged 0 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl23 | Persons living in households with very low work intensity by degree of urbanisation (population aged 0 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl14 | Persons living in households with very low work intensity by educational attainment level (population aged 18 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl15 | Persons living in households with very low work intensity by group of citizenship (population aged 18 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl21 | Persons living in households with very low work intensity by NUTS 2 region (population aged 0 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl12 | Persons living in households with very low work intensity by most frequent activity status (population aged 18 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl13 | Persons living in households with very low work intensity by income quantile and household composition (population aged 0 to 59 years) - EU 2020 strategy | 2003–2025
ilc_lvhl16 | Persons living in households with very low work intensity by group of country of birth (population aged 18 to 59 years) - EU 2020 strategy | 2003–2025
```

**14. `get_structure(dataset="demo_r_pjangroup")`**

```
Dataset demo_r_pjangroup — dimensions :
- freq [Time frequency] : A (Annual)
- unit [Unit of measure] : NR (Number)
- sex [Sex] : T (Total), M (Males), F (Females)
- age [Age class] : TOTAL (Total), Y_LT5 (Less than 5 years), Y5-9 (From 5 to 9 years), Y10-14 (From 10 to 14 years), Y15-19 (From 15 to 19 years), Y20-24 (From 20 to 24 years), Y25-29 (From 25 to 29 years), Y30-34 (From 30 to 34 years), Y35-39 (From 35 to 39 years), Y40-44 (From 40 to 44 years), Y45-49 (From 45 to 49 years), Y50-54 (From 50 to 54 years), Y55-59 (From 55 to 59 years), Y60-64 (From 60 to 64 years), Y65-69 (From 65 to 69 years), Y70-74 (From 70 to 74 years), Y75-79 (From 75 to 79 years), Y_GE75 (75 years or over), Y80-84 (From 80 to 84 years), Y_GE80 (80 years or over), Y_GE85 (85 years or over), UNK (Unknown)
- geo [Geopolitical entity (reporting)] : EU27_2020 (European Union - 27 countries (from 2020)), EU28 (European Union - 28 countries (2013-2020)), EU27_2007 (European Union - 27 countries (2007-2013)), BE (Belgium), BE1 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE10 (Région de Bruxelles-Capitale/Brussels Hoofdstedelijk Gewest), BE2 (Vlaams Gewest), BE21 (Prov. Antwerpen), BE22 (Prov. Limburg (BE)), BE23 (Prov. Oost-Vlaanderen), BE24 (Prov. Vlaams-Brabant), BE25 (Prov. West-Vlaanderen), BE3 (Région wallonne), BE31 (Prov. Brabant wallon), BE32 (Prov. Hainaut), BE33 (Prov. Liège), BE34 (Prov. Luxembourg (BE)), BE35 (Prov. Namur), BG (Bulgaria), BG3 (Severna i Yugoiztochna Bulgaria), BG31 (Severozapaden), BG32 (Severen tsentralen), BG33 (Severoiztochen), BG34 (Yugoiztochen), BG4 (Yugozapadna i Yuzhna tsentralna Bulgaria) … et 506 autres (voir list_codes)
- time [Time] : 1990 → 2025 (filtrer avec time_from / time_to)
```

**15. `get_indicators(indicators=["schools_count"], zones=["FR10", "FRB0", "FRC1", "FRC2", "FRD1", "FRD2", "FRE1", "FRE2", "FRF1", "FRF2", "FRF3", "FRG0", "FRH0", "FRI1", "FRI2", "FRI3", "FRJ1", "FRJ2", "FRK1", "FRK2", "FRL0", "FRM0", "DE11", "DE12", "DE13", "DE14", "DE21", "DE22", "DE23", "DE24", "DE25", "DE26", "DE27", "DE30", "DE40", "DE50", "DE60", "DE71", "DE72", "DE73", "DE80", "DE91", "DE92", "DE93", "DE94", "DEA1", "DEA2", "DEA3", "DEA4", "DEA5", "DEB1", "DEB2", "DEB3", "DEC0", "DED2", "DED4", "DED5", "DEE0", "DEF0", "DEG0"])`**

```
geo_code | time | schools_count
DE11 | 2026-08 | 1881 [osm_completeness_unknown]
DE12 | 2026-08 | 1176 [osm_completeness_unknown]
DE13 | 2026-08 | 1224 [osm_completeness_unknown]
DE14 | 2026-08 | 1010 [osm_completeness_unknown]
DE21 | 2026-08 | 1845 [osm_completeness_unknown]
DE22 | 2026-08 | 568 [osm_completeness_unknown]
DE23 | 2026-08 | 547 [osm_completeness_unknown]
DE24 | 2026-08 | 550 [osm_completeness_unknown]
DE25 | 2026-08 | 688 [osm_completeness_unknown]
DE26 | 2026-08 | 692 [osm_completeness_unknown]
DE27 | 2026-08 | 817 [osm_completeness_unknown]
DE30 | 2026-08 | 1077 [osm_completeness_unknown]
DE40 | 2026-08 | 1057 [osm_completeness_unknown]
DE50 | 2026-08 | 257 [osm_completeness_unknown]
DE60 | 2026-08 | 561 [osm_completeness_unknown]
DE71 | 2026-08 | 1391 [osm_completeness_unknown]
DE72 | 2026-08 | 465 [osm_completeness_unknown]
DE73 | 2026-08 | 572 [osm_completeness_unknown]
DE80 | 2026-08 | 689 [osm_completeness_unknown]
DE91 | 2026-08 | 831 [osm_completeness_unknown]
DE92 | 2026-08 | 841 [osm_completeness_unknown]
DE93 | 2026-08 | 840 [osm_completeness_unknown]
DE94 | 2026-08 | 1422 [osm_completeness_unknown]
DEA1 | 2026-08 | 2040 [osm_completeness_unknown]
DEA2 | 2026-08 | 1718 [osm_completeness_unknown]
DEA3 | 2026-08 | 1117 [osm_completeness_unknown]
DEA4 | 2026-08 | 994 [osm_completeness_unknown]
DEA5 | 2026-08 | 1540 [osm_completeness_unknown]
DEB1 | 2026-08 | 679 [osm_completeness_unknown]
DEB2 | 2026-08 | 260 [osm_completeness_unknown]
DEB3 | 2026-08 | 808 [osm_completeness_unknown]
DEC0 | 2026-08 | 417 [osm_completeness_unknown]
DED2 | 2026-08 | 781 [osm_completeness_unknown]
DED4 | 2026-08 | 707 [osm_completeness_unknown]
DED5 | 2026-08 | 468 [osm_completeness_unknown]
DEE0 | 2026-08 | 1087 [osm_completeness_unknown]
DEF0 | 2026-08 | 1163 [osm_completeness_unknown]
DEG0 | 2026-08 | 1108 [osm_completeness_unknown]
FR10 | 2026-08 | 10023 [osm_completeness_unknown]
FRB0 | 2026-08 | 2797 [osm_completeness_unknown]
FRC1 | 2026-08 | 2434 [osm_completeness_unknown]
FRC2 | 2026-08 | 1647 [osm_completeness_unknown]
FRD1 | 2026-08 | 1457 [osm_completeness_unknown]
FRD2 | 2026-08 | 1965 [osm_completeness_unknown]
FRE1 | 2026-08 | 4326 [osm_completeness_unknown]
FRE2 | 2026-08 | 2018 [osm_completeness_unknown]
FRF1 | 2026-08 | 1877 [osm_completeness_unknown]
FRF2 | 2026-08 | 1375 [osm_completeness_unknown]
FRF3 | 2026-08 | 2626 [osm_completeness_unknown]
FRG0 | 2026-08 | 3753 [osm_completeness_unknown]
FRH0 | 2026-08 | 3264 [osm_completeness_unknown]
FRI1 | 2026-08 | 3471 [osm_completeness_unknown]
FRI2 | 2026-08 | 934 [osm_completeness_unknown]
FRI3 | 2026-08 | 1783 [osm_completeness_unknown]
FRJ1 | 2026-08 | 2651 [osm_completeness_unknown]
FRJ2 | 2026-08 | 3244 [osm_completeness_unknown]
FRK1 | 2026-08 | 1666 [osm_completeness_unknown]
FRK2 | 2026-08 | 7444 [osm_completeness_unknown]
FRL0 | 2026-08 | 3875 [osm_completeness_unknown]
FRM0 | 2026-08 | 320 [osm_completeness_unknown]
[Source : osm (extrait 2026-08)]
```

**16. `query_data(dataset="demo_r_pjangroup", filters={"geo": "FR10+FRB0+FRC1+FRC2+FRD1+FRD2+FRE1+FRE2+FRF1+FRF2+FRF3+FRG0+FRH0+FRI1+FRI2+FRI3+FRJ1+FRJ2+FRK1+FRK2+FRL0+FRM0+DE11+DE12+DE13+DE14+DE21+DE22+DE23+DE24+DE25+DE26+DE27+DE30+DE40+DE50+DE60+DE71+DE72+DE73+DE80+DE91+DE92+DE93+DE94+DEA1+DEA2+DEA3+DEA4+DEA5+DEB1+DEB2+DEB3+DEC0+DED2+DED4+DED5+DEE0+DEF0+DEG0", "age": "Y_LT5+Y5-9+Y10-14", "sex": "T"}, time_from="2024", time_to="2025")`**

```
freq | unit | sex | age | geo | time | value | flag
A | NR | T | Y5-9 | DE60 | 2024 | 91357.0 | 
A | NR | T | Y5-9 | FRE2 | 2024 | 117004.0 | p
A | NR | T | Y5-9 | FR10 | 2024 | 739467.0 | p
A | NR | T | Y5-9 | DEA1 | 2024 | 256170.0 | 
A | NR | T | Y5-9 | FRB0 | 2024 | 145328.0 | p
A | NR | T | Y5-9 | DE23 | 2024 | 52346.0 | 
A | NR | T | Y5-9 | FRC1 | 2024 | 84730.0 | p
A | NR | T | Y5-9 | DEA2 | 2024 | 214450.0 | 
A | NR | T | Y5-9 | FRC2 | 2024 | 67594.0 | p
A | NR | T | Y5-9 | DE14 | 2024 | 95693.0 | 
A | NR | T | Y5-9 | FRD1 | 2024 | 77871.0 | p
A | NR | T | Y5-9 | DEA3 | 2024 | 132524.0 | 
A | NR | T | Y5-9 | FRD2 | 2024 | 111465.0 | p
A | NR | T | Y5-9 | DE26 | 2024 | 61915.0 | 
A | NR | T | Y5-9 | FRE1 | 2024 | 246363.0 | p
A | NR | T | Y5-9 | DEA4 | 2024 | 103852.0 | 
A | NR | T | Y5-9 | DE50 | 2024 | 35523.0 | 
A | NR | T | Y_LT5 | DE30 | 2024 | 173699.0 | 
A | NR | T | Y5-9 | DEG0 | 2024 | 96277.0 | 
A | NR | T | Y5-9 | FRM0 | 2024 | 18341.0 | p
A | NR | T | Y5-9 | DE30 | 2024 | 176060.0 | 
A | NR | T | Y5-9 | DEB3 | 2024 | 100480.0 | 
A | NR | T | Y5-9 | DE91 | 2024 | 74957.0 | 
A | NR | T | Y5-9 | DEE0 | 2024 | 93904.0 | 
A | NR | T | Y5-9 | DE21 | 2024 | 231430.0 | 
A | NR | T | Y5-9 | DEF0 | 2024 | 138234.0 | 
A | NR | T | Y5-9 | DE92 | 2024 | 100148.0 | 
A | NR | T | Y_LT5 | FRF1 | 2024 | 90570.0 | p
A | NR | T | Y5-9 | DE40 | 2024 | 122942.0 | 
A | NR | T | Y5-9 | DE11 | 2024 | 207292.0 | 
A | NR | T | Y5-9 | DE93 | 2024 | 84436.0 | 
A | NR | T | Y5-9 | DE12 | 2024 | 135822.0 | 
A | NR | T | Y5-9 | DE25 | 2024 | 87575.0 | 
A | NR | T | Y5-9 | DE13 | 2024 | 117203.0 | 
A | NR | T | Y5-9 | DE94 | 2024 | 126660.0 | 
A | NR | T | Y_LT5 | DE92 | 2024 | 95121.0 | 
A | NR | T | Y_LT5 | FRI1 | 2024 | 159991.0 | p
A | NR | T | Y_LT5 | DE25 | 2024 | 84716.0 | 
A | NR | T | Y_LT5 | DE13 | 2024 | 113167.0 | 
A | NR | T | Y_LT5 | DE23 | 2024 | 52195.0 | 
A | NR | T | Y_LT5 | FRI2 | 2024 | 29523.0 | p
A | NR | T | Y_LT5 | DED5 | 2024 | 45245.0 | 
A | NR | T | Y_LT5 | DEB3 | 2024 | 95685.0 | 
A | NR | T | Y_LT5 | FRC1 | 2024 | 71535.0 | p
A | NR | T | Y_LT5 | DE93 | 2024 | 78506.0 | 
A | NR | T | Y10-14 | DEC0 | 2024 | 42627.0 | 
A | NR | T | Y10-14 | DE11 | 2024 | 195212.0 | 
A | NR | T | Y10-14 | DED2 | 2024 | 78283.0 | 
A | NR | T | Y10-14 | DE72 | 2024 | 46965.0 | 
A | NR | T | Y10-14 | DED4 | 2024 | 63975.0 | 
A | NR | T | Y10-14 | DE25 | 2024 | 80521.0 | 
A | NR | T | Y10-14 | DED5 | 2024 | 48738.0 | 
A | NR | T | Y10-14 | DE73 | 2024 | 54142.0 | 
A | NR | T | Y_LT5 | DEA2 | 2024 | 203991.0 | 
A | NR | T | Y_LT5 | DEC0 | 2024 | 42053.0 | 
A | NR | T | Y_LT5 | DEA1 | 2024 | 240726.0 | 
A | NR | T | Y_LT5 | FRF2 | 2024 | 62584.0 | p
A | NR | T | Y_LT5 | DE11 | 2024 | 204356.0 | 
A | NR | T | Y_LT5 | DE91 | 2024 | 71243.0 | 
A | NR | T | Y_LT5 | DE12 | 2024 | 130734.0 | 
A | NR | T | Y_LT5 | FRF3 | 2024 | 105171.0 | p
A | NR | T | Y_LT5 | DED2 | 2024 | 61685.0 | 
A | NR | T | Y5-9 | DED4 | 2024 | 63132.0 | 
A | NR | T | Y_LT5 | FRG0 | 2024 | 194817.0 | p
A | NR | T | Y_LT5 | DE72 | 2024 | 46620.0 | 
A | NR | T | Y_LT5 | FRB0 | 2024 | 125343.0 | p
A | NR | T | Y_LT5 | DE40 | 2024 | 98243.0 | 
A | NR | T | Y_LT5 | FRH0 | 2024 | 157468.0 | p
A | NR | T | Y_LT5 | DED4 | 2024 | 51024.0 | 
A | NR | T | Y_LT5 | DEA3 | 2024 | 128414.0 | 
A | NR | T | Y_LT5 | DE21 | 2024 | 231705.0 | 
A | NR | T | Y10-14 | DE23 | 2024 | 49064.0 | 
A | NR | T | Y10-14 | FRI2 | 2024 | 39105.0 | p
A | NR | T | Y_LT5 | FRD2 | 2024 | 96085.0 | p
A | NR | T | Y10-14 | DEB3 | 2024 | 93431.0 | 
A | NR | T | Y10-14 | FRI3 | 2024 | 104934.0 | p
A | NR | T | Y_LT5 | FRJ2 | 2024 | 143857.0 | p
A | NR | T | Y10-14 | DE50 | 2024 | 31804.0 | 
A | NR | T | Y10-14 | FRJ1 | 2024 | 173284.0 | p
A | NR | T | Y_LT5 | DEA5 | 2024 | 163839.0 | 
A | NR | T | Y10-14 | DEA5 | 2024 | 161439.0 | 
A | NR | T | Y10-14 | FRJ2 | 2024 | 185551.0 | p
A | NR | T | Y_LT5 | DE14 | 2024 | 94089.0 | 
A | NR | T | Y10-14 | DE14 | 2024 | 90042.0 | 
A | NR | T | Y10-14 | FRK1 | 2024 | 76659.0 | p
A | NR | T | Y10-14 | DEB1 | 2024 | 68841.0 | 
A | NR | T | Y10-14 | FRK2 | 2024 | 438949.0 | p
A | NR | T | Y_LT5 | FRK1 | 2024 | 58505.0 | p
A | NR | T | Y10-14 | DEA2 | 2024 | 204135.0 | 
A | NR | T | Y10-14 | DE30 | 2024 | 163535.0 | 
A | NR | T | Y10-14 | FRF1 | 2024 | 115401.0 | p
A | NR | T | Y_LT5 | DE73 | 2024 | 53244.0 | 
A | NR | T | Y10-14 | DEA1 | 2024 | 240401.0 | 
A | NR | T | Y10-14 | FRF2 | 2024 | 80075.0 | p
A | NR | T | Y_LT5 | DE50 | 2024 | 34613.0 | 
A | NR | T | Y10-14 | DE12 | 2024 | 128038.0 | 
A | NR | T | Y10-14 | FRF3 | 2024 | 136670.0 | p
A | NR | T | Y10-14 | DE60 | 2024 | 82758.0 | 
A | NR | T | Y10-14 | FRG0 | 2024 | 251980.0 | p
A | NR | T | Y_LT5 | FRJ1 | 2024 | 134579.0 | p
A | NR | T | Y10-14 | DE40 | 2024 | 120462.0 | 
A | NR | T | Y10-14 | FRH0 | 2024 | 209317.0 | p
A | NR | T | Y_LT5 | DEE0 | 2024 | 78034.0 | 
A | NR | T | Y10-14 | DEA3 | 2024 | 124079.0 | 
A | NR | T | Y10-14 | FRI1 | 2024 | 204302.0 | p
A | NR | T | Y5-9 | FRJ1 | 2024 | 156595.0 | p
A | NR | T | Y5-9 | FRH0 | 2024 | 186215.0 | p
A | NR | T | Y5-9 | DEB2 | 2024 | 25124.0 | 
A | NR | T | Y5-9 | FRI1 | 2024 | 185889.0 | p
A | NR | T | Y5-9 | DE27 | 2024 | 96886.0 | 
A | NR | T | Y5-9 | FRI2 | 2024 | 34528.0 | p
A | NR | T | Y5-9 | DED5 | 2024 | 52470.0 | 
A | NR | T | Y5-9 | FRI3 | 2024 | 92412.0 | p
A | NR | T | Y5-9 | DE73 | 2024 | 56463.0 | 
A | NR | T | Y5-9 | DE72 | 2024 | 49055.0 | 
A | NR | T | Y5-9 | DEC0 | 2024 | 44622.0 | 
A | NR | T | Y5-9 | FRJ2 | 2024 | 168650.0 | p
A | NR | T | Y5-9 | DE24 | 2024 | 47796.0 | 
A | NR | T | Y5-9 | FRK1 | 2024 | 70206.0 | p
A | NR | T | Y5-9 | DED2 | 2024 | 77634.0 | 
A | NR | T | Y5-9 | FRK2 | 2024 | 410753.0 | p
A | NR | T | Y5-9 | DE80 | 2024 | 70389.0 | 
A | NR | T | Y5-9 | FRL0 | 2024 | 274878.0 | p
A | NR | T | Y5-9 | DE71 | 2024 | 199628.0 | 
A | NR | T | Y10-14 | FRL0 | 2024 | 301046.0 | p
A | NR | T | Y_LT5 | DEF0 | 2024 | 125509.0 | 
A | NR | T | Y10-14 | DEB2 | 2024 | 24031.0 | 
A | NR | T | Y10-14 | FRM0 | 2024 | 19245.0 | p
A | NR | T | Y_LT5 | DEB1 | 2024 | 70143.0 | 
A | NR | T | Y10-14 | DE24 | 2024 | 45094.0 | 
A | NR | T | Y10-14 | DEA4 | 2024 | 99697.0 | 
A | NR | T | Y10-14 | DE71 | 2024 | 190957.0 | 
A | NR | T | Y_LT5 | FRI3 | 2024 | 76523.0 | p
A | NR | T | Y5-9 | FRF1 | 2024 | 105251.0 | p
A | NR | T | Y5-9 | DEA5 | 2024 | 170773.0 | 
A | NR | T | Y5-9 | FRF2 | 2024 | 71853.0 | p
A | NR | T | Y5-9 | DE22 | 2024 | 59158.0 | 
A | NR | T | Y5-9 | FRF3 | 2024 | 125997.0 | p
A | NR | T | Y5-9 | DEB1 | 2024 | 73700.0 | 
A | NR | T | Y5-9 | FRG0 | 2024 | 224086.0 | p
A | NR | T | Y_LT5 | FRC2 | 2024 | 55365.0 | p
A | NR | T | Y10-14 | FRC1 | 2024 | 92360.0 | p
A | NR | T | Y10-14 | DE92 | 2024 | 95456.0 | 
A | NR | T | Y10-14 | FRC2 | 2024 | 73731.0 | p
A | NR | T | Y10-14 | DE27 | 2024 | 87953.0 | 
A | NR | T | Y10-14 | FRD1 | 2024 | 87170.0 | p
A | NR | T | Y10-14 | DE93 | 2024 | 80812.0 | 
A | NR | T | Y10-14 | FRD2 | 2024 | 120436.0 | p
A | NR | T | Y10-14 | DE22 | 2024 | 56120.0 | 
A | NR | T | Y10-14 | FRE1 | 2024 | 271507.0 | p
A | NR | T | Y10-14 | DE94 | 2024 | 120997.0 | 
A | NR | T | Y_LT5 | FRE1 | 2024 | 212770.0 | p
A | NR | T | Y10-14 | DE26 | 2024 | 57243.0 | 
A | NR | T | Y_LT5 | FR10 | 2024 | 708505.0 | p
A | NR | T | Y_LT5 | DE27 | 2024 | 96408.0 | 
A | NR | T | Y_LT5 | DE94 | 2024 | 122442.0 | 
A | NR | T | Y10-14 | DE21 | 2024 | 217893.0 | 
A | NR | T | Y_LT5 | DE26 | 2024 | 61084.0 | 
A | NR | T | Y_LT5 | DE71 | 2024 | 189626.0 | 
A | NR | T | Y_LT5 | DEA4 | 2024 | 98839.0 | 
A | NR | T | Y_LT5 | FRD1 | 2024 | 66699.0 | p
A | NR | T | Y_LT5 | DE24 | 2024 | 46035.0 | 
A | NR | T | Y_LT5 | FRE2 | 2024 | 100024.0 | p
A | NR | T | Y_LT5 | FRM0 | 2024 | 15409.0 | p
A | NR | T | Y_LT5 | DE22 | 2024 | 58890.0 | 
A | NR | T | Y_LT5 | DEB2 | 2024 | 23307.0 | 
A | NR | T | Y_LT5 | DEG0 | 2024 | 76928.0 | 
A | NR | T | Y_LT5 | FRL0 | 2024 | 250134.0 | p
A | NR | T | Y_LT5 | DE60 | 2024 | 91434.0 | 
A | NR | T | Y_LT5 | DE80 | 2024 | 57767.0 | 
A | NR | T | Y_LT5 | FRK2 | 2024 | 353827.0 | p
A | NR | T | Y10-14 | DE13 | 2024 | 110399.0 | 
A | NR | T | Y10-14 | DEE0 | 2024 | 93944.0 | 
A | NR | T | Y10-14 | FRB0 | 2024 | 160812.0 | p
A | NR | T | Y10-14 | DE91 | 2024 | 69519.0 | 
A | NR | T | Y10-14 | DEF0 | 2024 | 134867.0 | 
A | NR | T | Y10-14 | DE80 | 2024 | 71843.0 | 
A | NR | T | Y10-14 | FR10 | 2024 | 803945.0 | p
A | NR | T | Y10-14 | DEG0 | 2024 | 96990.0 | 
A | NR | T | Y10-14 | FRE2 | 2024 | 127343.0 | p
A | NR | T | Y_LT5 | FRH0 | 2025 | 153773.0 | p
A | NR | T | Y10-14 | FRF2 | 2025 | 79333.0 | p
A | NR | T | Y_LT5 | FRC2 | 2025 | 53234.0 | p
A | NR | T | Y_LT5 | FRD1 | 2025 | 64866.0 | p
A | NR | T | Y_LT5 | DE11 | 2025 | 200267.0 | 
A | NR | T | Y10-14 | DE14 | 2025 | 90906.0 | 
A | NR | T | Y_LT5 | FRG0 | 2025 | 190491.0 | p
A | NR | T | Y_LT5 | DE30 | 2025 | 169788.0 | 
A | NR | T | Y_LT5 | FRI2 | 2025 | 28557.0 | p
A | NR | T | Y10-14 | DE91 | 2025 | 70717.0 | 
A | NR | T | Y_LT5 | FRK2 | 2025 | 343462.0 | p
A | NR | T | Y_LT5 | FRL0 | 2025 | 243704.0 | p
A | NR | T | Y_LT5 | DE12 | 2025 | 127756.0 | 
A | NR | T | Y5-9 | FRB0 | 2025 | 143247.0 | p
A | NR | T | Y_LT5 | DE22 | 2025 | 57948.0 | 
A | NR | T | Y5-9 | DED2 | 2025 | 76140.0 | 
A | NR | T | Y_LT5 | DE23 | 2025 | 51963.0 | 
A | NR | T | Y_LT5 | DE25 | 2025 | 82757.0 | 
A | NR | T | Y_LT5 | DEA5 | 2025 | 161271.0 | 
A | NR | T | Y5-9 | FRM0 | 2025 | 18459.0 | p
A | NR | T | Y5-9 | DE24 | 2025 | 48426.0 | 
A | NR | T | Y5-9 | DE30 | 2025 | 174956.0 | 
A | NR | T | Y5-9 | DE60 | 2025 | 91435.0 | 
A | NR | T | Y_LT5 | DE40 | 2025 | 93429.0 | 
A | NR | T | Y5-9 | DEA1 | 2025 | 257481.0 | 
A | NR | T | Y5-9 | DEA5 | 2025 | 172049.0 | 
A | NR | T | Y5-9 | DEC0 | 2025 | 45070.0 | 
A | NR | T | Y_LT5 | DE72 | 2025 | 45645.0 | 
A | NR | T | Y_LT5 | DEG0 | 2025 | 71735.0 | 
A | NR | T | Y_LT5 | DE92 | 2025 | 93430.0 | 
A | NR | T | Y5-9 | DEF0 | 2025 | 138687.0 | 
A | NR | T | Y_LT5 | DEB2 | 2025 | 22482.0 | 
A | NR | T | Y_LT5 | DEA4 | 2025 | 97091.0 | 
A | NR | T | Y5-9 | DE71 | 2025 | 200515.0 | 
A | NR | T | Y5-9 | DE13 | 2025 | 118675.0 | 
A | NR | T | Y_LT5 | DED4 | 2025 | 48000.0 | 
A | NR | T | Y_LT5 | DED5 | 2025 | 42481.0 | 
A | NR | T | Y_LT5 | FRI3 | 2025 | 74385.0 | p
A | NR | T | Y_LT5 | FRJ1 | 2025 | 130040.0 | p
A | NR | T | Y_LT5 | FRF2 | 2025 | 59873.0 | p
A | NR | T | Y_LT5 | FR10 | 2025 | 691161.0 | p
A | NR | T | Y_LT5 | FRD2 | 2025 | 93374.0 | p
A | NR | T | Y_LT5 | FRF1 | 2025 | 87272.0 | p
A | NR | T | Y5-9 | FRF3 | 2025 | 124247.0 | p
A | NR | T | Y5-9 | DE25 | 2025 | 88594.0 | 
A | NR | T | Y_LT5 | FRB0 | 2025 | 121714.0 | p
A | NR | T | Y_LT5 | FRI1 | 2025 | 156207.0 | p
A | NR | T | Y_LT5 | DEC0 | 2025 | 41330.0 | 
A | NR | T | Y_LT5 | DE14 | 2025 | 92082.0 | 
A | NR | T | Y_LT5 | FRM0 | 2025 | 14910.0 | p
A | NR | T | Y5-9 | FRE2 | 2025 | 115285.0 | p
A | NR | T | Y_LT5 | DE13 | 2025 | 110301.0 | 
A | NR | T | Y_LT5 | DE24 | 2025 | 44706.0 | 
A | NR | T | Y_LT5 | DE26 | 2025 | 59754.0 | 
A | NR | T | Y5-9 | FRK1 | 2025 | 69668.0 | p
A | NR | T | Y_LT5 | DEA2 | 2025 | 200165.0 | 
A | NR | T | Y_LT5 | DEB3 | 2025 | 94842.0 | 
A | NR | T | Y_LT5 | DE80 | 2025 | 54547.0 | 
A | NR | T | Y_LT5 | DEA1 | 2025 | 235920.0 | 
A | NR | T | Y5-9 | DE80 | 2025 | 69561.0 | 
A | NR | T | Y5-9 | DEB1 | 2025 | 74685.0 | 
A | NR | T | Y_LT5 | DE50 | 2025 | 33228.0 | 
A | NR | T | Y_LT5 | DE60 | 2025 | 89441.0 | 
A | NR | T | Y_LT5 | DE73 | 2025 | 52312.0 | 
A | NR | T | Y5-9 | DEA2 | 2025 | 215173.0 | 
A | NR | T | Y_LT5 | FRJ2 | 2025 | 139877.0 | p
A | NR | T | Y_LT5 | DE93 | 2025 | 76971.0 | 
A | NR | T | Y_LT5 | DE94 | 2025 | 119651.0 | 
A | NR | T | Y5-9 | DE92 | 2025 | 100853.0 | 
A | NR | T | Y_LT5 | DEB1 | 2025 | 68323.0 | 
A | NR | T | Y5-9 | FRI2 | 2025 | 34281.0 | p
A | NR | T | Y_LT5 | DEA3 | 2025 | 126442.0 | 
A | NR | T | Y5-9 | FRC1 | 2025 | 83600.0 | p
A | NR | T | Y5-9 | DE72 | 2025 | 49535.0 | 
A | NR | T | Y_LT5 | DE91 | 2025 | 69299.0 | 
A | NR | T | Y5-9 | FRD1 | 2025 | 77436.0 | p
A | NR | T | Y10-14 | DEC0 | 2025 | 43152.0 | 
A | NR | T | Y_LT5 | DE27 | 2025 | 94975.0 | 
A | NR | T | Y_LT5 | DEE0 | 2025 | 74272.0 | 
A | NR | T | Y5-9 | FRE1 | 2025 | 238972.0 | p
A | NR | T | Y5-9 | DE40 | 2025 | 122177.0 | 
A | NR | T | Y10-14 | DE72 | 2025 | 47444.0 | 
A | NR | T | Y5-9 | DE14 | 2025 | 96824.0 | 
A | NR | T | Y5-9 | DE11 | 2025 | 209330.0 | 
A | NR | T | Y5-9 | DEG0 | 2025 | 93941.0 | 
A | NR | T | Y5-9 | DEE0 | 2025 | 92473.0 | 
A | NR | T | Y_LT5 | DE71 | 2025 | 186122.0 | 
A | NR | T | Y10-14 | DEB2 | 2025 | 24299.0 | 
A | NR | T | Y10-14 | DEB1 | 2025 | 70104.0 | 
A | NR | T | Y10-14 | DEA4 | 2025 | 100770.0 | 
A | NR | T | Y10-14 | DEA2 | 2025 | 206943.0 | 
A | NR | T | Y10-14 | DE94 | 2025 | 121934.0 | 
A | NR | T | Y10-14 | DE93 | 2025 | 81622.0 | 
A | NR | T | Y10-14 | DE92 | 2025 | 96866.0 | 
A | NR | T | Y5-9 | FRC2 | 2025 | 66506.0 | p
A | NR | T | Y10-14 | DE60 | 2025 | 84761.0 | 
A | NR | T | Y10-14 | DE40 | 2025 | 122740.0 | 
A | NR | T | Y10-14 | DE27 | 2025 | 90058.0 | 
A | NR | T | Y10-14 | DE25 | 2025 | 81828.0 | 
A | NR | T | Y10-14 | DE23 | 2025 | 49943.0 | 
A | NR | T | Y10-14 | DE22 | 2025 | 57215.0 | 
A | NR | T | Y10-14 | DE21 | 2025 | 222065.0 | 
A | NR | T | Y_LT5 | DED2 | 2025 | 57409.0 | 
A | NR | T | Y10-14 | DEE0 | 2025 | 94915.0 | 
A | NR | T | Y10-14 | DEG0 | 2025 | 98153.0 | 
A | NR | T | Y10-14 | FRE2 | 2025 | 126062.0 | p
A | NR | T | Y5-9 | DE26 | 2025 | 63055.0 | 
A | NR | T | Y5-9 | DE91 | 2025 | 75545.0 | 
A | NR | T | Y5-9 | DED4 | 2025 | 61988.0 | 
A | NR | T | Y5-9 | DEB3 | 2025 | 101187.0 | 
A | NR | T | Y5-9 | DEB2 | 2025 | 25145.0 | 
A | NR | T | Y5-9 | DEA4 | 2025 | 104427.0 | 
A | NR | T | Y5-9 | DEA3 | 2025 | 134202.0 | 
A | NR | T | Y5-9 | DE94 | 2025 | 127951.0 | 
A | NR | T | Y5-9 | DE93 | 2025 | 85018.0 | 
A | NR | T | Y5-9 | DED5 | 2025 | 51875.0 | 
A | NR | T | Y5-9 | DE73 | 2025 | 56884.0 | 
A | NR | T | Y5-9 | DE50 | 2025 | 36186.0 | 
A | NR | T | Y5-9 | DE27 | 2025 | 98550.0 | 
A | NR | T | Y10-14 | FRB0 | 2025 | 159565.0 | p
A | NR | T | Y5-9 | DE23 | 2025 | 53027.0 | 
A | NR | T | Y5-9 | DE22 | 2025 | 60274.0 | 
A | NR | T | Y5-9 | FRL0 | 2025 | 270541.0 | p
A | NR | T | Y5-9 | FRK2 | 2025 | 404461.0 | p
A | NR | T | Y5-9 | FRJ1 | 2025 | 155825.0 | p
A | NR | T | Y5-9 | FRI3 | 2025 | 91277.0 | p
A | NR | T | Y5-9 | FRH0 | 2025 | 184156.0 | p
A | NR | T | Y5-9 | FRG0 | 2025 | 220845.0 | p
A | NR | T | Y5-9 | FRF1 | 2025 | 103093.0 | p
A | NR | T | Y5-9 | DE21 | 2025 | 233167.0 | 
A | NR | T | Y5-9 | FRD2 | 2025 | 110056.0 | p
A | NR | T | Y10-14 | DE80 | 2025 | 72204.0 | 
A | NR | T | Y10-14 | DED5 | 2025 | 49850.0 | 
A | NR | T | Y10-14 | DED4 | 2025 | 64337.0 | 
A | NR | T | Y10-14 | DED2 | 2025 | 79135.0 | 
A | NR | T | Y10-14 | DE12 | 2025 | 129816.0 | 
A | NR | T | Y10-14 | DE13 | 2025 | 111790.0 | 
A | NR | T | Y_LT5 | FRF3 | 2025 | 100969.0 | p
A | NR | T | Y10-14 | DE24 | 2025 | 45922.0 | 
A | NR | T | Y10-14 | DE26 | 2025 | 58556.0 | 
A | NR | T | Y10-14 | DE30 | 2025 | 166674.0 | 
A | NR | T | Y10-14 | DE50 | 2025 | 32533.0 | 
A | NR | T | Y10-14 | DEB3 | 2025 | 95539.0 | 
A | NR | T | Y10-14 | DE73 | 2025 | 54788.0 | 
A | NR | T | Y10-14 | FRM0 | 2025 | 19248.0 | p
A | NR | T | Y_LT5 | FRK1 | 2025 | 56265.0 | p
A | NR | T | Y10-14 | DEA1 | 2025 | 244309.0 | 
A | NR | T | Y10-14 | DEA3 | 2025 | 125833.0 | 
A | NR | T | Y10-14 | DEA5 | 2025 | 164198.0 | 
A | NR | T | Y_LT5 | FRE2 | 2025 | 97029.0 | p
A | NR | T | Y10-14 | DE71 | 2025 | 193363.0 | 
A | NR | T | Y5-9 | DE12 | 2025 | 136505.0 | 
A | NR | T | Y5-9 | FR10 | 2025 | 719831.0 | p
A | NR | T | Y_LT5 | DE21 | 2025 | 228448.0 | 
A | NR | T | Y5-9 | FRF2 | 2025 | 70612.0 | p
A | NR | T | Y5-9 | FRI1 | 2025 | 184453.0 | p
A | NR | T | Y10-14 | FRF1 | 2025 | 115391.0 | p
A | NR | T | Y10-14 | FRL0 | 2025 | 301389.0 | p
A | NR | T | Y10-14 | FRK2 | 2025 | 439303.0 | p
A | NR | T | Y10-14 | FRK1 | 2025 | 76273.0 | p
A | NR | T | Y_LT5 | DEF0 | 2025 | 122545.0 | 
A | NR | T | Y10-14 | FRJ1 | 2025 | 172885.0 | p
A | NR | T | Y10-14 | FRD2 | 2025 | 119420.0 | p
A | NR | T | Y10-14 | FRI2 | 2025 | 38548.0 | p
A | NR | T | Y10-14 | DE11 | 2025 | 197554.0 | 
A | NR | T | Y10-14 | FRH0 | 2025 | 207336.0 | p
A | NR | T | Y10-14 | FRG0 | 2025 | 249449.0 | p
A | NR | T | Y10-14 | FRF3 | 2025 | 135676.0 | p
A | NR | T | Y5-9 | FRJ2 | 2025 | 166540.0 | p
A | NR | T | Y_LT5 | FRC1 | 2025 | 69247.0 | p
A | NR | T | Y10-14 | FRI1 | 2025 | 204068.0 | p
A | NR | T | Y10-14 | FRE1 | 2025 | 270840.0 | p
A | NR | T | Y10-14 | FRI3 | 2025 | 103785.0 | p
A | NR | T | Y10-14 | FRD1 | 2025 | 85920.0 | p
A | NR | T | Y10-14 | FRC2 | 2025 | 73266.0 | p
A | NR | T | Y10-14 | FRC1 | 2025 | 91795.0 | p
A | NR | T | Y10-14 | FRJ2 | 2025 | 185526.0 | p
A | NR | T | Y10-14 | FR10 | 2025 | 803515.0 | p
A | NR | T | Y_LT5 | FRE1 | 2025 | 206211.0 | p
A | NR | T | Y10-14 | DEF0 | 2025 | 136365.0 | 
[Source : miroir local, données Eurostat du 10.08.2026]
```

## Answer

I now have all the data needed. Let me compute the schools-per-1,000-children ratio for each region and rank them.

## Results: Schools per 1,000 Children (under 15) at NUTS2 Level

**Data used:**
- Population under 15: Eurostat `demo_r_pjangroup` (2025, age bands 0-4 + 5-9 + 10-14, sex = Total)
- School counts: OSM snapshot 2026-08 (`schools_count`)

### 5 Regions with the FEWEST schools per 1,000 children

| Rank | Region | Country | Under-15 Pop | Schools | per 1,000 |
|------|--------|---------|-------------|---------|-----------|
| 1 | Berlin (DE30) | Germany | 511,418 | 1,077 | **2.11** |
| 2 | Hamburg (DE60) | Germany | 265,637 | 561 | **2.11** |
| 3 | Darmstadt (DE71) | Germany | 580,000 | 1,391 | **2.40** |
| 4 | Bremen (DE50) | Germany | 101,947 | 257 | **2.52** |
| 5 | Oberbayern (DE21) | Germany | 683,680 | 1,845 | **2.70** |

### 5 Regions with the MOST schools per 1,000 children

| Rank | Region | Country | Under-15 Pop | Schools | per 1,000 |
|------|--------|---------|-------------|---------|-----------|
| 1 | Bourgogne (FRC1) | France | 244,642 | 2,434 | **9.95** |
| 2 | Limousin (FRI2) | France | 101,386 | 934 | **9.21** |
| 3 | Franche-Comté (FRC2) | France | 193,006 | 1,647 | **8.53** |
| 4 | Auvergne (FRK1) | France | 202,206 | 1,666 | **8.24** |
| 5 | Lorraine (FRF3) | France | 360,892 | 2,626 | **7.28** |

---

## Limits of This Comparison

1. **OSM mapping completeness is unknown.** Every school count carries an `osm_completeness_unknown` flag. OpenStreetMap coverage is far better in urban and Western European areas than in rural or remote regions. German states like Berlin and Hamburg are well-mapped, but smaller rural German districts may be under-mapped. French rural regions (Bourgogne, Limousin) may be over- or under-counted depending on local mapping effort. This is the single largest source of error.

2. **Structural differences in school systems.** France and Germany organize schooling very differently. France maintains a large network of small primary schools (écoles élémentaires) often one per commune, especially in rural areas. Germany's system varies by *Land* and includes multiple school types (Grundschule, Realschule, Gymnasium, Gesamtschule) that OSM may tag inconsistently. A "school" in OSM is a generic tag; it doesn't distinguish type, level, or whether it's still operational.

3. **Rural vs. urban artifact.** The high ratios in rural French regions (Bourgogne, Limousin, Franche-Comté, Auvergne) largely reflect the French policy of maintaining a school in every small commune, resulting in many tiny schools with few students. The low ratios in Berlin, Hamburg, and other large German urban areas reflect consolidation into larger institutions. Neither necessarily indicates "scarcity" of educational access.

4. **Age-group mismatch.** The denominator is all children under 15, but most schools count serve ages 6–18 (or 6–10 for primary). Young children (0–5) are in *crèches* or *Krippen*, not schools. Including them in the denominator dilutes the ratio and is not a true measure of school demand.

5. **NUTS2 boundaries ≠ school districts.** Children frequently attend schools across NUTS2 boundaries. A child living near a border may be enrolled in a school in the neighboring region, so the ratio doesn't cleanly represent access.

6. **Snapshot timing mismatch.** Population data is 2025 (Eurostat); OSM snapshot is August 2026. Schools opened, closed, or reclassified in that interval are not reconciled.

7. **Overseas territories excluded.** French NUTS2 overseas regions (Guadeloupe, Martinique, Guyane, Réunion, Mayotte) were not returned by OSM and are omitted, though they could have materially different ratios.

