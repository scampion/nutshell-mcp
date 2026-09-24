# Example prompts — what nutshell-mcp is for

[🇫🇷 Français](examples.fr.md) · 🇬🇧 English · [← README](../README.md)

Each example is a prompt you can paste into any MCP client connected to the
server (`https://nutshell.scamp.fr/mcp`, or your own instance). The model never
writes an SDMX URL, an Overpass query or a CDS request: it picks a tool, the
server validates and answers from local data.

> Tool outputs are in French (project convention). The model answers in the
> language of your prompt.

| # | Example | Tools chained | Shows |
|---|---|---|---|
| 1 | [Where to open a geriatric clinic?](#1-where-to-open-a-geriatric-clinic) | unified layer + native grain | crossing Eurostat and OSM, quality flags |
| 2 | [Compare four regions](#2-compare-four-regions) | 3 unified tools | one table, one column per indicator |
| 3 | [A typo the server fixes](#3-a-typo-the-server-fixes) | `get_indicators` | actionable errors |
| 4 | [Tourism, beyond the registry](#4-tourism-beyond-the-registry) | native Eurostat grain | the 10,301-dataset catalogue |
| 5 | [A new indicator in one YAML file](#5-a-new-indicator-in-one-yaml-file) | registry + `sync` | extending the server without code |

---

## 1. Where to open a geriatric clinic?

The flagship demo: a decision question that no single source answers.

```
I need to choose the European region where to open a geriatric clinic.
Compare the NUTS2 regions of France, Belgium and Luxembourg: I want the ones
with the oldest population, the weakest hospital supply relative to
population, and a decent GDP per capita. Give me a justified top 5, with a
table of figures, and state how reliable each source is.
```

**What happens.** The model discovers indicators with `search_indicators`,
lists the zones of each country with `list_zones`, then calls `get_indicators`
in several batches (limit: 5 indicators and 100 zones per call). Unsatisfied by
the OSM hospital *count* (it counts sites, not beds), it goes down to the native
grain — `search_datasets` → `get_structure` → `list_codes` → `query_data` — to
find real hospital *beds* by region.

**What a real run produced** (condensed excerpt of the model's answer):

| # | Region (NUTS2) | Dependency 65+ | Beds / 100k inh. | GDP / inh. |
|---|---|---|---|---|
| 1 | Brabant wallon (BE31) | 33.4 % | 225.3 | €69,500 |
| 2 | Poitou-Charentes (FRI3) | 47.3 % | 492.9 | €34,900 |
| 3 | Vlaams-Brabant (BE24) | 32.5 % | 377.4 | €57,100 |
| 4 | Basse-Normandie (FRD1) | 44.3 % | 557.2 | €34,600 |
| 5 | Corse (FRM0) | 43.2 % | 552.0 | €37,500 |

The ranking is a composite z-score computed by the model (weights: 40 % age,
40 % supply, 20 % GDP), over 39 zones.

**Why it convinces.** The interesting part is not the table but what the
provenance layer let the model say about it:

- Belgian bed counts all carry the flag `d` (*definition differs*), so the model
  warned that the FR/BE comparison is *indicative, not a measurement* — and that
  ranks 1 and 3 are Belgian.
- OSM returned 0 hospitals for the five French overseas departments; the model
  spotted the completeness defect (`osm_completeness_unknown`) and excluded them.
- Luxembourg returned no bed data; the model reported *a data hole, not a bad
  score* and ranked it on demography alone.
- Values marked `[p]` (provisional) were called out as such for 2025.
- It noticed that the French data was on the pre-2016 regional geography
  (Poitou-Charentes rather than Nouvelle-Aquitaine) and told the user to rerun
  on NUTS 2021 before any decision.

The final recommendation is hedged accordingly — which is the point: a model
that can see the quality flags behaves like an analyst, not like a search box.

---

## 2. Compare four regions

The shortest useful prompt — one question, three tool calls.

```
Compare unemployment, median age and GDP per capita for Île-de-France,
Oberbayern, Lombardia and Cataluña. Which one looks the most
dynamic, and why?
```

**Expected chain.**

```
search_indicators("unemployment median age GDP")
list_zones("NUTS2", contains="Oberbayern")        # ×4, to get FR10, DE21, ITC4, ES51
get_indicators(["unemployment_rate", "median_age", "gdp_per_capita"],
               ["FR10", "DE21", "ITC4", "ES51"])
```

The answer is one pivoted table, one column per indicator, with a provenance
line (`[Source : eurostat (date)]`). Without a time filter the server returns the
last 3 periods, so the model sees the trend for free.

---

## 3. A typo the server fixes

```
Give me the gdp_capita of FR10 for the last 3 years.
```

`gdp_capita` does not exist. Instead of failing, the server answers:

```
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.
```

and the model retries by itself. Every error names the corrective action and
offers at most 3 suggestions (`difflib`) — this is what lets a 27B local model
follow tool chains without a human.

Same idea for granularity:

```
Give me the GDP per capita of the NUTS3 zone FR101.
```

```
'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux
disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).
```

---

## 4. Tourism, beyond the registry

The registry holds a curated set of indicators; the native grain exposes all of
Eurostat.

```
Find in Eurostat a dataset on nights spent at tourist accommodation by region.
Which five NUTS2 regions of Spain and Italy had the most nights in the latest
year available? Tell me which filters you used.
```

**Expected chain.** `search_datasets("nights spent tourist accommodation")` →
`get_structure("tour_occ_nin2")` (dimensions, sizes, time range) →
`list_codes("tour_occ_nin2", "nace_r2")` and `list_codes("tour_occ_nin2", "unit")` to pick valid codes →
`query_data(...)` with filters. Each step's description names the next tool, so
the model does not need to know the dataset in advance. `query_data` is capped
at 400 rows and says how to narrow the query when it truncates.

---

## 5. A new indicator in one YAML file

For the person running the server, not the model. Adding an indicator needs no
code — see [Adding an indicator](../README.md#adding-an-indicator--one-yaml-file):

```yaml
# registry/my_indicator.yaml — same pattern for any Eurostat dataset
id: my_indicator
label: "…"
unit: …
source: eurostat
frequency: A
geo_levels: [NUTS2]
extraction:
  dataset: <dataset code found with search_datasets>
  filters: { … }
  value_dim: geo
```

```bash
.venv/bin/python -m nutshell_mcp.registry validate
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators my_indicator
```

The server reloads the registry on the fly: the indicator appears in
`search_indicators` without a restart, and example 1 can then use it.

---

## Tips for demos

- **Ask for provenance.** "State how reliable each source is" is what triggers
  the quality-flag reasoning that makes example 1 stand out.
- **Force a medium/low reasoning level** on small local models: the default
  `xhigh` over-thinks simple tool chains.
- **Watch the limits.** 5 indicators and 100 zones per `get_indicators` call:
  a good model batches on its own; a weaker one will follow the truncation
  message.
- **`SNAPSHOT` indicators** (OSM counts such as `hospitals_count`) describe the
  current state and are repeated on every period row of the zone, tagged
  `[snapshot YYYY-MM]` — don't read them as a time series.
