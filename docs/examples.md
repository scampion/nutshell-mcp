# Example prompts — what nutshell-mcp is for

[🇫🇷 Français](examples.fr.md) · 🇬🇧 English · [← README](../README.md)

Each example is a prompt you can paste into any MCP client connected to the
server (`https://nutshell.arcamens.ai/mcp`, or your own instance). The model never
writes an SDMX URL, an Overpass query or a CDS request: it picks a tool, the
server validates and answers from local data.

> Tool outputs are in French (project convention). The model answers in the
> language of your prompt.

| # | Example | Tools chained | Shows |
|---|---|---|---|
| 1 | [Where to open a geriatric clinic?](#1-where-to-open-a-geriatric-clinic) | unified layer + native grain | crossing Eurostat and OSM, quality flags |
| 2 | [Compare four regions](#2-compare-four-regions) | 3 unified tools | one table, one column per indicator |
| 3 | [When the registry stops at NUTS2](#3-when-the-registry-stops-at-nuts2) | unified layer → native grain | falling back to NUTS3, actionable errors |
| 4 | [Tourism, beyond the registry](#4-tourism-beyond-the-registry) | native Eurostat grain | the 10,301-dataset catalogue |
| 5 | [A new indicator in one YAML file](#5-a-new-indicator-in-one-yaml-file) | native grain → registry | the model drafts the YAML |
| 6 | [Heatwaves and the elderly](#6-heatwaves-and-the-elderly) | unified layer, 3 batches | climate × ageing × hospitals (3 sources) |
| 7 | [Moving with a young family](#7-moving-with-a-young-family) | one `get_indicators` call | 5 indicators from 3 sources |
| 8 | [Summer tourism, heat and rail](#8-summer-tourism-heat-and-rail) | native grain + unified layer | monthly series × heat × rail (3 sources) |
| 9 | [Schools and children](#9-schools-and-children) | registry → native grain | a denominator found in the catalogue |
| 10 | [East–West convergence](#10-eastwest-convergence) | one `get_indicators` call, 11 years | time series, breaks and provisional values |

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

**What a real run produced** (condensed excerpt — [full answer](results/01-geriatric-clinic.md)):

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
The final recommendation is hedged accordingly — which is the point: a model
that can see the quality flags behaves like an analyst, not like a search box.

**What the model got wrong.** It warned that the French data was on the
"pre-2016 regional geography" (Poitou-Charentes rather than Nouvelle-Aquitaine)
and told the user to rerun on NUTS 2021. That is a misreading: in NUTS 2021 and
2024, the current French regions are the NUTS1 level (`FRI` Nouvelle-Aquitaine)
while NUTS2 keeps the former regions (`FRI3` Poitou-Charentes). The data was
current; the NUTS2 level simply does not match today's administrative regions.

---

## 2. Compare four regions

The shortest useful prompt — one question, three tool calls.

```
Compare unemployment, median age and GDP per capita for Île-de-France,
Oberbayern, Lombardia and Cataluña. Which one looks the most
dynamic, and why?
```

**Real run** with Qwen3.8-27B — [full transcript](results/02-compare-regions.md).
The model ran 3 `search_indicators` and 4 `list_zones` in parallel, retried
`list_zones` once (`contains="Île-de-France"` finds nothing: the GISCO name is
`Ile-de-France`, without the accent), then 2 `get_indicators` calls:

```
geo_code | time | unemployment_rate | median_age | gdp_per_capita
DE21 | 2025 | 3 | 43.3 |
DE21 | 2024 | 2.7 | 43.3 | 75700 [e]
DE21 | 2023 | 2.3 | 43.3 [b] | 74700 [p]
ES51 | 2025 | 8.4 [d] | 44.6 |
ES51 | 2024 | 8.9 [d] | 44.4 | 37500 [p]
…
[Source : eurostat (unemployment_rate 30.06.2026, median_age 10.07.2026, gdp_per_capita 10.02.2026)]
```

Answer (excerpt):

| Region | Unemployment | Median age | GDP per capita |
|---|---|---|---|
| **Oberbayern** (DE21) | **2.7%** (2024) | 43.3 | **€75,700** |
| **Île-de-France** (FR10) | 8.0% (2024) | **38.2** | €69,500 |
| **Lombardia** (ITC4) | 3.7% (2024) | 48.1 | €50,400 |
| **Cataluña** (ES51) | 8.9% (2024) | 44.4 | €37,500 |

> **Oberbayern is the most dynamic *today* (wealth + full employment).** If you
> define dynamism as *growth potential* rather than current performance,
> Île-de-France's young population is the standout.

Without a time filter the server returns the last 3 periods, so the model sees
the trend for free. One thing to watch with a 27B model: in its reasoning it
misread the `[d]` flag as "not available" instead of *definition differs* —
asking explicitly about reliability (example 1) makes the model check.

---

## 3. When the registry stops at NUTS2

```
Give me the gdp_capita of FR10 for the last 3 years, then the GDP per capita
of the NUTS3 zone FR101.
```

**Real run** with Qwen3.8-27B — [full transcript](results/03-nuts3-fallback.md).
The model never sent the typo: it called `search_indicators("GDP per capita")`
first and used the right id, `gdp_per_capita`. The registry only goes down to
NUTS2, so it got FR10 from `get_indicators`, then went down to the native grain
for Paris:

```
search_datasets("GDP NUTS")          → nama_10r_3gdp | Gross domestic product (GDP) at current market prices by NUTS 3 region
get_structure("nama_10r_3gdp")       → unit: EUR_HAB (Euro per inhabitant), …
query_data("nama_10r_3gdp", {"geo": "FR101", "unit": "EUR_HAB"}, 2022–2024)

freq | unit | geo | time | value | flag
A | EUR_HAB | FR101 | 2022 | 123100.0 | p
A | EUR_HAB | FR101 | 2023 | 125300.0 | p
A | EUR_HAB | FR101 | 2024 | 133700.0 | p
[Source : miroir local, données Eurostat du 10.02.2026]
```

Answer: FR10 €63,200 → €66,800 → €69,500, FR101 €123,100 → €125,300 →
€133,700 (2022–2024, all provisional).

**Actionable errors.** Had the model sent the typo or asked the registry for
NUTS3, the server would have answered with the fix (real server outputs):

```
get_indicators(["gdp_capita"], ["FR10"])
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

get_indicators(["gdp_per_capita"], ["FR101"])
'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).
```

Every error names the corrective action and offers at most 3 suggestions
(`difflib`): this is what lets a 27B model follow tool chains without a human.

> *This run exposed a weakness since fixed:* four `search_datasets` calls
> ("gross domestic product regions", "GDP regions"…) returned nothing because
> catalogue search required every word verbatim. It now matches plurals, and
> falls back to "at least one word" when no title has them all, and says so.

---

## 4. Tourism, beyond the registry

The registry holds a curated set of indicators; the native grain exposes all of
Eurostat.

```
Find in Eurostat a dataset on nights spent at tourist accommodation by region.
Which five NUTS2 regions of Spain and Italy had the most nights in the latest
year available? Tell me which filters you used.
```

**Real run** with Qwen3.8-27B — [full transcript](results/04-tourism.md). The
model searched the catalogue, compared `tour_occ_nin2` and `tour_occ_nin2dc`
with `get_structure`, listed the Spanish and Italian codes with `list_codes`,
then ran one `query_data` over the 40 regions:

| Rank | Region | Code | Year | Nights |
|---|---|---|---|---|
| 1 | Canarias | ES70 | 2024 | 99,488,821 |
| 2 | Cataluña | ES51 | 2024 | 88,670,191 |
| 3 | Andalucía | ES61 | 2024 | 77,308,673 |
| 4 | Veneto | ITH3 | 2025 | 74,157,131 |
| 5 | Illes Balears | ES53 | 2024 | 73,845,222 |

It stated its filters (`unit=NR`, `c_resid=TOTAL`, `nace_r2=I551-I553`,
`freq=A`) and flagged, unprompted, that Spain's latest year is 2024 and Italy's
2025 — then checked that a same-year comparison gives the same top 5. Every
figure matches the mirror.

> *A first run found a server weakness, since fixed* —
> [transcript](results/04-tourism-before-fix.md). `list_codes(contains="ES")`
> also matched labels ("Bruxell**es**", "H**es**sen"…), which filled 36 of the
> 60 lines shown; ES63, ES64 and ES70 fell past the cut. The model ignored the
> `… et 53 autres, affinez 'contains'` hint for Spain, missed Canarias and got
> the wrong #1. Codes starting with the filter now come first, higher levels
> first.

---

## 5. A new indicator in one YAML file

Adding an indicator to the registry needs no code — see
[Adding an indicator](../README.md#adding-an-indicator--one-yaml-file). The model
can even write the YAML for you:

```
I run a nutshell-mcp server and want to add a new indicator: hospital beds per
100,000 inhabitants at NUTS2 level. Find the right Eurostat dataset and the
filter codes, then write the registry YAML file using this schema: id, label,
unit, source: eurostat, frequency: A, geo_levels, extraction: {dataset,
filters, value_dim: geo}. Check that the codes you use really exist.
```

**Real run** with Qwen3.8-27B — [full transcript](results/05-new-indicator-yaml.md).
The model compared three candidate datasets with `get_structure`, checked each
code with `list_codes`, ran a test `query_data`, and wrote:

```yaml
id: hospital_beds_per_100k
label: "Lits d'hôpital disponibles pour 100 000 habitants"
unit: P_HTHAB
source: eurostat
frequency: A
geo_levels:
  - NUTS2
extraction:
  dataset: hlth_rs_bdsrg
  filters:
    freq: A
    unit: P_HTHAB
    facility: HBEDT
  value_dim: geo
```

This file passes `python -m nutshell_mcp.registry validate` as is. The model
also flagged, unprompted, that the dataset mixes NUTS generations (`DE1`,
`ITC4`) and stops around 2020.

**What a human still has to check.** That caveat is the clue: `hlth_rs_bdsrg`
is titled *"Hospital beds by NUTS 2 region - historical data (1993-2016)"*. The
current series is `hlth_rs_bdsrg2` (*Available beds in hospitals by NUTS 2
region*, 1993–2025). Swap the dataset, then:

```bash
.venv/bin/python -m nutshell_mcp.registry validate
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators hospital_beds_per_100k
```

The server reloads the registry on the fly: the indicator appears in
`search_indicators` without a restart, and example 1 can then use it through
`get_indicators` instead of the native grain. (The model also suggested saving
the file under `indicators/`; the registry directory is `registry/`.)

---

## Crossing the three sources

The examples above mostly combine two sources. The questions below need all
three views of a territory at once: **socio-economic** (who lives there —
Eurostat), **geographic** (what the environment is like — Copernicus) and
**infrastructure** (what is available — OpenStreetMap).

## 6. Heatwaves and the elderly

```
Heatwaves hit the elderly hardest. Among the NUTS3 regions of Spain and Italy,
which ones combine the hottest summers, the oldest population and the fewest
hospitals per 100,000 inhabitants? Give me a ranked top 10 with the figures,
and explain how much each data source can be trusted.
```

**Real run** with Qwen3.8-27B — [full transcript](results/06-heat-ageing.md).
The model found the four indicators (`lst_summer_mean`, `old_age_dependency`,
`population`, `hospitals_count`), listed the 159 NUTS3 regions with
`list_zones`, then wrote a small script through the harness's `mcpScript`
helper that called `get_indicators` in three batches (the 100-zone limit per
call) and ranked the regions by percentile:

| # | Region | Summer temp. (°C) | 65+ / 15–64 (%) | Hospitals (OSM) | Per 100,000 |
|---|---|---|---|---|---|
| 1 | Asti (ITC17) | 25.1 | 45.2 | 2 | 0.97 |
| 2 | Lecce (ITF45) | 27.8 | 42.6 | 18 | 2.35 |
| 3 | Terni (ITI22) | 24.8 | 48.0 | 4 | 1.86 |
| 4 | Cagliari (ITG2G) | 25.9 | 49.5 | 4 | 2.70 |
| 5 | Trapani (ITG11) | 27.7 | 39.8 | 8 | 1.94 |
| … | | | | | |
| 10 | Salamanca (ES415) | 23.3 | 46.3 | 6 | 1.83 |

Its reliability section ranks the sources the way an analyst would: Eurostat
"high trust", temperature "moderate", OSM hospital counts "lowest trust, the
weakest link" — uneven mapping, and a per-100,000 ratio that swings on a single
missing hospital when counts are small. It concludes: *treat ranks 1–10 as a
directional shortlist, not a precise ordering.*

**What we checked.** Dependency ratios, hospital counts and populations match
the mirror exactly. The temperatures do not: the model labelled them "2024" but
its script read the third row of each zone, which is **2023** (Asti 25.1 °C in
2023, 23.8 °C in 2024). The ranking is therefore a 2023 heat ranking. The model
also describes the temperature as satellite land-surface temperature; it is
ERA5-Land reanalysis skin temperature, flagged `[sampled]` on this demo server
(estimate from the keyless ARCO provider).

## 7. Moving with a young family

```
My family with two young children wants to move to Germany or Austria. Compare
their NUTS2 regions: we want mild summers, low unemployment, and as many
schools and train stations as possible relative to population. Suggest the 5
best regions with a table of figures, and tell me what the data cannot tell us.
```

**Real run** with Qwen3.8-27B — [full transcript](results/07-family-relocation.md).
Four `search_indicators`, two `list_zones`, then **a single `get_indicators`
call** with 5 indicators from 3 sources over 45 regions — exactly the limits
of one call:

```
get_indicators(["lst_summer_mean", "unemployment_rate", "schools_count",
                "train_stations_count", "population"], [DE11 … AT34])
```

| # | Region | Summer (°C) | Unemployment | Schools / 1,000 inh. | Stations / 1,000 inh. |
|---|---|---|---|---|---|
| 1 | Oberösterreich (AT31) | 19.7 | 3.8 % | 0.640 | 0.091 |
| 2 | Steiermark (AT22) | 18.4 | 4.4 % | 0.608 | 0.095 |
| 3 | Lüneburg (DE93) | 18.7 | 2.7 % | 0.488 | 0.078 |
| 4 | Oberfranken (DE24) | 18.4 | 2.7 % | 0.521 | 0.059 |
| 5 | Tübingen (DE14) | 18.4 | 2.8 % | 0.531 | 0.056 |

All figures in the table match the mirror. The model made "mild" explicit
(17.5–20 °C), offered the other reading (*cool* summers put Tirol first) and
listed what the data cannot say: daycare places, cost of housing, train
frequency rather than station counts, heatwave frequency rather than a summer
mean, and the per-capita bias that favours small, sparsely populated regions.

---

## More questions

## 8. Summer tourism, heat and rail

```
Summer tourism meets climate change. Among the NUTS2 regions of Spain, Italy,
Greece and Croatia, which ones receive the most tourist nights, have the
hottest summers, and how well are they served by rail relative to population?
Give a top 8 with the figures, and say which conclusions the data does and
does not support.
```

**Real run** with Qwen3.8-27B — [full transcript](results/08-tourism-heat-rail.md).
Tourist nights are not in the registry: the model went to the native grain and
chose the **monthly** series (`tour_occ_nin2m`) to sum June–August only, then
crossed it with summer temperature (Copernicus) and stations per inhabitant
(OSM + Eurostat) over 56 regions:

| # | Region | Summer 2024 nights | Summer temp. 2024 | Stations / 100k inh. |
|---|---|---|---|---|
| 1 | Jadranska Hrvatska (HR03) | 63.0 M | 23.6 °C | 3.8 |
| 2 | Cataluña (ES51) | 40.3 M | 23.9 °C | 5.3 |
| 3 | Illes Balears (ES53) | 37.7 M | 26.9 °C | 2.9 |
| 4 | Veneto (ITH3) | 37.0 M | 22.0 °C | 2.4 |
| 5 | Andalucía (ES61) | 27.6 M | 27.7 °C | 2.4 |
| 6 | Canarias (ES70) | 25.6 M | *no data* | 0 |
| 7 | Notio Aigaio (EL42) | 24.3 M | 25.4 °C | 0 |
| 8 | Emilia-Romagna (ITH5) | 23.0 M | 23.7 °C | 4.8 |

Every figure in the table matches the mirror. The findings are the kind a
planner would want: the hottest regions (Attica, Melilla, Puglia) are *not* the
biggest night-receivers; volume and intensity pick different winners (Croatia's
coast by volume, the Greek islands per inhabitant); the busiest summer
destinations are among the *least* rail-served; and annual figures overstate
Alpine "summer" tourism, which the monthly series corrects. It kept the Canaries
in the ranking with their temperature marked missing (outside the Copernicus
extent on this demo). One slip: it calls Cataluña, Veneto and Emilia-Romagna
"land-locked hubs".

> *How the server shaped this run.* The [first run](results/08-tourism-heat-rail-run1.md)
> spent ten calls looking for Greece under `GR` (its NUTS code is `EL`), read
> 2023 temperatures as 2024 and invented a ~24 °C summer for the Canaries. A
> [second run](results/08-tourism-heat-rail-run2.md), after the `GR → EL` hint,
> found Greece in one call but dropped the tourism part: `search_indicators`
> said the registry had nothing and did not mention the catalogue. The server now
> points to `search_datasets` in that case — this third run followed it.

## 9. Schools and children

```
Where in France and Germany are schools scarcest relative to the number of
children? Compare NUTS2 regions using the population aged under 15 and the
number of schools. Give the 5 regions with the fewest schools per 1,000
children and the 5 with the most, and explain the limits of this comparison.
```

**Real run** with Qwen3.8-27B — [full transcript](results/09-schools-children.md).
The registry has no "children" indicator, so the model searched the catalogue,
opened several structures and settled on `demo_r_pjangroup` (population by
5-year age group, NUTS2). It summed the 0–4, 5–9 and 10–14 bands with
`query_data` and crossed them with `schools_count` (OSM):

| | Region | Under 15 | Schools | Per 1,000 children |
|---|---|---|---|---|
| fewest | Berlin (DE30) | 511,418 | 1,077 | 2.11 |
| | Hamburg (DE60) | 265,637 | 561 | 2.11 |
| | Darmstadt (DE71) | 580,000 | 1,391 | 2.40 |
| most | Bourgogne (FRC1) | 244,642 | 2,434 | 9.95 |
| | Limousin (FRI2) | 101,386 | 934 | 9.21 |
| | Franche-Comté (FRC2) | 193,006 | 1,647 | 8.53 |

Every figure matches the mirror. The interesting part is the model's own
reading: the gap is mostly **structural, not a shortage** — France keeps a
small primary school in almost every rural commune while German cities run
fewer, larger schools. It also flagged that OSM tags every school type the same
way, and that 0–5 year-olds are in the denominator but not in schools.

## 10. East–West convergence

```
How have Poland, Romania, Czechia and Hungary converged with the rest of the
EU since 2014? For their capital regions and one other NUTS2 region per country
of your choice, show GDP per capita and unemployment over 2014-2024 and
summarise the trend. Point out breaks in series and provisional values.
```

**Real run** with Qwen3.8-27B — [full transcript](results/10-east-west-convergence.md).
One `get_indicators` call returned 11 years × 8 regions × 2 indicators, with
their flags. To build an EU reference, the model then queried the 27 member
states and averaged them:

| Region | GDP / inh. 2014 | 2024 | % of EU27 mean, 2014 → 2024 |
|---|---|---|---|
| Praha (CZ01) | €33,200 | €62,400 | 127 % → 150 % |
| Budapest (HU11) | €22,700 | €47,600 [p] | 87 % → 115 % |
| Warszawa (PL91) | €23,000 | €45,300 [p] | 88 % → 109 % |
| București-Ilfov (RO32) | €17,300 | €45,200 [p] | 66 % → 109 % |
| Sud-Muntenia (RO31) | €6,400 | €13,200 [p] | 24 % → 32 % |

Its conclusion: capitals have caught up with — or overtaken — the EU average,
while the rest of each country lags far behind (Budapest 115 % vs Pest 44 %).
Unemployment fell everywhere, except in Sud-Muntenia, back up to 7.3 %.

**What we checked.** Regional series and the 2014 and 2024 EU means (€26,141 and
€41,548) match the mirror; the 2020 mean is wrong in the answer (~€27,000
instead of €31,233). The model says itself that an unweighted mean of 27
countries, skewed by Ireland and Luxembourg, is only indicative. Its list of
series breaks is partly wrong (it flags Warsaw GDP for 2021, which is not).

> *The first run* ([transcript](results/10-east-west-convergence-before-fix.md))
> asked for zone `EU27`, got "unknown zone" and dropped the EU comparison — and
> placed Debrecen in HU31 and Cluj in RO12, both wrong. The server now explains
> that `EU27` is an aggregate and points to the native datasets (`geo=EU27_2020`).

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
