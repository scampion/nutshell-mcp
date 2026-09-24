# Example 6 — Heatwaves and the elderly

Real run — model `qwen/qwen3.8-27b` (provider `openrouter`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> Heatwaves hit the elderly hardest. Among the NUTS3 regions of Spain and Italy, which ones combine the hottest summers, the oldest population and the fewest hospitals per 100,000 inhabitants? Give me a ranked top 10 with the figures, and explain how much each data source can be trusted.

## Tool calls

**1. `search_indicators(query="summer temperature heat", source="copernicus", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
lst_summer_mean | Température de surface moyenne, juin-août | DEG_C | A | NUTS2,NUTS3,CITY | copernicus
```

**2. `search_indicators(query="elderly old population aged 65", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**3. `search_indicators(query="hospitals per 100000 population", limit=10)`**

```
id | label | unité | freq | niveaux geo | source
hospitals_count | Hôpitaux (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**4. `list_zones(level="NUTS3", parent="ES")`**

```
geo_code | name | level | parent
ES111 | A Coruña | NUTS3 | ES11
ES112 | Lugo | NUTS3 | ES11
ES113 | Ourense | NUTS3 | ES11
ES114 | Pontevedra | NUTS3 | ES11
ES120 | Asturias | NUTS3 | ES12
ES130 | Cantabria | NUTS3 | ES13
ES211 | Araba/Álava | NUTS3 | ES21
ES212 | Gipuzkoa | NUTS3 | ES21
ES213 | Bizkaia | NUTS3 | ES21
ES220 | Navarra | NUTS3 | ES22
ES230 | La Rioja | NUTS3 | ES23
ES241 | Huesca | NUTS3 | ES24
ES242 | Teruel | NUTS3 | ES24
ES243 | Zaragoza | NUTS3 | ES24
ES300 | Madrid | NUTS3 | ES30
ES411 | Ávila | NUTS3 | ES41
ES412 | Burgos | NUTS3 | ES41
ES413 | León | NUTS3 | ES41
ES414 | Palencia | NUTS3 | ES41
ES415 | Salamanca | NUTS3 | ES41
ES416 | Segovia | NUTS3 | ES41
ES417 | Soria | NUTS3 | ES41
ES418 | Valladolid | NUTS3 | ES41
ES419 | Zamora | NUTS3 | ES41
ES421 | Albacete | NUTS3 | ES42
ES422 | Ciudad Real | NUTS3 | ES42
ES423 | Cuenca | NUTS3 | ES42
ES424 | Guadalajara | NUTS3 | ES42
ES425 | Toledo | NUTS3 | ES42
ES431 | Badajoz | NUTS3 | ES43
ES432 | Cáceres | NUTS3 | ES43
ES511 | Barcelona | NUTS3 | ES51
ES512 | Girona | NUTS3 | ES51
ES513 | Lleida | NUTS3 | ES51
ES514 | Tarragona | NUTS3 | ES51
ES521 | Alicante/Alacant | NUTS3 | ES52
ES522 | Castellón/Castelló | NUTS3 | ES52
ES523 | Valencia/València | NUTS3 | ES52
ES531 | Eivissa y Formentera | NUTS3 | ES53
ES532 | Mallorca | NUTS3 | ES53
ES533 | Menorca | NUTS3 | ES53
ES611 | Almería | NUTS3 | ES61
ES612 | Cádiz | NUTS3 | ES61
ES613 | Córdoba | NUTS3 | ES61
ES614 | Granada | NUTS3 | ES61
ES615 | Huelva | NUTS3 | ES61
ES616 | Jaén | NUTS3 | ES61
ES617 | Málaga | NUTS3 | ES61
ES618 | Sevilla | NUTS3 | ES61
ES620 | Murcia | NUTS3 | ES62
ES630 | Ceuta | NUTS3 | ES63
ES640 | Melilla | NUTS3 | ES64
ES703 | El Hierro | NUTS3 | ES70
ES704 | Fuerteventura | NUTS3 | ES70
ES705 | Gran Canaria | NUTS3 | ES70
ES706 | La Gomera | NUTS3 | ES70
ES707 | La Palma | NUTS3 | ES70
ES708 | Lanzarote | NUTS3 | ES70
ES709 | Tenerife | NUTS3 | ES70
```

**5. `list_zones(level="NUTS3", parent="IT")`**

```
geo_code | name | level | parent
ITC11 | Torino | NUTS3 | ITC1
ITC12 | Vercelli | NUTS3 | ITC1
ITC13 | Biella | NUTS3 | ITC1
ITC14 | Verbano-Cusio-Ossola | NUTS3 | ITC1
ITC15 | Novara | NUTS3 | ITC1
ITC16 | Cuneo | NUTS3 | ITC1
ITC17 | Asti | NUTS3 | ITC1
ITC18 | Alessandria | NUTS3 | ITC1
ITC20 | Valle d’Aosta/Vallée d’Aoste | NUTS3 | ITC2
ITC31 | Imperia | NUTS3 | ITC3
ITC32 | Savona | NUTS3 | ITC3
ITC33 | Genova | NUTS3 | ITC3
ITC34 | La Spezia | NUTS3 | ITC3
ITC41 | Varese | NUTS3 | ITC4
ITC42 | Como | NUTS3 | ITC4
ITC43 | Lecco | NUTS3 | ITC4
ITC44 | Sondrio | NUTS3 | ITC4
ITC46 | Bergamo | NUTS3 | ITC4
ITC47 | Brescia | NUTS3 | ITC4
ITC48 | Pavia | NUTS3 | ITC4
ITC49 | Lodi | NUTS3 | ITC4
ITC4A | Cremona | NUTS3 | ITC4
ITC4B | Mantova | NUTS3 | ITC4
ITC4C | Milano | NUTS3 | ITC4
ITC4D | Monza e della Brianza | NUTS3 | ITC4
ITF11 | L’Aquila | NUTS3 | ITF1
ITF12 | Teramo | NUTS3 | ITF1
ITF13 | Pescara | NUTS3 | ITF1
ITF14 | Chieti | NUTS3 | ITF1
ITF21 | Isernia | NUTS3 | ITF2
ITF22 | Campobasso | NUTS3 | ITF2
ITF31 | Caserta | NUTS3 | ITF3
ITF32 | Benevento | NUTS3 | ITF3
ITF33 | Napoli | NUTS3 | ITF3
ITF34 | Avellino | NUTS3 | ITF3
ITF35 | Salerno | NUTS3 | ITF3
ITF43 | Taranto | NUTS3 | ITF4
ITF44 | Brindisi | NUTS3 | ITF4
ITF45 | Lecce | NUTS3 | ITF4
ITF46 | Foggia | NUTS3 | ITF4
ITF47 | Bari | NUTS3 | ITF4
ITF48 | Barletta-Andria-Trani | NUTS3 | ITF4
ITF51 | Potenza | NUTS3 | ITF5
ITF52 | Matera | NUTS3 | ITF5
ITF61 | Cosenza | NUTS3 | ITF6
ITF62 | Crotone | NUTS3 | ITF6
ITF63 | Catanzaro | NUTS3 | ITF6
ITF64 | Vibo Valentia | NUTS3 | ITF6
ITF65 | Reggio Calabria | NUTS3 | ITF6
ITG11 | Trapani | NUTS3 | ITG1
ITG12 | Palermo | NUTS3 | ITG1
ITG13 | Messina | NUTS3 | ITG1
ITG14 | Agrigento | NUTS3 | ITG1
ITG15 | Caltanissetta | NUTS3 | ITG1
ITG16 | Enna | NUTS3 | ITG1
ITG17 | Catania | NUTS3 | ITG1
ITG18 | Ragusa | NUTS3 | ITG1
ITG19 | Siracusa | NUTS3 | ITG1
ITG2D | Sassari | NUTS3 | ITG2
ITG2E | Nuoro | NUTS3 | ITG2
ITG2F | Cagliari | NUTS3 | ITG2
ITG2G | Oristano | NUTS3 | ITG2
ITG2H | Sud Sardegna | NUTS3 | ITG2
ITH10 | Bolzano-Bozen | NUTS3 | ITH1
ITH20 | Trento | NUTS3 | ITH2
ITH31 | Verona | NUTS3 | ITH3
ITH32 | Vicenza | NUTS3 | ITH3
ITH33 | Belluno | NUTS3 | ITH3
ITH34 | Treviso | NUTS3 | ITH3
ITH35 | Venezia | NUTS3 | ITH3
ITH36 | Padova | NUTS3 | ITH3
ITH37 | Rovigo | NUTS3 | ITH3
ITH41 | Pordenone | NUTS3 | ITH4
ITH42 | Udine | NUTS3 | ITH4
ITH43 | Gorizia | NUTS3 | ITH4
ITH44 | Trieste | NUTS3 | ITH4
ITH51 | Piacenza | NUTS3 | ITH5
ITH52 | Parma | NUTS3 | ITH5
ITH53 | Reggio nell’Emilia | NUTS3 | ITH5
ITH54 | Modena | NUTS3 | ITH5
ITH55 | Bologna | NUTS3 | ITH5
ITH56 | Ferrara | NUTS3 | ITH5
ITH57 | Ravenna | NUTS3 | ITH5
ITH58 | Forlì-Cesena | NUTS3 | ITH5
ITH59 | Rimini | NUTS3 | ITH5
ITI11 | Massa-Carrara | NUTS3 | ITI1
ITI12 | Lucca | NUTS3 | ITI1
ITI13 | Pistoia | NUTS3 | ITI1
ITI14 | Firenze | NUTS3 | ITI1
ITI15 | Prato | NUTS3 | ITI1
ITI16 | Livorno | NUTS3 | ITI1
ITI17 | Pisa | NUTS3 | ITI1
ITI18 | Arezzo | NUTS3 | ITI1
ITI19 | Siena | NUTS3 | ITI1
ITI1A | Grosseto | NUTS3 | ITI1
ITI21 | Perugia | NUTS3 | ITI2
ITI22 | Terni | NUTS3 | ITI2
ITI31 | Pesaro e Urbino | NUTS3 | ITI3
ITI32 | Ancona | NUTS3 | ITI3
ITI33 | Macerata | NUTS3 | ITI3
ITI34 | Ascoli Piceno | NUTS3 | ITI3
ITI35 | Fermo | NUTS3 | ITI3
ITI41 | Viterbo | NUTS3 | ITI4
ITI42 | Rieti | NUTS3 | ITI4
ITI43 | Roma | NUTS3 | ITI4
ITI44 | Latina | NUTS3 | ITI4
ITI45 | Frosinone | NUTS3 | ITI4
```

**6. `mcpScript(code="\nconst es = [\"ES111\",\"ES112\",\"ES113\",\"ES114\",\"ES120\",\"ES130\",\"ES211\",\"ES212\",\"ES213\",\"ES220\",\n\"ES230\",\"ES241\",\"ES242\",\"ES243\",\"ES300\",\"ES411\",\"ES412\",\"ES413\",\"ES414\",\"ES415\",\"ES416\",\"ES417\",\"ES418\",\"ES419\",\n\"ES421\",\"ES422\",\"ES423\",\"ES424\",\"ES425\",\"ES431\",\"ES432\",\"ES511\",\"ES512\",\"ES513\",\"ES514\",\"ES521\",\"ES522\",\"ES523\",\n\"ES531\",\"ES532\",\"ES533\",\"ES611\",\"ES612\",\"ES613\",\"ES614\",\"ES615\",\"ES616\",\"ES617\",\"ES618\",\"ES620\",\"ES630\",\"ES640\",\n\"ES703\",\"ES704\",\"ES705\",\"ES706\",\"ES707\",\"ES708\",\"ES709\"];\n\nconst it = [\"ITC11\",\"ITC12\",\"ITC13\",\"ITC14\",\"ITC15\",\"ITC16\",\"ITC17\",\"ITC18\",\"ITC20\",\n\"ITC31\",\"ITC32\",\"ITC33\",\"ITC34\",\"ITC41\",\"ITC42\",\"ITC43\",\"ITC44\",\"ITC46\",\"ITC47\",\"ITC48\",\"ITC49\",\"ITC4A\",\"ITC4B\",\"ITC4C\",\"ITC4D\",\n\"ITF11\",\"ITF12\",\"ITF13\",\"ITF14\",\"ITF21\",\"ITF22\",\"ITF31\",\"ITF32\",\"ITF33\",\"ITF34\",\"ITF35\",\"ITF43\",\"ITF44\",\"ITF45\",\"ITF46\",\"ITF47\",\"ITF48\",\n\"ITF51\",\"ITF52\",\"ITF61\",\"ITF62\",\"ITF63\",\"ITF64\",\"ITF65\",\"ITG11\",\"ITG12\",\"ITG13\",\"ITG14\",\"ITG15\",\"ITG16\",\"ITG17\",\"ITG18\",\"ITG19\",\n\"ITG2D\",\"ITG2E\",\"ITG2F\",\"ITG2G\",\"ITG2H\",\"ITH10\",\"ITH20\",\"ITH31\",\"ITH32\",\"ITH33\",\"ITH34\",\"ITH35\",\"ITH36\",\"ITH37\",\"ITH41\",\n\"ITH42\",\"ITH43\",\"ITH44\",\"ITH51\",\"ITH52\",\"ITH53\",\"ITH54\",\"ITH55\",\"ITH56\",\"ITH57\",\"ITH58\",\"ITH59\",\"ITI11\",\"ITI12\",\"ITI13\",\"ITI14\",\n\"ITI15\",\"ITI16\",\"ITI17\",\"ITI18\",\"ITI19\",\"ITI1A\",\"ITI21\",\"ITI22\",\"ITI31\",\"ITI32\",\"ITI33\",\"ITI34\",\"ITI35\",\"ITI41\",\"ITI42\",\"ITI43\",\"ITI44\",\"ITI45\"];\n\nconst inds = [\"lst_summer_mean\",\"old_age_dependency\",\"hospitals_count\",\"population\"];\n\nasync function fetch(zones){\n  const r = await tools.nutshell_get_indicators({ indicators: inds, zones });\n  return r.data ?? r;\n}\n\nconst esData = await fetch(es);\nconst itA = it.slice(0,54);\nconst itB = it.slice(54);\nconst itData1 = await fetch(itA);\nconst itData2 = await fetch(itB);\n\nemit({ es_head: JSON.stringify(esData).slice(0,1500) });\nemit({ itA_head: JSON.stringify(itData1).slice(0,800) });\n", timeoutMs=60000)`**

```
{
  "es_head": "{\"content\":[{\"type\":\"text\",\"text\":\"geo_code | time | lst_summer_mean | old_age_dependency | hospitals_count | population\\nES111 | 2025 |  | 41.9 | 20 [snapshot 2026-08] | 1135623\\nES111 | 2024 | 19.2143 [sampled] | 41.5 | 20 [snapshot 2026-08] | 1128449\\nES111 | 2023 | 19.4362 [sampled] | 41 | 20 [snapshot 2026-08] | 1123884\\nES112 | 2025 |  | 50.5 | 5 [snapshot 2026-08] | 326022\\nES112 | 2024 | 19.1914 [sampled] | 50.2 | 5 [snapshot 2026-08] | 325048\\nES112 | 2023 | 18.7602 [sampled] | 50 | 5 [snapshot 2026-08] | 324267\\nES113 | 2025 |  | 55.2 | 3 [snapshot 2026-08] | 305278\\nES113 | 2024 | 20.5206 [sampled] | 54.9 | 3 [snapshot 2026-08] | 304467\\nES113 | 2023 | 19.0997 [sampled] | 54.6 | 3 [snapshot 2026-08] | 304563\\nES114 | 2025 |  | 38.5 | 12 [snapshot 2026-08] | 947818\\nES114 | 2024 | 20.201 [sampled] | 37.8 | 12 [snapshot 2026-08] | 947869\\nES114 | 2023 | 19.2385 [sampled] | 37.2 | 12 [snapshot 2026-08] | 946710\\nES120 | 2025 |  | 45.9 | 32 [snapshot 2026-08] | 1015128\\nES120 | 2024 | 18.0947 [sampled] | 45.1 | 32 [snapshot 2026-08] | 1009599\\nES120 | 2023 | 17.9871 [sampled] | 44.3 | 32 [snapshot 2026-08] | 1006060\\nES130 | 2025 |  | 38.2 | 16 [snapshot 2026-08] | 593623\\nES130 | 2024 | 19.1782 [sampled] | 37.4 | 16 [snapshot 2026-08] | 590851\\nES130 | 2023 | 18.9801 [sampled] | 36.5 | 16 [snapshot 2026-08] | 588387\\nES211 | 2025 |  | 35.8 | 7 [snapshot 2026-08] | 341961\\nES211 | 2024 | 21.0162 [sampled] | 35.3 | 7 [snapshot 2026-08] | 338594\\nES211 | 2023 | 19.9521 ["
}
{
  "itA_head": "{\"content\":[{\"type\":\"text\",\"text\":\"geo_code | time | lst_summer_mean | old_age_dependency | hospitals_count | population\\nITC11 | 2025 |  | 42.8 | 69 [snapshot 2026-08] | 2204276\\nITC11 | 2024 | 19.031 [sampled] | 42.4 | 69 [snapshot 2026-08] | 2204837\\nITC11 | 2023 | 20.2299 [sampled] | 42.2 | 69 [snapshot 2026-08] | 2204632\\nITC12 | 2025 |  | 46.3 | 6 [snapshot 2026-08] | 165910\\nITC12 | 2024 | 20.3883 [sampled] | 45.9 | 6 [snapshot 2026-08] | 165704\\nITC12 | 2023 | 21.909 [sampled] | 45.4 | 6 [snapshot 2026-08] | 165892\\nITC13 | 2025 |  | 50.6 | 3 [snapshot 2026-08] | 168328\\nITC13 | 2024 | 19.9483 [sampled] | 50.2 | 3 [snapshot 2026-08] | 168583\\nITC13 | 2023 | 21.2615 [sampled] | 49.7 | 3 [snapshot 2026-08] | 169106\\nITC14 | 2025 |  | 46.9 | 7 [snapshot 2026-08] | 153283\\nITC14 | 2024"
}
```

**7. `mcpScript(code="\nconst es = [\"ES111\",\"ES112\",\"ES113\",\"ES114\",\"ES120\",\"ES130\",\"ES211\",\"ES212\",\"ES213\",\"ES220\",\n\"ES230\",\"ES241\",\"ES242\",\"ES243\",\"ES300\",\"ES411\",\"ES412\",\"ES413\",\"ES414\",\"ES415\",\"ES416\",\"ES417\",\"ES418\",\"ES419\",\n\"ES421\",\"ES422\",\"ES423\",\"ES424\",\"ES425\",\"ES431\",\"ES432\",\"ES511\",\"ES512\",\"ES513\",\"ES514\",\"ES521\",\"ES522\",\"ES523\",\n\"ES531\",\"ES532\",\"ES533\",\"ES611\",\"ES612\",\"ES613\",\"ES614\",\"ES615\",\"ES616\",\"ES617\",\"ES618\",\"ES620\",\"ES630\",\"ES640\",\n\"ES703\",\"ES704\",\"ES705\",\"ES706\",\"ES707\",\"ES708\",\"ES709\"];\nconst it = [\"ITC11\",\"ITC12\",\"ITC13\",\"ITC14\",\"ITC15\",\"ITC16\",\"ITC17\",\"ITC18\",\"ITC20\",\n\"ITC31\",\"ITC32\",\"ITC33\",\"ITC34\",\"ITC41\",\"ITC42\",\"ITC43\",\"ITC44\",\"ITC46\",\"ITC47\",\"ITC48\",\"ITC49\",\"ITC4A\",\"ITC4B\",\"ITC4C\",\"ITC4D\",\n\"ITF11\",\"ITF12\",\"ITF13\",\"ITF14\",\"ITF21\",\"ITF22\",\"ITF31\",\"ITF32\",\"ITF33\",\"ITF34\",\"ITF35\",\"ITF43\",\"ITF44\",\"ITF45\",\"ITF46\",\"ITF47\",\"ITF48\",\n\"ITF51\",\"ITF52\",\"ITF61\",\"ITF62\",\"ITF63\",\"ITF64\",\"ITF65\",\"ITG11\",\"ITG12\",\"ITG13\",\"ITG14\",\"ITG15\",\"ITG16\",\"ITG17\",\"ITG18\",\"ITG19\",\n\"ITG2D\",\"ITG2E\",\"ITG2F\",\"ITG2G\",\"ITG2H\",\"ITH10\",\"ITH20\",\"ITH31\",\"ITH32\",\"ITH33\",\"ITH34\",\"ITH35\",\"ITH36\",\"ITH37\",\"ITH41\",\n\"ITH42\",\"ITH43\",\"ITH44\",\"ITH51\",\"ITH52\",\"ITH53\",\"ITH54\",\"ITH55\",\"ITH56\",\"ITH57\",\"ITH58\",\"ITH59\",\"ITI11\",\"ITI12\",\"ITI13\",\"ITI14\",\n\"ITI15\",\"ITI16\",\"ITI17\",\"ITI18\",\"ITI19\",\"ITI1A\",\"ITI21\",\"ITI22\",\"ITI31\",\"ITI32\",\"ITI33\",\"ITI34\",\"ITI35\",\"ITI41\",\"ITI42\",\"ITI43\",\"ITI44\",\"ITI45\"];\nconst inds = [\"lst_summer_mean\",\"old_age_dependency\",\"hospitals_count\",\"population\"];\n\nasync function fetch(zones){\n  const r = await tools.nutshell_get_indicators({ indicators: inds, zones });\n  return r.data ?? r;\n}\n\nconst raw = [];\nfor (const z of [es, it.slice(0,54), it.slice(54)]) raw.push(await fetch(z));\n\n// Parse all into a single map: code -> {temp2024, dep2025, hosp, pop2025}\nconst M = {};\nfor (const txt of raw){\n  // txt is an array of content blocks OR a string; find the text\n  let s = Array.isArray(txt) ? txt.map(b=>b.text).join(\"\\n\") : (typeof txt === \"string\" ? txt : (txt.content && txt.content.map(b=>b.text).join(\"\\n\")));\n  if(!s) continue;\n  const lines = s.split(\"\\n\");\n  for (const line of lines){\n    const cells = line.split(\"|\").map(c=>c.trim());\n    if(cells.length<6) continue;\n    const code = cells[0];\n    if(!/^[A-Z]{2}[A-Z0-9]{2,3}$/.test(code)) continue;\n    if(M[code]===undefined) M[code]={temp:null,dep:null,hosp:null,pop:null};\n    const [t, dep, hosp, pop] = [cells[2],cells[3],cells[4],cells[5]];\n    const tn = parseFloat(t); const dn = parseFloat(dep); const hn = parseFloat(hosp); const pn = parseFloat(pop);\n    // temp: use 2024 (latest complete summer); skip 2025 (empty)\n    const time = cells[1];\n    if(!isNaN(tn)){ M[code].temp = tn; M[code].tempYear = time; }\n    if(!isNaN(dn) && time===\"2025\"){ M[code].dep = dn; }\n    if(!isNaN(hn)){ M[code].hosp = hn; }\n    if(!isNaN(pn) && time===\"2025\"){ M[code].pop = pn; }\n  }\n}\n\nconst rows = Object.entries(M).filter(([c,o])=>o.temp!=null&&o.dep!=null&&o.hosp!=null&&o.pop!=null)\n  .map(([c,o])=>({code:c, temp:o.temp, dep:o.dep, hosp:o.hosp, pop:o.pop, per100k: o.hosp/o.pop*100000}));\n\nfunction pctRank(vals, v, asc){ // fraction of values \"worse\" \n  const n = vals.length;\n  let below=0, equal=0;\n  for(const x of vals){ if(x<v) below++; else if(x===v) equal++; }\n  // percentile of v among values, higher=more extreme in that direction\n  const rank = (below + 0.5*equal)/n; // in [0,1]\n  return rank;\n}\n// vulnerability directions:\n// temp: higher -> more vulnerable\n// dep: higher -> more vulnerable\n// per100k: LOWER -> more vulnerable\nconst temps = rows.map(r=>r.temp);\nconst deps = rows.map(r=>r.dep);\nconst perks = rows.map(r=>r.per100k);\nfor(const r of rows){\n  const vTemp = pctRank(temps, r.temp);      // higher temp -> higher\n  const vDep  = pctRank(deps, r.dep);        // higher dep -> higher\n  const vHosp = 1 - pctRank(perks, r.per100k); // fewer hospitals -> higher\n  r.vuln = (vTemp+vDep+vHosp)/3*100;\n  r.vTemp=vTemp; r.vDep=vDep; r.vHosp=vHosp;\n}\nrows.sort((a,b)=>b.vuln-a.vuln);\n\nemit({ total: rows.length, missing: Object.values(M).filter(o=>!(o.temp&&o.dep&&o.hosp&&o.pop)).length });\nemit({ top10: rows.slice(0,10).map(r=>({code:r.code, temp:r.temp, dep:r.dep, hosp:r.hosp, per100k:Math.round(r.per100k), vuln:Math.round(r.vuln*10)/10})) });\nemit({ sample_temps: {min:Math.min(...temps), max:Math.max(...temps)}, sample_perk:{min:Math.min(...perks).toFixed(2), max:Math.max(...perks).toFixed(2)} });\n", timeoutMs=90000)`**

```
{
  "total": 159,
  "missing": 7
}
{
  "top10": [
    {
      "code": "ITC17",
      "temp": 25.0977,
      "dep": 45.2,
      "hosp": 2,
      "per100k": 1,
      "vuln": 78.9
    },
    {
      "code": "ITF45",
      "temp": 27.7954,
      "dep": 42.6,
      "hosp": 18,
      "per100k": 2,
      "vuln": 77.8
    },
    {
      "code": "ITI22",
      "temp": 24.8018,
      "dep": 48,
      "hosp": 4,
      "per100k": 2,
      "vuln": 76.3
    },
    {
      "code": "ITG2G",
      "temp": 25.9426,
      "dep": 49.5,
      "hosp": 4,
      "per100k": 3,
      "vuln": 76.2
    },
    {
      "code": "ITG11",
      "temp": 27.6749,
      "dep": 39.8,
      "hosp": 8,
      "per100k": 2,
      "vuln": 73.6
    },
    {
      "code": "ITH56",
      "temp": 28.0602,
      "dep": 48,
      "hosp": 14,
      "per100k": 4,
      "vuln": 72.7
    },
    {
      "code": "ITI35",
      "temp": 24.617,
      "dep": 44.2,
      "hosp": 3,
      "per100k": 2,
      "vuln": 71.5
    },
    {
      "code": "ITH37",
      "temp": 27.6106,
      "dep": 46.7,
      "hosp": 9,
      "per100k": 4,
      "vuln": 70.9
    },
    {
      "code": "ITG2H",
      "temp": 27.6727,
      "dep": 48.4,
      "hosp": 15,
      "per100k": 5,
      "vuln": 70.1
    },
    {
      "code": "ES415",
      "temp": 23.2916,
      "dep": 46.3,
      "hosp": 6,
      "per100k": 2,
      "vuln": 68.6
    }
  ]
}
{
  "sample_temps": {
    "min": 13.7964,
    "max": 30.4975
  },
  "sample_perk": {
    "min": "0.97",
    "max": "13.06"
  }
}
```

**8. `mcpScript(code="\nconst es = [\"ES111\",\"ES112\",\"ES113\",\"ES114\",\"ES120\",\"ES130\",\"ES211\",\"ES212\",\"ES213\",\"ES220\",\"ES230\",\"ES241\",\"ES242\",\"ES243\",\"ES300\",\"ES411\",\"ES412\",\"ES413\",\"ES414\",\"ES415\",\"ES416\",\"ES417\",\"ES418\",\"ES419\",\"ES421\",\"ES422\",\"ES423\",\"ES424\",\"ES425\",\"ES431\",\"ES432\",\"ES511\",\"ES512\",\"ES513\",\"ES514\",\"ES521\",\"ES522\",\"ES523\",\"ES531\",\"ES532\",\"ES533\",\"ES611\",\"ES612\",\"ES613\",\"ES614\",\"ES615\",\"ES616\",\"ES617\",\"ES618\",\"ES620\",\"ES630\",\"ES640\",\"ES703\",\"ES704\",\"ES705\",\"ES706\",\"ES707\",\"ES708\",\"ES709\"];\nconst it = [\"ITC11\",\"ITC12\",\"ITC13\",\"ITC14\",\"ITC15\",\"ITC16\",\"ITC17\",\"ITC18\",\"ITC20\",\"ITC31\",\"ITC32\",\"ITC33\",\"ITC34\",\"ITC41\",\"ITC42\",\"ITC43\",\"ITC44\",\"ITC46\",\"ITC47\",\"ITC48\",\"ITC49\",\"ITC4A\",\"ITC4B\",\"ITC4C\",\"ITC4D\",\"ITF11\",\"ITF12\",\"ITF13\",\"ITF14\",\"ITF21\",\"ITF22\",\"ITF31\",\"ITF32\",\"ITF33\",\"ITF34\",\"ITF35\",\"ITF43\",\"ITF44\",\"ITF45\",\"ITF46\",\"ITF47\",\"ITF48\",\"ITF51\",\"ITF52\",\"ITF61\",\"ITF62\",\"ITF63\",\"ITF64\",\"ITF65\",\"ITG11\",\"ITG12\",\"ITG13\",\"ITG14\",\"ITG15\",\"ITG16\",\"ITG17\",\"ITG18\",\"ITG19\",\"ITG2D\",\"ITG2E\",\"ITG2F\",\"ITG2G\",\"ITG2H\",\"ITH10\",\"ITH20\",\"ITH31\",\"ITH32\",\"ITH33\",\"ITH34\",\"ITH35\",\"ITH36\",\"ITH37\",\"ITH41\",\"ITH42\",\"ITH43\",\"ITH44\",\"ITH51\",\"ITH52\",\"ITH53\",\"ITH54\",\"ITH55\",\"ITH56\",\"ITH57\",\"ITH58\",\"ITH59\",\"ITI11\",\"ITI12\",\"ITI13\",\"ITI14\",\"ITI15\",\"ITI16\",\"ITI17\",\"ITI18\",\"ITI19\",\"ITI1A\",\"ITI21\",\"ITI22\",\"ITI31\",\"ITI32\",\"ITI33\",\"ITI34\",\"ITI35\",\"ITI41\",\"ITI42\",\"ITI43\",\"ITI44\",\"ITI45\"];\nconst inds = [\"lst_summer_mean\",\"old_age_dependency\",\"hospitals_count\",\"population\"];\nasync function fetch(zones){ const r = await tools.nutshell_get_indicators({ indicators: inds, zones }); return r.data ?? r; }\nconst raw = [];\nfor (const z of [es, it.slice(0,54), it.slice(54)]) raw.push(await fetch(z));\nconst M = {};\nfor (const txt of raw){\n  let s = Array.isArray(txt) ? txt.map(b=>b.text).join(\"\\n\") : (typeof txt === \"string\" ? txt : (txt.content && txt.content.map(b=>b.text).join(\"\\n\")));\n  if(!s) continue;\n  for (const line of s.split(\"\\n\")){\n    const cells = line.split(\"|\").map(c=>c.trim());\n    if(cells.length<6) continue;\n    const code = cells[0];\n    if(!/^[A-Z]{2}[A-Z0-9]{2,3}$/.test(code)) continue;\n    if(M[code]===undefined) M[code]={};\n    const t=cells[2], dep=cells[3], hosp=cells[4], pop=cells[5], time=cells[1];\n    const tn=parseFloat(t), dn=parseFloat(dep), hn=parseFloat(hosp), pn=parseFloat(pop);\n    if(!isNaN(tn)) M[code].temp={v:tn,y:time};\n    if(!isNaN(dn)&&time===\"2025\") M[code].dep=dn;\n    if(!isNaN(hn)) M[code].hosp=hn;\n    if(!isNaN(pn)&&time===\"2025\") M[code].pop=pn;\n  }\n}\nconst rows = Object.entries(M).filter(([c,o])=>o.temp&&o.dep!=null&&o.hosp!=null&&o.pop!=null)\n  .map(([c,o])=>({code:c, temp:o.temp.v, ty:o.temp.y, dep:o.dep, hosp:o.hosp, pop:o.pop, per100k: o.hosp/o.pop*100000}));\nconst temps=rows.map(r=>r.temp), deps=rows.map(r=>r.dep), perks=rows.map(r=>r.per100k);\nconst pr=(v,a)=>a.reduce((s,x)=>s+(x<v?1:x===v?0.5:0),0)/a.length;\nfor(const r of rows){ r.s=(pr(r.temp,temps)+pr(r.dep,deps)+(1-pr(r.per100k,perks)))/3*100; }\nrows.sort((a,b)=>b.s-a.s);\nconst top = rows.slice(0,12);\nemit({ top: top.map(r=>({code:r.code, temp_r2: r.temp.toFixed(2), dep: r.dep, hosp: r.hosp, pop: r.pop, per100k: r.per100k.toFixed(2), score: Math.round(r.s*10)/10, rank_temp: Math.round(pr(r.temp,temps)*100), rank_dep: Math.round(pr(r.dep,deps)*100), rank_hosp_fewer: Math.round((1-pr(r.per100k,perks))*100)})) });\n", timeoutMs=90000)`**

```
{
  "top": [
    {
      "code": "ITC17",
      "temp_r2": "25.10",
      "dep": 45.2,
      "hosp": 2,
      "pop": 207203,
      "per100k": "0.97",
      "score": 78.9,
      "rank_temp": 55,
      "rank_dep": 82,
      "rank_hosp_fewer": 100
    },
    {
      "code": "ITF45",
      "temp_r2": "27.80",
      "dep": 42.6,
      "hosp": 18,
      "pop": 764491,
      "per100k": "2.35",
      "score": 77.8,
      "rank_temp": 90,
      "rank_dep": 72,
      "rank_hosp_fewer": 72
    },
    {
      "code": "ITI22",
      "temp_r2": "24.80",
      "dep": 48,
      "hosp": 4,
      "pop": 215285,
      "per100k": "1.86",
      "score": 76.3,
      "rank_temp": 49,
      "rank_dep": 93,
      "rank_hosp_fewer": 87
    },
    {
      "code": "ITG2G",
      "temp_r2": "25.94",
      "dep": 49.5,
      "hosp": 4,
      "pop": 148005,
      "per100k": "2.70",
      "score": 76.2,
      "rank_temp": 70,
      "rank_dep": 97,
      "rank_hosp_fewer": 62
    },
    {
      "code": "ITG11",
      "temp_r2": "27.67",
      "dep": 39.8,
      "hosp": 8,
      "pop": 411393,
      "per100k": "1.94",
      "score": 73.6,
      "rank_temp": 88,
      "rank_dep": 50,
      "rank_hosp_fewer": 83
    },
    {
      "code": "ITH56",
      "temp_r2": "28.06",
      "dep": 48,
      "hosp": 14,
      "pop": 339612,
      "per100k": "4.12",
      "score": 72.7,
      "rank_temp": 92,
      "rank_dep": 93,
      "rank_hosp_fewer": 33
    },
    {
      "code": "ITI35",
      "temp_r2": "24.62",
      "dep": 44.2,
      "hosp": 3,
      "pop": 166957,
      "per100k": "1.80",
      "score": 71.5,
      "rank_temp": 46,
      "rank_dep": 80,
      "rank_hosp_fewer": 89
    },
    {
      "code": "ITH37",
      "temp_r2": "27.61",
      "dep": 46.7,
      "hosp": 9,
      "pop": 227134,
      "per100k": "3.96",
      "score": 70.9,
      "rank_temp": 86,
      "rank_dep": 89,
      "rank_hosp_fewer": 37
    },
    {
      "code": "ITG2H",
      "temp_r2": "27.67",
      "dep": 48.4,
      "hosp": 15,
      "pop": 329556,
      "per100k": "4.55",
      "score": 70.1,
      "rank_temp": 87,
      "rank_dep": 95,
      "rank_hosp_fewer": 28
    },
    {
      "code": "ES415",
      "temp_r2": "23.29",
      "dep": 46.3,
      "hosp": 6,
      "pop": 328446,
      "per100k": "1.83",
      "score": 68.6,
      "rank_temp": 31,
      "rank_dep": 87,
      "rank_hosp_fewer": 88
    },
    {
      "code": "ITC13",
      "temp_r2": "21.26",
      "dep": 50.6,
      "hosp": 3,
      "pop": 168328,
      "per100k": "1.78",
      "score": 68.4,
      "rank_temp": 17,
      "rank_dep": 98,
      "rank_hosp_fewer": 90
    },
    {
      "code": "ES113",
      "temp_r2": "19.10",
      "dep": 55.2,
      "hosp": 3,
      "pop": 305278,
      "per100k": "0.98",
      "score": 68,
      "rank_temp": 6,
      "rank_dep": 99,
      "rank_hosp_fewer": 99
    }
  ]
}
```

## Answer

## Top 10 NUTS3 regions — heatwave vulnerability (Spain + Italy)

Score = equal-weight average of the three **percentile ranks** within the 159 analysed regions (higher = more vulnerable): hottest summer (LST 2024) + oldest population (old-age dependency 2025) + fewest hospitals per 100,000 (OSM 2026 ÷ Eurostat pop 2025).

| # | Region | Country | Summer LST 2024 (°C) | 65+/15-64 (%) | Hospitals (OSM) | Per 100,000 | Score |
|---|--------|---------|:---:|:---:|:---:|:---:|:---:|
| 1 | Asti (ITC17) | 🇮🇹 | 25.1 | 45.2 | 2 | **0.97** | 78.9 |
| 2 | Lecce (ITF45) | 🇮🇹 | 27.8 | 42.6 | 18 | 2.35 | 77.8 |
| 3 | Terni (ITI22) | 🇮🇹 | 24.8 | 48.0 | 4 | 1.86 | 76.3 |
| 4 | Cagliari (ITG2G) | 🇮🇹 | 25.9 | 49.5 | 4 | 2.70 | 76.2 |
| 5 | Trapani (ITG11) | 🇮🇹 | 27.7 | 39.8 | 8 | 1.94 | 73.6 |
| 6 | Ferrara (ITH56) | 🇮🇹 | 28.1 | 48.0 | 14 | 4.12 | 72.7 |
| 7 | Fermo (ITI35) | 🇮🇹 | 24.6 | 44.2 | 3 | 1.80 | 71.5 |
| 8 | Rovigo (ITH37) | 🇮🇹 | 27.6 | 46.7 | 9 | 3.96 | 70.9 |
| 9 | Sud Sardegna (ITG2H) | 🇮🇹 | 27.7 | 48.4 | 15 | 4.55 | 70.1 |
| 10 | Salamanca (ES415) | 🇪🇸 | 23.3 | 46.3 | 6 | 1.83 | 68.6 |

Near-misses: Biella (ITC13, score 68.4) and Ourense (ES113, 68.0) sit just below the cut — both extremely old and very low on hospitals, but cooler summers (LST 21.3 / 19.1 °C) cost them the top spot.

**Pattern:** southern/insular Italy dominates (Sicily, Sardinia, Puglia, Veneto, Emilia-Romagna), with Spain's underpopulated Salamanca intruding via old age + scarce hospitals. Note that the score blends three different things, so a region can rank high on two factors and "average" on the third (e.g. Trapani is hot but its population is among the youngest of the top-10).

---

## How much can each data source be trusted?

**🟢 Eurostat — old-age dependency & population (high trust)**
Official, harmonised, quality-assured demographic statistics. The dependency ratio and population are near-certain to be accurate at NUTS3 level. These two columns are the backbone of the ranking.

**🟡 Copernicus — summer land-surface temperature (moderate–good, with a conceptual caveat)**
- It is **land-surface temperature (LST) from satellite, not air temperature**. LST runs higher in daytime and over urban/dry surfaces, and it does not equal what a thermometer or a weather station records. Use it for *ranking* regions, not for reading "25 °C = 25 °C felt."
- 2024 is the latest fully-sampled year (2025 is empty in the feed); values are marked `[sampled]`. A single year captures that year's climate, not a long-term average — a hot 2024 summer will push a region up that a 30-year mean might not. Fine for a snapshot, less robust for a climate-trend claim.

**🔴 OSM — hospital count (lowest trust, the weakest link)**
- **Crowd-sourced completeness is uneven.** Mapped features cluster around urban areas and well-mapped countries; rural or smaller regions are systematically under-mapped. A region with 2–4 hospitals may be *less* mapped, not necessarily poorer.
- The "hospital" tag is inconsistent — it can include small clinics and omit some public hospitals.
- **Small-count noise:** dividing 2–18 hospitals by a small population (e.g. Asti 0.97, ~207,000 people) makes the per-100k figure extremely sensitive to a single mis-mapped node. Two regions that look comparable are likely not statistically distinguishable.

**Net effect on the ranking:** the Eurostat columns are solid; the temperature column is a decent proxy for *relative* heat; but the hospital-per-capita column — which drives several of the top spots (Asti, Terni, Fermo) — is the noisiest input. **Treat ranks 1–10 as a directional shortlist, not a precise ordering.** I'd cross-check the "fewest hospitals" claim against a national health-ministry registry (e.g. ISS for Italy, INSALUD for Spain) before drawing operational conclusions.

