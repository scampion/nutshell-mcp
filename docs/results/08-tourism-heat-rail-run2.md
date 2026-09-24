# Example 8 — second run (before the search_datasets hint)

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> Summer tourism meets climate change. Among the NUTS2 regions of Spain, Italy, Greece and Croatia, which ones receive the most tourist nights, have the hottest summers, and how well are they served by rail relative to population? Give a top 8 with the figures, and say which conclusions the data does and does not support.

## Tool calls

**1. `search_indicators(query="tourist nights", limit=10)`**

```
Aucun indicateur ne correspond à 'tourist nights'. Registre complet (10) : gdp_per_capita, hospitals_count, imperviousness_share, lst_summer_mean, median_age, old_age_dependency, population, schools_count, train_stations_count, unemployment_rate.
```

**2. `search_indicators(query="summer temperature heat", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
lst_summer_mean | Température de surface moyenne, juin-août | DEG_C | A | NUTS2,NUTS3,CITY | copernicus
```

**3. `search_indicators(query="railway rail network population", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**4. `list_zones(level="NUTS2", parent="ES")`**

```
geo_code | name | level | parent
ES11 | Galicia | NUTS2 | ES1
ES12 | Principado de Asturias | NUTS2 | ES1
ES13 | Cantabria | NUTS2 | ES1
ES21 | País Vasco | NUTS2 | ES2
ES22 | Comunidad Foral de Navarra | NUTS2 | ES2
ES23 | La Rioja | NUTS2 | ES2
ES24 | Aragón | NUTS2 | ES2
ES30 | Comunidad de Madrid | NUTS2 | ES3
ES41 | Castilla y León | NUTS2 | ES4
ES42 | Castilla-La Mancha | NUTS2 | ES4
ES43 | Extremadura | NUTS2 | ES4
ES51 | Cataluña | NUTS2 | ES5
ES52 | Comunitat Valenciana  | NUTS2 | ES5
ES53 | Illes Balears | NUTS2 | ES5
ES61 | Andalucía | NUTS2 | ES6
ES62 | Región de Murcia | NUTS2 | ES6
ES63 | Ciudad de Ceuta | NUTS2 | ES6
ES64 | Ciudad de Melilla | NUTS2 | ES6
ES70 | Canarias | NUTS2 | ES7
```

**5. `list_zones(level="NUTS2", parent="IT")`**

```
geo_code | name | level | parent
ITC1 | Piemonte | NUTS2 | ITC
ITC2 | Valle d’Aosta/Vallée d’Aoste | NUTS2 | ITC
ITC3 | Liguria | NUTS2 | ITC
ITC4 | Lombardia | NUTS2 | ITC
ITF1 | Abruzzo | NUTS2 | ITF
ITF2 | Molise | NUTS2 | ITF
ITF3 | Campania | NUTS2 | ITF
ITF4 | Puglia | NUTS2 | ITF
ITF5 | Basilicata | NUTS2 | ITF
ITF6 | Calabria | NUTS2 | ITF
ITG1 | Sicilia | NUTS2 | ITG
ITG2 | Sardegna | NUTS2 | ITG
ITH1 | Provincia Autonoma di Bolzano/Bozen | NUTS2 | ITH
ITH2 | Provincia Autonoma di Trento | NUTS2 | ITH
ITH3 | Veneto | NUTS2 | ITH
ITH4 | Friuli-Venezia Giulia | NUTS2 | ITH
ITH5 | Emilia-Romagna | NUTS2 | ITH
ITI1 | Toscana | NUTS2 | ITI
ITI2 | Umbria | NUTS2 | ITI
ITI3 | Marche | NUTS2 | ITI
ITI4 | Lazio | NUTS2 | ITI
```

**6. `list_zones(level="NUTS2", parent="GR")`**

```
Zone parente 'GR' inconnue. La Grèce est codée EL en NUTS (GR est le code ISO) : essayez 'EL'.
```

**7. `list_zones(level="NUTS2", parent="HR")`**

```
geo_code | name | level | parent
HR02 | Panonska Hrvatska | NUTS2 | HR0
HR03 | Jadranska Hrvatska | NUTS2 | HR0
HR05 | Grad Zagreb | NUTS2 | HR0
HR06 | Sjeverna Hrvatska | NUTS2 | HR0
```

**8. `list_zones(level="NUTS2", parent="EL")`**

```
geo_code | name | level | parent
EL30 | Attiki | NUTS2 | EL3
EL41 | Voreio Aigaio | NUTS2 | EL4
EL42 | Notio Aigaio | NUTS2 | EL4
EL43 | Kriti | NUTS2 | EL4
EL51 | Anatoliki Makedonia, Thraki | NUTS2 | EL5
EL52 | Kentriki Makedonia | NUTS2 | EL5
EL53 | Dytiki Makedonia | NUTS2 | EL5
EL54 | Ipeiros | NUTS2 | EL5
EL61 | Thessalia | NUTS2 | EL6
EL62 | Ionia Nisia | NUTS2 | EL6
EL63 | Dytiki Elláda | NUTS2 | EL6
EL64 | Sterea Elláda | NUTS2 | EL6
EL65 | Peloponnisos | NUTS2 | EL6
```

**9. `get_indicators(indicators=["lst_summer_mean", "train_stations_count", "population"], zones=["ES11", "ES12", "ES13", "ES21", "ES22", "ES23", "ES24", "ES30", "ES41", "ES42", "ES43", "ES51", "ES52", "ES53", "ES61", "ES62", "ES63", "ES64", "ES70", "ITC1", "ITC2", "ITC3", "ITC4", "ITF1", "ITF2", "ITF3", "ITF4", "ITF5", "ITF6", "ITG1", "ITG2", "ITH1", "ITH2", "ITH3", "ITH4", "ITH5", "ITI1", "ITI2", "ITI3", "ITI4", "EL30", "EL41", "EL42", "EL43", "EL51", "EL52", "EL53", "EL54", "EL61", "EL62", "EL63", "EL64", "EL65", "HR02", "HR03", "HR05", "HR06"])`**

```
geo_code | time | lst_summer_mean | train_stations_count | population
EL30 | 2025 |  | 98 [snapshot 2026-08] | 3764272
EL30 | 2024 | 29.9199 [sampled] | 98 [snapshot 2026-08] | 3772675
EL30 | 2023 | 28.7443 [sampled] | 98 [snapshot 2026-08] | 3789105
EL41 | 2025 |  | 0 [snapshot 2026-08] | 207927
EL41 | 2024 | 26.076 [sampled] | 0 [snapshot 2026-08] | 200051
EL41 | 2023 | 25.0875 [sampled] | 0 [snapshot 2026-08] | 194221
EL42 | 2025 |  | 0 [snapshot 2026-08] | 327036
EL42 | 2024 | 25.4391 [sampled] | 0 [snapshot 2026-08] | 326373
EL42 | 2023 | 24.6074 [sampled] | 0 [snapshot 2026-08] | 326433
EL43 | 2025 |  | 0 [snapshot 2026-08] | 621121
EL43 | 2024 | 28.2479 [sampled] | 0 [snapshot 2026-08] | 621442
EL43 | 2023 | 26.2262 [sampled] | 0 [snapshot 2026-08] | 622246
EL51 | 2025 |  | 29 [snapshot 2026-08] | 565195
EL51 | 2024 | 27.3255 [sampled] | 29 [snapshot 2026-08] | 561325
EL51 | 2023 | 25.0131 [sampled] | 29 [snapshot 2026-08] | 559007
EL52 | 2025 |  | 63 [snapshot 2026-08] | 1772400
EL52 | 2024 | 28.5057 [sampled] | 63 [snapshot 2026-08] | 1774437
EL52 | 2023 | 26.4375 [sampled] | 63 [snapshot 2026-08] | 1779991
EL53 | 2025 |  | 6 [snapshot 2026-08] | 243575
EL53 | 2024 | 24.5302 [sampled] | 6 [snapshot 2026-08] | 246524
EL53 | 2023 | 23.6407 [sampled] | 6 [snapshot 2026-08] | 249809
EL54 | 2025 |  | 0 [snapshot 2026-08] | 324061
EL54 | 2024 | 24.8936 [sampled] | 0 [snapshot 2026-08] | 320698
EL54 | 2023 | 23.6503 [sampled] | 0 [snapshot 2026-08] | 318495
EL61 | 2025 |  | 16 [snapshot 2026-08] | 676040
EL61 | 2024 | 27.8029 [sampled] | 16 [snapshot 2026-08] | 677721
EL61 | 2023 | 26.78 [sampled] | 16 [snapshot 2026-08] | 680837
EL62 | 2025 |  | 0 [snapshot 2026-08] | 198421
EL62 | 2024 | 26.0511 [sampled] | 0 [snapshot 2026-08] | 200014
EL62 | 2023 | 24.6986 [sampled] | 0 [snapshot 2026-08] | 201877
EL63 | 2025 |  | 14 [snapshot 2026-08] | 635954
EL63 | 2024 | 28.4259 [sampled] | 14 [snapshot 2026-08] | 638468
EL63 | 2023 | 25.9855 [sampled] | 14 [snapshot 2026-08] | 641643
EL64 | 2025 |  | 20 [snapshot 2026-08] | 507168
EL64 | 2024 | 28.0512 [sampled] | 20 [snapshot 2026-08] | 504963
EL64 | 2023 | 26.4503 [sampled] | 20 [snapshot 2026-08] | 504332
EL65 | 2025 |  | 11 [snapshot 2026-08] | 529165
EL65 | 2024 | 28.1079 [sampled] | 11 [snapshot 2026-08] | 531073
EL65 | 2023 | 26.4455 [sampled] | 11 [snapshot 2026-08] | 533872
ES11 | 2025 |  | 97 [snapshot 2026-08] | 2714741
ES11 | 2024 | 19.6743 [sampled] | 97 [snapshot 2026-08] | 2705833
ES11 | 2023 | 19.098 [sampled] | 97 [snapshot 2026-08] | 2699424
ES12 | 2025 |  | 97 [snapshot 2026-08] | 1015128
ES12 | 2024 | 18.0947 [sampled] | 97 [snapshot 2026-08] | 1009599
ES12 | 2023 | 17.9871 [sampled] | 97 [snapshot 2026-08] | 1006060
ES13 | 2025 |  | 89 [snapshot 2026-08] | 593623
ES13 | 2024 | 19.1782 [sampled] | 89 [snapshot 2026-08] | 590851
ES13 | 2023 | 18.9801 [sampled] | 89 [snapshot 2026-08] | 588387
ES21 | 2025 |  | 191 [snapshot 2026-08] | 2242343
ES21 | 2024 | 20.2938 [sampled] | 191 [snapshot 2026-08] | 2227684
ES21 | 2023 | 19.7257 [sampled] | 191 [snapshot 2026-08] | 2216302
ES22 | 2025 |  | 19 [snapshot 2026-08] | 683854
ES22 | 2024 | 22.5107 [sampled] | 19 [snapshot 2026-08] | 678333
ES22 | 2023 | 20.8923 [sampled] | 19 [snapshot 2026-08] | 672155
ES23 | 2025 |  | 9 [snapshot 2026-08] | 326803
ES23 | 2024 | 22.4119 [sampled] | 9 [snapshot 2026-08] | 324184
ES23 | 2023 | 20.6143 [sampled] | 9 [snapshot 2026-08] | 322282
ES24 | 2025 |  | 82 [snapshot 2026-08] | 1364621
ES24 | 2024 | 24.9549 [sampled] | 82 [snapshot 2026-08] | 1351591
ES24 | 2023 | 23.4894 [sampled] | 82 [snapshot 2026-08] | 1341289
ES30 | 2025 |  | 392 [snapshot 2026-08] | 7113886
ES30 | 2024 | 26.771 [sampled] | 392 [snapshot 2026-08] | 7009268
ES30 | 2023 | 25.8013 [sampled] | 392 [snapshot 2026-08] | 6871903
ES41 | 2025 |  | 114 [snapshot 2026-08] | 2401221
ES41 | 2024 | 23.0661 [sampled] | 114 [snapshot 2026-08] | 2391682
ES41 | 2023 | 22.1109 [sampled] | 114 [snapshot 2026-08] | 2383703
ES42 | 2025 |  | 53 [snapshot 2026-08] | 2126378
ES42 | 2024 | 27.3082 [sampled] | 53 [snapshot 2026-08] | 2104433
ES42 | 2023 | 26.5672 [sampled] | 53 [snapshot 2026-08] | 2084086
ES43 | 2025 |  | 28 [snapshot 2026-08] | 1053345
ES43 | 2024 | 28.2059 [sampled] | 28 [snapshot 2026-08] | 1054681
ES43 | 2023 | 28.1691 [sampled] | 28 [snapshot 2026-08] | 1054306
ES51 | 2025 |  | 425 [snapshot 2026-08] | 8124126
ES51 | 2024 | 23.8968 [sampled] | 425 [snapshot 2026-08] | 8012231
ES51 | 2023 | 23.6906 [sampled] | 425 [snapshot 2026-08] | 7901963
ES52 | 2025 |  | 206 [snapshot 2026-08] | 5425182
ES52 | 2024 | 26.8594 [sampled] | 206 [snapshot 2026-08] | 5319285
ES52 | 2023 | 26.8022 [sampled] | 206 [snapshot 2026-08] | 5216195
ES53 | 2025 |  | 36 [snapshot 2026-08] | 1249844
ES53 | 2024 | 26.8639 [sampled] | 36 [snapshot 2026-08] | 1231768
ES53 | 2023 | 27.9364 [sampled] | 36 [snapshot 2026-08] | 1209906
ES61 | 2025 |  | 207 [snapshot 2026-08] | 8676713
ES61 | 2024 | 27.7282 [sampled] | 207 [snapshot 2026-08] | 8631862
ES61 | 2023 | 28.2763 [sampled] | 207 [snapshot 2026-08] | 8584147
ES62 | 2025 |  | 26 [snapshot 2026-08] | 1586989
ES62 | 2024 | 28.1372 [sampled] | 26 [snapshot 2026-08] | 1568492
ES62 | 2023 | 28.5938 [sampled] | 26 [snapshot 2026-08] | 1551692
ES63 | 2025 |  | 0 [snapshot 2026-08] | 83567
ES63 | 2024 | 20.447 [sampled] | 0 [snapshot 2026-08] | 83179
ES63 | 2023 | 20.9772 [sampled] | 0 [snapshot 2026-08] | 83052
ES64 | 2025 |  | 0 [snapshot 2026-08] | 87067
ES64 | 2024 | 29.5485 [sampled] | 0 [snapshot 2026-08] | 85985
ES64 | 2023 | 30.4975 [sampled] | 0 [snapshot 2026-08] | 85493
ES70 | 2025 |  | 0 [snapshot 2026-08] | 2258866
ES70 | 2024 |  | 0 [snapshot 2026-08] | 2238754
ES70 | 2023 |  | 0 [snapshot 2026-08] | 2213016
HR02 | 2025 |  | 91 [snapshot 2026-08] | 982159
HR02 | 2024 | 24.4673 [sampled] | 91 [snapshot 2026-08] | 990636
HR02 | 2023 | 22.6599 [sampled] | 91 [snapshot 2026-08] | 999106
HR03 | 2025 |  | 50 [snapshot 2026-08] | 1322482
HR03 | 2024 | 23.5692 [sampled] | 50 [snapshot 2026-08] | 1310313
HR03 | 2023 | 23.2019 [sampled] | 50 [snapshot 2026-08] | 1297987
HR05 | 2025 |  | 6 [snapshot 2026-08] | 777359
HR05 | 2024 | 24.0941 [sampled] | 6 [snapshot 2026-08] | 772122
HR05 | 2023 | 22.0519 [sampled] | 6 [snapshot 2026-08] | 768624
HR06 | 2025 |  | 47 [snapshot 2026-08] | 792350
HR06 | 2024 | 23.5204 [sampled] | 47 [snapshot 2026-08] | 788896
HR06 | 2023 | 21.7746 [sampled] | 47 [snapshot 2026-08] | 785177
ITC1 | 2025 |  | 277 [snapshot 2026-08] | 4251868
ITC1 | 2024 | 20.3834 [sampled] | 277 [snapshot 2026-08] | 4251623
ITC1 | 2023 | 21.5837 [sampled] | 277 [snapshot 2026-08] | 4251351
ITC2 | 2025 |  | 16 [snapshot 2026-08] | 122532
ITC2 | 2024 | 13.1018 [sampled] | 16 [snapshot 2026-08] | 122877
ITC2 | 2023 | 13.7964 [sampled] | 16 [snapshot 2026-08] | 123130
ITC3 | 2025 |  | 100 [snapshot 2026-08] | 1510143
ITC3 | 2024 | 22.0603 [sampled] | 100 [snapshot 2026-08] | 1509140
ITC3 | 2023 | 22.5423 [sampled] | 100 [snapshot 2026-08] | 1507636
ITC4 | 2025 |  | 513 [snapshot 2026-08] | 10033918
ITC4 | 2024 | 20.5825 [sampled] | 513 [snapshot 2026-08] | 10012054
ITC4 | 2023 | 22.0951 [sampled] | 513 [snapshot 2026-08] | 9976509
ITF1 | 2025 |  | 81 [snapshot 2026-08] | 1269118
ITF1 | 2024 | 23.1647 [sampled] | 81 [snapshot 2026-08] | 1269571
ITF1 | 2023 | 22.4916 [sampled] | 81 [snapshot 2026-08] | 1272627
ITF2 | 2025 |  | 26 [snapshot 2026-08] | 287814
ITF2 | 2024 | 24.9286 [sampled] | 26 [snapshot 2026-08] | 289224
ITF2 | 2023 | 23.9 [sampled] | 26 [snapshot 2026-08] | 290636
ITF3 | 2025 |  | 359 [snapshot 2026-08] | 5582337
ITF3 | 2024 | 25.8758 [sampled] | 359 [snapshot 2026-08] | 5593906
ITF3 | 2023 | 24.509 [sampled] | 359 [snapshot 2026-08] | 5609536
ITF4 | 2025 |  | 190 [snapshot 2026-08] | 3877395
ITF4 | 2024 | 28.5815 [sampled] | 190 [snapshot 2026-08] | 3890661
ITF4 | 2023 | 27.6657 [sampled] | 190 [snapshot 2026-08] | 3907683
ITF5 | 2025 |  | 60 [snapshot 2026-08] | 530004
ITF5 | 2024 | 26.684 [sampled] | 60 [snapshot 2026-08] | 533233
ITF5 | 2023 | 25.3521 [sampled] | 60 [snapshot 2026-08] | 537577
ITF6 | 2025 |  | 133 [snapshot 2026-08] | 1834646
ITF6 | 2024 | 26.5926 [sampled] | 133 [snapshot 2026-08] | 1838568
ITF6 | 2023 | 25.2228 [sampled] | 133 [snapshot 2026-08] | 1846610
ITG1 | 2025 |  | 169 [snapshot 2026-08] | 4787390
ITG1 | 2024 | 28.0545 [sampled] | 169 [snapshot 2026-08] | 4797359
ITG1 | 2023 | 26.5764 [sampled] | 169 [snapshot 2026-08] | 4814016
ITG2 | 2025 |  | 118 [snapshot 2026-08] | 1562381
ITG2 | 2024 | 26.1635 [sampled] | 118 [snapshot 2026-08] | 1570453
ITG2 | 2023 | 26.3412 [sampled] | 118 [snapshot 2026-08] | 1578146
ITH1 | 2025 |  | 52 [snapshot 2026-08] | 539679
ITH1 | 2024 | 12.21 [sampled] | 52 [snapshot 2026-08] | 537533
ITH1 | 2023 | 14.0983 [sampled] | 52 [snapshot 2026-08] | 534147
ITH2 | 2025 |  | 49 [snapshot 2026-08] | 546573
ITH2 | 2024 | 15.7992 [sampled] | 49 [snapshot 2026-08] | 545169
ITH2 | 2023 | 16.6407 [sampled] | 49 [snapshot 2026-08] | 542996
ITH3 | 2025 |  | 116 [snapshot 2026-08] | 4853472
ITH3 | 2024 | 21.9601 [sampled] | 116 [snapshot 2026-08] | 4852216
ITH3 | 2023 | 23.1626 [sampled] | 116 [snapshot 2026-08] | 4849553
ITH4 | 2025 |  | 52 [snapshot 2026-08] | 1193284
ITH4 | 2024 | 21.1665 [sampled] | 52 [snapshot 2026-08] | 1194616
ITH4 | 2023 | 21.1953 [sampled] | 52 [snapshot 2026-08] | 1194248
ITH5 | 2025 |  | 212 [snapshot 2026-08] | 4461998
ITH5 | 2024 | 23.7184 [sampled] | 212 [snapshot 2026-08] | 4451938
ITH5 | 2023 | 25.5364 [sampled] | 212 [snapshot 2026-08] | 4437578
ITI1 | 2025 |  | 208 [snapshot 2026-08] | 3657716
ITI1 | 2024 | 24.3012 [sampled] | 208 [snapshot 2026-08] | 3660530
ITI1 | 2023 | 25.1088 [sampled] | 208 [snapshot 2026-08] | 3661981
ITI2 | 2025 |  | 86 [snapshot 2026-08] | 851473
ITI2 | 2024 | 24.8845 [sampled] | 86 [snapshot 2026-08] | 853068
ITI2 | 2023 | 24.643 [sampled] | 86 [snapshot 2026-08] | 856407
ITI3 | 2025 |  | 39 [snapshot 2026-08] | 1480545
ITI3 | 2024 | 25.1554 [sampled] | 39 [snapshot 2026-08] | 1482746
ITI3 | 2023 | 24.7086 [sampled] | 39 [snapshot 2026-08] | 1484298
ITI4 | 2025 |  | 265 [snapshot 2026-08] | 5709178
ITI4 | 2024 | 25.2805 [sampled] | 265 [snapshot 2026-08] | 5714745
ITI4 | 2023 | 24.7081 [sampled] | 265 [snapshot 2026-08] | 5720536
[Instantanés, état courant répété sur chaque période : train_stations_count (2026-08, osm_completeness_unknown)]
[Source : copernicus (ARCO-ERA5 2026-09-24), eurostat (21.08.2026), osm (extrait 2026-08)]
```

## Answer

Here's what the data gives us. One caveat up front: **the indicator registry has no tourist-nights measure** (the complete 10-indicator set is GDP per capita, population, median age, old-age dependency, unemployment, hospital/school counts, imperviousness, summer surface temperature, and train station counts). So the "most tourist nights" leg of the question is **unanswerable from this data**, and I'm answering the other two legs with the best available figures (2024, the last full year; train stations OSM snapshot 2026-08; Eurostat pop. 2024).

## Top 8 hottest summers (Copernicus land-surface mean, Jun–Aug 2024)

| # | Region (code) | Country | Summer °C | Population | Rail stations | Rail per 100k |
|---|---|---|---|---|---|---|
| 1 | Attiki / Attica (EL30) | Greece | **29.92** | 3,772,675 | 98 | 2.60 |
| 2 | Ciudad de Melilla (ES64) | Spain | 29.55 | 85,985 | 0 | 0.00 |
| 3 | Puglia (ITF4) | Italy | 28.58 | 3,890,661 | 190 | 4.88 |
| 4 | Kentriki Makedonia (EL52) | Greece | 28.51 | 1,774,437 | 63 | 3.55 |
| 5 | Dytiki Elláda (EL63) | Greece | 28.43 | 638,468 | 14 | 2.19 |
| 6 | Kriti / Crete (EL43) | Greece | 28.25 | 621,442 | 0 | 0.00 |
| 7 | Extremadura (ES43) | Spain | 28.21 | 1,054,681 | 28 | 2.66 |
| 8 | Región de Murcia (ES62) | Spain | 28.14 | 1,568,492 | 26 | 1.66 |

## Top 8 best-served by rail relative to population (stations per 100k, 2024)

| # | Region (code) | Country | Per 100k | Summer °C |
|---|---|---|---|---|
| 1 | Cantabria (ES13) | Spain | **15.06** | 19.18 |
| 2 | Bolzano (ITH1) | Italy | 9.67 | 12.21 |
| 3 | Asturias (ES12) | Spain | 9.61 | 18.09 |
| 4 | Panonska Hrvatska (HR02) | Croatia | 9.19 | 24.47 |
| 5 | Molise (ITF2) | Italy | 9.00 | 24.93 |
| 6 | Trento (ITH2) | Italy | 9.00 | 15.80 |
| 7 | País Vasco (ES21) | Spain | 8.57 | 20.29 |
| 8 | Sardegna (ITG2) | Italy | 7.51 | 26.16 |

## What the data supports

- **Heat is concentrated in the south and on islands:** 5 of the 8 hottest regions are Greek (mainland south, central Macedonia, Crete), plus Andalusian/SE-Spanish and southern-Italian regions. This matches the climatic expectation for NUTS2 granularity.
- **Rail access is inversely related to heat here:** the best rail-per-capita regions are cool northern/mountain regions (Bolzano 12.2 °C, Aosta 13.1, Trento 15.8, Cantabria/Asturias ~18–19 °C), while the hottest regions are the *worst*-served by rail — the four hottest regions that matter for tourism (Puglia, Crete, Murcia, Melilla) sit at 0–4.9 stations per 100k, and Crete and Melilla have **zero** mapped stations.
- **The top-8 overlap is essentially empty:** no region is in both top-8 lists. "Hottest + best rail" does not describe any single region in these four countries.

## What the data does **not** support

- **Anything about tourist nights.** There is no tourism indicator in the registry, so I cannot say which regions receive the most tourist nights, nor confirm that the hot regions are the popular ones. The "summer tourism" half of the premise is unverified.
- **That the hottest = most touristed.** That inference needs visitor/accommodation data (Eurostat tourism_nsi-class datasets exist but aren't in this registry); from heat + rail alone it's speculation.
- **"Rail service" as such.** `train_stations_count` is a station *count* from OSM — a density proxy, not track-km, service frequency, or passenger volume. A low count doesn't prove a region is poorly served (Crete's single-line network could still cover its demand), and OSM completeness is unknown.
- **°C figures as "heat felt by tourists."** These are Copernicus land-surface temperature means for the whole summer — not air temperature, not peak summer days, not coastal-seabreeze moderated.
- **Data gaps:** Canarias (ES70) has no summer temperature for 2023–2024, and Ceuta/Melilla's zero station counts partly reflect their status as Spanish enclaves, not necessarily travel patterns.

**Bottom line:** within the evidence, the hottest summer regions (Greece's south and center, Murcia, Melilla, Extremadura, Puglia) are precisely the ones with the thinnest rail-per-capita coverage, while the rail-rich regions are the cool northern ones — a structural mismatch that *could* matter for summer tourism strategy, but confirming the tourism demand side would require the missing tourist-nights data.

