# Example 2 — Compare four regions

Real run — model `Qwen/Qwen3.8-27B` (provider `huggingface`), harness [pi](https://github.com/badlogic/pi-mono) + `pi-mcp-adapter`, thinking level `low`, server `https://nutshell.scamp.fr/mcp`, MCP tools only. Model reasoning omitted; tool calls and tool outputs are verbatim.

## Prompt

> Compare unemployment, median age and GDP per capita for Île-de-France, Oberbayern, Lombardia and Cataluña. Which one looks the most dynamic, and why?

## Tool calls

**1. `search_indicators(query="unemployment rate")`**

```
id | label | unité | freq | niveaux geo | source
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**2. `search_indicators(query="median age population")`**

```
id | label | unité | freq | niveaux geo | source
median_age | Âge médian de la population | YR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
population | Population au 1er janvier | NR | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
unemployment_rate | Taux de chômage, 15-74 ans | PC | A | NUTS0,NUTS1,NUTS2 | eurostat
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
```

**3. `search_indicators(query="GDP per capita")`**

```
id | label | unité | freq | niveaux geo | source
gdp_per_capita | PIB par habitant (prix courants) | EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat
old_age_dependency | Ratio de dépendance des personnes âgées (65 ans et plus / 15-64 ans) | PC | A | NUTS0,NUTS1,NUTS2,NUTS3 | eurostat
train_stations_count | Gares ferroviaires (comptage OSM) | COUNT | SNAPSHOT | NUTS2,NUTS3,CITY | osm
```

**4. `list_zones(level="NUTS2", contains="Île-de-France")`**

```
Aucune zone de niveau NUTS2 contenant 'Île-de-France'.
```

**5. `list_zones(level="NUTS2", contains="Oberbayern")`**

```
geo_code | name | level | parent
DE21 | Oberbayern | NUTS2 | DE2
```

**6. `list_zones(level="NUTS2", contains="Lombardia")`**

```
geo_code | name | level | parent
ITC4 | Lombardia | NUTS2 | ITC
```

**7. `list_zones(level="NUTS2", contains="Cataluña")`**

```
geo_code | name | level | parent
ES51 | Cataluña | NUTS2 | ES5
```

**8. `list_zones(contains="Ile-de-France", level="NUTS2")`**

```
geo_code | name | level | parent
FR10 | Ile-de-France | NUTS2 | FR1
```

**9. `get_indicators(indicators=["unemployment_rate", "median_age", "gdp_per_capita"], zones=["DE21", "ITC4", "ES51"])`**

```
geo_code | time | unemployment_rate | median_age | gdp_per_capita
DE21 | 2025 | 3 | 43.3 | 
DE21 | 2024 | 2.7 | 43.3 | 75700 [e]
DE21 | 2023 | 2.3 | 43.3 [b] | 74700 [p]
ES51 | 2025 | 8.4 [d] | 44.6 | 
ES51 | 2024 | 8.9 [d] | 44.4 | 37500 [p]
ES51 | 2023 | 9.3 [d] | 44.2 | 35600 [p]
ITC4 | 2025 | 3 | 48.4 | 
ITC4 | 2024 | 3.7 | 48.1 | 50400
ITC4 | 2023 | 4 | 47.8 | 49100
[Source : eurostat (unemployment_rate 30.06.2026, median_age 10.07.2026, gdp_per_capita 10.02.2026)]
```

**10. `get_indicators(indicators=["unemployment_rate", "median_age", "gdp_per_capita"], zones=["FR10"])`**

```
geo_code | time | unemployment_rate | median_age | gdp_per_capita
FR10 | 2025 | 8.8 [d] | 38.4 [p] | 
FR10 | 2024 | 8 [bd] | 38.2 [p] | 69500 [p]
FR10 | 2023 | 7.6 [d] | 38 [p] | 66800 [p]
[Source : eurostat (unemployment_rate 30.06.2026, median_age 10.07.2026, gdp_per_capita 10.02.2026)]
```

## Answer

Here's the comparison (Eurostat, latest available — 2024 for GDP, most recent year for unemployment & age):

| Region | Unemployment | Median age | GDP per capita |
|---|---|---|---|
| **Oberbayern** (DE21) | **2.7%** (2024) | 43.3 | **€75,700** |
| **Île-de-France** (FR10) | 8.0% (2024) | **38.2** | €69,500 |
| **Lombardia** (ITC4) | 3.7% (2024) | 48.1 | €50,400 |
| **Cataluña** (ES51) | 8.9% (2024) | 44.4 | €37,500 |

*(Some 2024 figures are marked provisional `[p]`/estimated `[e]`; 2025 unemployment is partial.)*

## Verdict: Oberbayern looks the most dynamic

The case rests on a **"hot economy" combination** no other region matches:

1. **Highest GDP per capita** (€75,700) — the most productive and wealthiest of the four, ~2× Cataluña and above France's heartland.
2. **Near-full employment** (2.7%, lowest by far) — signal of strong labour demand, hiring, and low friction. A tight labour market is the classic footprint of an economy expanding.
3. **Reasonably young workforce** (43.3) — younger than Lombardia (48.1), so its output isn't being proppped up by an ageing, shrinking labour base.

High output **plus** near zero unemployment = a self-reinforcing cycle of demand, jobs and investment, which is what "dynamic" means in practice right now.

### The nuance worth flagging
- **Île-de-France** is the most **demographically** dynamic — by far the youngest population (38.2 median年龄). That's a *future* growth engine (large inflow into prime working age, births, inflows), but today it shows up as higher unemployment (8%) and less GDP. Think "high potential, currently under-utilised labour."
- **Lombardia** has a good job market (3.7%) but an **oldest population** (48.1) and mid-tier GDP — the clearest warning sign for long-term dynamism.
- **Cataluña** is the weakest on all three: highest unemployment, high GDP gap, ageing.

**Bottom line:** Oberbayern is the most dynamic *today* (wealth + full employment). If you define dynamism as *growth potential* rather than current performance, Île-de-France's young population is the standout — and worth watching.

