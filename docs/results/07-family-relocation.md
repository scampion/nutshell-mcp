# Example 7 — Moving with a young family

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> My family with two young children wants to move to Germany or Austria. Compare their NUTS2 regions: we want mild summers, low unemployment, and as many schools and train stations as possible relative to population. Suggest the 5 best regions with a table of figures, and tell me what the data cannot tell us.

## Tool calls

**1. `list_zones(level="NUTS2", parent="DE")`**

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

**2. `list_zones(level="NUTS2", parent="AT")`**

```
geo_code | name | level | parent
AT11 | Burgenland | NUTS2 | AT1
AT12 | Niederösterreich | NUTS2 | AT1
AT13 | Wien | NUTS2 | AT1
AT21 | Kärnten | NUTS2 | AT2
AT22 | Steiermark | NUTS2 | AT2
AT31 | Oberösterreich | NUTS2 | AT3
AT32 | Salzburg | NUTS2 | AT3
AT33 | Tirol | NUTS2 | AT3
AT34 | Vorarlberg | NUTS2 | AT3
```

**3. `search_indicators(query="summer temperature summer climate heat", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
lst_summer_mean | Température de surface moyenne, juin-août | DEG_C | A | NUTS2,NUTS3,CITY | copernicus
```

**4. `search_indicators(query="unemployment rate", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**5. `search_indicators(query="schools per population", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
schools_count | Établissements scolaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**6. `search_indicators(query="train stations railway per population", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**7. `get_indicators(indicators=["lst_summer_mean", "unemployment_rate", "schools_count", "train_stations_count", "population"], zones=["DE11", "DE12", "DE13", "DE14", "DE21", "DE22", "DE23", "DE24", "DE25", "DE26", "DE27", "DE30", "DE40", "DE50", "DE60", "DE71", "DE72", "DE73", "DE80", "DE91", "DE92", "DE93", "DE94", "DEA1", "DEA2", "DEA3", "DEA4", "DEA5", "DEB1", "DEB2", "DEB3", "DEC0", "DED2", "DED4", "DED5", "DEE0", "DEF0", "DEG0", "AT11", "AT12", "AT13", "AT21", "AT22", "AT31", "AT32", "AT33", "AT34"])`**

```
geo_code | time | lst_summer_mean | unemployment_rate | schools_count | train_stations_count | population
AT11 | 2025 |  | 5 | 193 [snapshot 2026-08] | 33 [snapshot 2026-08] | 301790
AT11 | 2024 | 23.1477 [sampled] | 4.9 | 193 [snapshot 2026-08] | 33 [snapshot 2026-08] | 301951
AT11 | 2023 | 22.0667 [sampled] | 5.2 | 193 [snapshot 2026-08] | 33 [snapshot 2026-08] | 301250
AT12 | 2025 |  | 4.4 | 1156 [snapshot 2026-08] | 213 [snapshot 2026-08] | 1727514
AT12 | 2024 | 21.4359 [sampled] | 4.2 | 1156 [snapshot 2026-08] | 213 [snapshot 2026-08] | 1723723
AT12 | 2023 | 20.9986 [sampled] | 4.3 | 1156 [snapshot 2026-08] | 213 [snapshot 2026-08] | 1718373
AT13 | 2025 |  | 9.9 | 632 [snapshot 2026-08] | 127 [snapshot 2026-08] | 2028289
AT13 | 2024 | 24.0849 [sampled] | 9.4 | 632 [snapshot 2026-08] | 127 [snapshot 2026-08] | 2005760
AT13 | 2023 | 23.1474 [sampled] | 9.6 | 632 [snapshot 2026-08] | 127 [snapshot 2026-08] | 1982097
AT21 | 2025 |  | 4.8 | 365 [snapshot 2026-08] | 58 [snapshot 2026-08] | 570095
AT21 | 2024 | 16.9025 [sampled] | 4.3 | 365 [snapshot 2026-08] | 58 [snapshot 2026-08] | 569744
AT21 | 2023 | 16.8995 [sampled] | 4.5 | 365 [snapshot 2026-08] | 58 [snapshot 2026-08] | 568984
AT22 | 2025 |  | 5 | 772 [snapshot 2026-08] | 121 [snapshot 2026-08] | 1271716
AT22 | 2024 | 18.3791 [sampled] | 4.4 | 772 [snapshot 2026-08] | 121 [snapshot 2026-08] | 1269801
AT22 | 2023 | 17.6906 [sampled] | 4.3 | 772 [snapshot 2026-08] | 121 [snapshot 2026-08] | 1265198
AT31 | 2025 |  | 4.6 | 980 [snapshot 2026-08] | 139 [snapshot 2026-08] | 1535519
AT31 | 2024 | 19.6913 [sampled] | 3.8 | 980 [snapshot 2026-08] | 139 [snapshot 2026-08] | 1530349
AT31 | 2023 | 19.7197 [sampled] | 3.5 | 980 [snapshot 2026-08] | 139 [snapshot 2026-08] | 1522825
AT32 | 2025 |  | 3.5 | 396 [snapshot 2026-08] | 54 [snapshot 2026-08] | 572846
AT32 | 2024 | 15.0077 [sampled] | 3.4 | 396 [snapshot 2026-08] | 54 [snapshot 2026-08] | 571479
AT32 | 2023 | 15.0746 [sampled] | 3 | 396 [snapshot 2026-08] | 54 [snapshot 2026-08] | 568346
AT33 | 2025 |  | 3.8 | 714 [snapshot 2026-08] | 85 [snapshot 2026-08] | 777660
AT33 | 2024 | 12.4266 [sampled] | 3.1 | 714 [snapshot 2026-08] | 85 [snapshot 2026-08] | 775970
AT33 | 2023 | 13.6291 [sampled] | 3.1 | 714 [snapshot 2026-08] | 85 [snapshot 2026-08] | 771304
AT34 | 2025 |  | 4.3 | 234 [snapshot 2026-08] | 18 [snapshot 2026-08] | 411784
AT34 | 2024 | 14.8163 [sampled] | 4.1 | 234 [snapshot 2026-08] | 18 [snapshot 2026-08] | 409973
AT34 | 2023 | 15.8047 [sampled] | 3.4 | 234 [snapshot 2026-08] | 18 [snapshot 2026-08] | 406395
DE11 | 2025 |  | 3.6 | 1881 [snapshot 2026-08] | 177 [snapshot 2026-08] | 4167550
DE11 | 2024 | 19.1259 [sampled] | 3.2 | 1881 [snapshot 2026-08] | 177 [snapshot 2026-08] | 4164699
DE11 | 2023 | 20.6762 [sampled] | 2.9 | 1881 [snapshot 2026-08] | 177 [snapshot 2026-08] | 4142738 [b]
DE12 | 2025 |  | 3.4 | 1176 [snapshot 2026-08] | 148 [snapshot 2026-08] | 2848413
DE12 | 2024 | 19.6364 [sampled] | 3.2 | 1176 [snapshot 2026-08] | 148 [snapshot 2026-08] | 2844407
DE12 | 2023 | 21.0708 [sampled] | 2.9 | 1176 [snapshot 2026-08] | 148 [snapshot 2026-08] | 2832121 [b]
DE13 | 2025 |  | 3.1 | 1224 [snapshot 2026-08] | 120 [snapshot 2026-08] | 2325856
DE13 | 2024 | 19.1631 [sampled] | 2.5 | 1224 [snapshot 2026-08] | 120 [snapshot 2026-08] | 2320772
DE13 | 2023 | 20.6758 [sampled] | 2.2 | 1224 [snapshot 2026-08] | 120 [snapshot 2026-08] | 2304974 [b]
DE14 | 2025 |  | 2.9 | 1010 [snapshot 2026-08] | 106 [snapshot 2026-08] | 1904079
DE14 | 2024 | 18.3951 [sampled] | 2.8 | 1010 [snapshot 2026-08] | 106 [snapshot 2026-08] | 1900862
DE14 | 2023 | 20.2691 [sampled] | 2.1 [u] | 1010 [snapshot 2026-08] | 106 [snapshot 2026-08] | 1887888 [b]
DE21 | 2025 |  | 3 | 1845 [snapshot 2026-08] | 326 [snapshot 2026-08] | 4764548
DE21 | 2024 | 18.7322 [sampled] | 2.7 | 1845 [snapshot 2026-08] | 326 [snapshot 2026-08] | 4726101
DE21 | 2023 | 19.5384 [sampled] | 2.3 | 1845 [snapshot 2026-08] | 326 [snapshot 2026-08] | 4705040 [b]
DE22 | 2025 |  | 2.9 [u] | 568 [snapshot 2026-08] | 51 [snapshot 2026-08] | 1259204
DE22 | 2024 | 19.9589 [sampled] | 2 [u] | 568 [snapshot 2026-08] | 51 [snapshot 2026-08] | 1251623
DE22 | 2023 | 20.3806 [sampled] |  | 568 [snapshot 2026-08] | 51 [snapshot 2026-08] | 1244102 [b]
DE23 | 2025 |  | 2.8 [u] | 547 [snapshot 2026-08] | 43 [snapshot 2026-08] | 1121379
DE23 | 2024 | 19.0109 [sampled] | 2.4 [u] | 547 [snapshot 2026-08] | 43 [snapshot 2026-08] | 1116135
DE23 | 2023 | 20.1244 [sampled] | 2.1 [u] | 547 [snapshot 2026-08] | 43 [snapshot 2026-08] | 1107750 [b]
DE24 | 2025 |  | 3.2 [u] | 550 [snapshot 2026-08] | 62 [snapshot 2026-08] | 1055758
DE24 | 2024 | 18.3617 [sampled] | 2.7 [u] | 550 [snapshot 2026-08] | 62 [snapshot 2026-08] | 1055751
DE24 | 2023 | 20.3252 [sampled] | 2.5 [u] | 550 [snapshot 2026-08] | 62 [snapshot 2026-08] | 1051868 [b]
DE25 | 2025 |  | 3.8 | 688 [snapshot 2026-08] | 110 [snapshot 2026-08] | 1795909
DE25 | 2024 | 19.6249 [sampled] | 2.7 | 688 [snapshot 2026-08] | 110 [snapshot 2026-08] | 1791147
DE25 | 2023 | 20.8602 [sampled] | 2.4 [u] | 688 [snapshot 2026-08] | 110 [snapshot 2026-08] | 1782419 [b]
DE26 | 2025 |  | 3 [u] | 692 [snapshot 2026-08] | 61 [snapshot 2026-08] | 1318817
DE26 | 2024 | 18.8199 [sampled] | 2.9 [u] | 692 [snapshot 2026-08] | 61 [snapshot 2026-08] | 1315155
DE26 | 2023 | 20.6307 [sampled] | 2.1 [u] | 692 [snapshot 2026-08] | 61 [snapshot 2026-08] | 1310561 [b]
DE27 | 2025 |  | 2.7 | 817 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1933313
DE27 | 2024 | 18.2137 [sampled] | 2.6 | 817 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1920514
DE27 | 2023 | 19.756 [sampled] | 1.8 [u] | 817 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1903481 [b]
DE30 | 2025 |  | 6.5 | 1077 [snapshot 2026-08] | 285 [snapshot 2026-08] | 3685265
DE30 | 2024 | 19.976 [sampled] | 5.6 | 1077 [snapshot 2026-08] | 285 [snapshot 2026-08] | 3662381
DE30 | 2023 | 20.6769 [sampled] | 5.2 | 1077 [snapshot 2026-08] | 285 [snapshot 2026-08] | 3632853 [b]
DE40 | 2025 |  | 3.8 | 1057 [snapshot 2026-08] | 225 [snapshot 2026-08] | 2556747
DE40 | 2024 | 19.5043 [sampled] | 3.2 | 1057 [snapshot 2026-08] | 225 [snapshot 2026-08] | 2554464
DE40 | 2023 | 20.2612 [sampled] | 3.3 | 1057 [snapshot 2026-08] | 225 [snapshot 2026-08] | 2545159 [b]
DE50 | 2025 |  | 5.1 [u] | 257 [snapshot 2026-08] | 16 [snapshot 2026-08] | 704881
DE50 | 2024 | 18.4956 [sampled] | 4.9 [u] | 257 [snapshot 2026-08] | 16 [snapshot 2026-08] | 702655
DE50 | 2023 | 18.2471 [sampled] | 4.7 [u] | 257 [snapshot 2026-08] | 16 [snapshot 2026-08] | 695758 [b]
DE60 | 2025 |  | 5.3 | 561 [snapshot 2026-08] | 114 [snapshot 2026-08] | 1862565
DE60 | 2024 | 18.4854 [sampled] | 4.8 | 561 [snapshot 2026-08] | 114 [snapshot 2026-08] | 1851596
DE60 | 2023 | 18.5456 [sampled] | 4.1 | 561 [snapshot 2026-08] | 114 [snapshot 2026-08] | 1832675 [b]
DE71 | 2025 |  | 3.6 | 1391 [snapshot 2026-08] | 254 [snapshot 2026-08] | 4039611
DE71 | 2024 | 19.1229 [sampled] | 3.4 | 1391 [snapshot 2026-08] | 254 [snapshot 2026-08] | 4024030
DE71 | 2023 | 20.9933 [sampled] | 3.1 | 1391 [snapshot 2026-08] | 254 [snapshot 2026-08] | 4001146 [b]
DE72 | 2025 |  | 2.7 [u] | 465 [snapshot 2026-08] | 49 [snapshot 2026-08] | 1040290
DE72 | 2024 | 17.6891 [sampled] | 3.7 [u] | 465 [snapshot 2026-08] | 49 [snapshot 2026-08] | 1041453
DE72 | 2023 | 19.6261 [sampled] | 3 [u] | 465 [snapshot 2026-08] | 49 [snapshot 2026-08] | 1036748 [b]
DE73 | 2025 |  | 3.6 [u] | 572 [snapshot 2026-08] | 59 [snapshot 2026-08] | 1200892
DE73 | 2024 | 17.41 [sampled] | 2.2 [u] | 572 [snapshot 2026-08] | 59 [snapshot 2026-08] | 1202063
DE73 | 2023 | 19.1607 [sampled] | 2.1 [u] | 572 [snapshot 2026-08] | 59 [snapshot 2026-08] | 1199039 [b]
DE80 | 2025 |  | 3.5 | 689 [snapshot 2026-08] | 123 [snapshot 2026-08] | 1573597
DE80 | 2024 | 18.7335 [sampled] | 3.7 | 689 [snapshot 2026-08] | 123 [snapshot 2026-08] | 1578041
DE80 | 2023 | 18.5282 [sampled] | 4.3 | 689 [snapshot 2026-08] | 123 [snapshot 2026-08] | 1576049 [b]
DE91 | 2025 |  | 3.9 | 831 [snapshot 2026-08] | 47 [snapshot 2026-08] | 1589423
DE91 | 2024 | 18.1702 [sampled] | 3.7 | 831 [snapshot 2026-08] | 47 [snapshot 2026-08] | 1592700
DE91 | 2023 | 19.1252 [sampled] | 3.1 [u] | 831 [snapshot 2026-08] | 47 [snapshot 2026-08] | 1589602 [b]
DE92 | 2025 |  | 3.9 | 841 [snapshot 2026-08] | 122 [snapshot 2026-08] | 2123689
DE92 | 2024 | 18.654 [sampled] | 3.1 | 841 [snapshot 2026-08] | 122 [snapshot 2026-08] | 2123401
DE92 | 2023 | 18.932 [sampled] | 3 | 841 [snapshot 2026-08] | 122 [snapshot 2026-08] | 2117034 [b]
DE93 | 2025 |  | 3.3 | 840 [snapshot 2026-08] | 134 [snapshot 2026-08] | 1721892
DE93 | 2024 | 18.7302 [sampled] | 2.7 [u] | 840 [snapshot 2026-08] | 134 [snapshot 2026-08] | 1721982
DE93 | 2023 | 18.6539 [sampled] | 2.6 [u] | 840 [snapshot 2026-08] | 134 [snapshot 2026-08] | 1716631 [b]
DE94 | 2025 |  | 2.9 | 1422 [snapshot 2026-08] | 89 [snapshot 2026-08] | 2569485
DE94 | 2024 | 18.5883 [sampled] | 3.1 | 1422 [snapshot 2026-08] | 89 [snapshot 2026-08] | 2570052
DE94 | 2023 | 18.4897 [sampled] | 2.5 | 1422 [snapshot 2026-08] | 89 [snapshot 2026-08] | 2559680 [b]
DEA1 | 2025 |  | 4.8 | 2040 [snapshot 2026-08] | 159 [snapshot 2026-08] | 5244379
DEA1 | 2024 | 19.277 [sampled] | 4.3 | 2040 [snapshot 2026-08] | 159 [snapshot 2026-08] | 5238909
DEA1 | 2023 | 19.5931 [sampled] | 4 | 2040 [snapshot 2026-08] | 159 [snapshot 2026-08] | 5222540 [b]
DEA2 | 2025 |  | 3.9 | 1718 [snapshot 2026-08] | 114 [snapshot 2026-08] | 4486282
DEA2 | 2024 | 18.1619 [sampled] | 3.7 | 1718 [snapshot 2026-08] | 114 [snapshot 2026-08] | 4478118
DEA2 | 2023 | 19.2865 [sampled] | 3.3 | 1718 [snapshot 2026-08] | 114 [snapshot 2026-08] | 4461422 [b]
DEA3 | 2025 |  | 3.4 | 1117 [snapshot 2026-08] | 65 [snapshot 2026-08] | 2659034
DEA3 | 2024 | 19.1368 [sampled] | 3.4 | 1117 [snapshot 2026-08] | 65 [snapshot 2026-08] | 2654384
DEA3 | 2023 | 19.4477 [sampled] | 3 | 1117 [snapshot 2026-08] | 65 [snapshot 2026-08] | 2640307 [b]
DEA4 | 2025 |  | 3.7 | 994 [snapshot 2026-08] | 66 [snapshot 2026-08] | 2072861
DEA4 | 2024 | 18.2294 [sampled] | 3.4 | 994 [snapshot 2026-08] | 66 [snapshot 2026-08] | 2072972
DEA4 | 2023 | 18.918 [sampled] | 2.4 | 994 [snapshot 2026-08] | 66 [snapshot 2026-08] | 2070052 [b]
DEA5 | 2025 |  | 4.7 | 1540 [snapshot 2026-08] | 132 [snapshot 2026-08] | 3571898
DEA5 | 2024 | 17.414 [sampled] | 4.1 | 1540 [snapshot 2026-08] | 132 [snapshot 2026-08] | 3573137
DEA5 | 2023 | 18.5059 [sampled] | 3.6 | 1540 [snapshot 2026-08] | 132 [snapshot 2026-08] | 3570099 [b]
DEB1 | 2025 |  | 2.9 [u] | 679 [snapshot 2026-08] | 98 [snapshot 2026-08] | 1530208
DEB1 | 2024 | 17.942 [sampled] | 3.3 | 679 [snapshot 2026-08] | 98 [snapshot 2026-08] | 1527616
DEB1 | 2023 | 19.4622 [sampled] | 2.5 [u] | 679 [snapshot 2026-08] | 98 [snapshot 2026-08] | 1522385 [b]
DEB2 | 2025 |  |  | 260 [snapshot 2026-08] | 29 [snapshot 2026-08] | 525583
DEB2 | 2024 | 17.693 [sampled] |  | 260 [snapshot 2026-08] | 29 [snapshot 2026-08] | 526651
DEB2 | 2023 | 18.8262 [sampled] |  | 260 [snapshot 2026-08] | 29 [snapshot 2026-08] | 524876 [b]
DEB3 | 2025 |  | 4 | 808 [snapshot 2026-08] | 104 [snapshot 2026-08] | 2073778
DEB3 | 2024 | 19.55 [sampled] | 3.4 | 808 [snapshot 2026-08] | 104 [snapshot 2026-08] | 2070896
DEB3 | 2023 | 21.1444 [sampled] | 3.6 | 808 [snapshot 2026-08] | 104 [snapshot 2026-08] | 2061294 [b]
DEC0 | 2025 |  | 4.1 [u] | 417 [snapshot 2026-08] | 41 [snapshot 2026-08] | 1012141
DEC0 | 2024 | 19.2411 [sampled] | 3.6 [u] | 417 [snapshot 2026-08] | 41 [snapshot 2026-08] | 1014047
DEC0 | 2023 | 20.2428 [sampled] | 3.4 [u] | 417 [snapshot 2026-08] | 41 [snapshot 2026-08] | 1011891 [b]
DED2 | 2025 |  | 4.7 | 781 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1584687
DED2 | 2024 | 19.3969 [sampled] | 3.6 | 781 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1589143
DED2 | 2023 | 20.375 [sampled] | 2.4 [u] | 781 [snapshot 2026-08] | 100 [snapshot 2026-08] | 1588724 [b]
DED4 | 2025 |  | 4.4 | 707 [snapshot 2026-08] | 111 [snapshot 2026-08] | 1386336
DED4 | 2024 | 17.9947 [sampled] | 3.1 [u] | 707 [snapshot 2026-08] | 111 [snapshot 2026-08] | 1396049
DED4 | 2023 | 19.5935 [sampled] | 3.3 [u] | 707 [snapshot 2026-08] | 111 [snapshot 2026-08] | 1397272 [b]
DED5 | 2025 |  | 5.2 | 468 [snapshot 2026-08] | 60 [snapshot 2026-08] | 1071399
DED5 | 2024 | 19.7156 [sampled] | 5.5 | 468 [snapshot 2026-08] | 60 [snapshot 2026-08] | 1069497
DED5 | 2023 | 21.1842 [sampled] | 4.5 | 468 [snapshot 2026-08] | 60 [snapshot 2026-08] | 1063971 [b]
DEE0 | 2025 |  | 4.9 | 1087 [snapshot 2026-08] | 180 [snapshot 2026-08] | 2135597
DEE0 | 2024 | 19.0414 [sampled] | 4.2 | 1087 [snapshot 2026-08] | 180 [snapshot 2026-08] | 2144570
DEE0 | 2023 | 20.6897 [sampled] | 3.8 | 1087 [snapshot 2026-08] | 180 [snapshot 2026-08] | 2150239 [b]
DEF0 | 2025 |  | 3.7 | 1163 [snapshot 2026-08] | 112 [snapshot 2026-08] | 2959517
DEF0 | 2024 | 17.948 [sampled] | 3.4 | 1163 [snapshot 2026-08] | 112 [snapshot 2026-08] | 2953202
DEF0 | 2023 | 17.9676 [sampled] | 3.1 | 1163 [snapshot 2026-08] | 112 [snapshot 2026-08] | 2939283 [b]
DEG0 | 2025 |  | 3.7 | 1108 [snapshot 2026-08] | 153 [snapshot 2026-08] | 2100277
DEG0 | 2024 | 17.6198 [sampled] | 3.5 | 1108 [snapshot 2026-08] | 153 [snapshot 2026-08] | 2114870
DEG0 | 2023 | 19.91 [sampled] | 3.1 | 1108 [snapshot 2026-08] | 153 [snapshot 2026-08] | 2118830 [b]
[Instantanés, état courant répété sur chaque période : schools_count (2026-08, osm_completeness_unknown), train_stations_count (2026-08, osm_completeness_unknown)]
[Source : copernicus (ARCO-ERA5 2026-09-24), eurostat (unemployment_rate 30.06.2026, population 21.08.2026), osm (extrait 2026-08)]
```

## Answer

I have everything I need from that one cross‑source query. Here's my analysis.

## Method (short version)

I pulled 5 indicators for all **45 NUTS2 regions** (36 German + 9 Austrian): summer surface temperature (Copernicus, Jun–Aug mean, 2024), unemployment (Eurostat, 2024), school count, train‑station count (OSM snapshot), and population. I computed schools and train stations **per 1,000 residents** as you asked.

**On "mild":** I interpreted it as *comfortably warm but not scorching* — so I softly filtered to regions whose summer mean sits around **17.5–20 °C** (the comfortable mid‑band), which drops out the hot Vienna‑hinterland (Wien 24.1 °C, Burgenland 23.2 °C, N.Ö. 21.4 °C) and the cool Alpine regions (Tirol 12.4 °C, Salzburg 15.0 °C, Vorarlberg 14.8 °C, Kärnten 16.9 °C). Within that band I balanced **low unemployment + schools per capita + stations per capita**.

## The 5 best regions

| # | Region (code) | Country | Summer mean (°C) | Unemployment (2024) | Schools /1k | Stations /1k | Population (2024) |
|---|---------------|---------|:---:|:---:|:---:|:---:|---:|
| 1 | **Oberösterreich** (AT31) | AT | 19.7 | 3.8 % | 0.640 | 0.091 | 1,530,349 |
| 2 | **Steiermark** (AT22) | AT | 18.4 | 4.4 % | 0.608 | 0.095 | 1,269,801 |
| 3 | **Lüneburg** (DE93) | DE | 18.7 | 2.7 % | 0.488 | 0.078 | 1,721,982 |
| 4 | **Oberfranken** (DE24) | DE | 18.4 | 2.7 % | 0.521 | 0.059 | 1,055,751 |
| 5 | **Tübingen** (DE14) | DE | 18.4 | 2.8 % | 0.531 | 0.056 | 1,900,862 |

*Schools/1k = schools per 1,000 residents; Stations/1k = train stations per 1,000 residents.*

- **Near‑miss:** **Freiburg (DE13)** — 19.2 °C, 2.5 % unemployment (the best of the German top 5), 0.527 /1k schools, 0.052 /1k stations. It's essentially tied with Tübingen.
- **The trade‑off you should see:** the two Austrian regions win because the small *Bundesländer* have **denser school/train networks per capita** (and good job markets), while the German regions win on **very low unemployment** and cooler summers. No single region is best at all three.

### ⚠️ Important fork: what *did* you mean by "mild"?
If by "mild" you actually mean **cool/refreshing** (many families love that), flip the temperature lens and **Tirol (AT33)** jumps to the top — it has the *best* per‑capita schools (0.92 /1k), strong per‑capita stations (0.110 /1k), cool summers (12.4 °C) and 3.1 % unemployment. **Salzburg** and **Vorarlberg** are the same story. So: *mild = pleasantly warm* → table above; *mild = cool* → Tirol, Salzburg, Vorarlberg.

## What the data **cannot** tell you

1. **LST ≠ air temperature.** The Copernicus figure is *land‑surface* temperature, which runs several degrees hotter than the air (and even hotter over cities — urban heat island). The **ranking** (cooler vs. warmer regions) is still meaningful, but the absolute °C is a proxy, not what your kids will actually feel.
2. **Raw counts ≠ quality or capacity.** "980 schools" says nothing about teaching quality, classroom space, waiting lists, or whether there's a **place available for your children**. For two young kids the real bottleneck is usually **daycare/nursery (Kita) places**, not school buildings — and those are not in this dataset at all.
3. **Per‑capita has a built‑in bias.** Dividing by population *mechanically* favors small, low‑density or mountainous regions (fewer people to divide by). Part of why the Austrian *Bundesländer* rank high is the small denominator, not necessarily a richer service. "More per person" can still mean fewer total schools and a less frequent train timetable.
4. **"Many train stations" ≠ good connections.** The OSM count includes tiny local halts of every type, not just major intercity stops. It says nothing about frequency, directness, or how far your home is from the nearest stop.
5. **Cost of living / housing.** Huge for a young family, and entirely absent from this data — Munich/Upper Bavaria, Vienna suburbs and the Alps are pricey; Lüneburg and Oberfranken are notably cheaper.
6. **Your specific job.** A region's 2.7 % unemployment does not guarantee a job in *your* field, at *your* salary, with your *commute*.
7. **Climate detail.** A single Jun–Aug mean hides heat‑wave frequency, humidity, rain, sunshine, seasonality, and microclimate (valley vs. mountain vs. city can differ a lot with the same mean).
8. **Pediatric/health access, safety, family services, nature/outdoor space, integration** — none of these are in the dataset.

**Data vintages & flags:** LST = Copernicus 2024 (sampled); unemployment = Eurostat 2024 (2025 partial; Lüneburg & Oberfranken flagged as estimated `[u]`); OSM counts = 2026‑08 snapshot with **completeness "unknown"** (rural/Alpine areas may be under‑ or over‑counted); population = 2024. Trier had no 2024 unemployment figure and was excluded from ranking.

Want me to re‑run the ranking with the "cool summers" lens, or add a cost‑of‑living / housing proxy (e.g. GDP per capita) as a tie‑breaker?

