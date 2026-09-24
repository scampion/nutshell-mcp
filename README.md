<p align="center"><img src="assets/logo.png" alt="nutshell-mcp" width="200"></p>

# nutshell-mcp — *Europe in a nutshell*

[🇫🇷 Français](README.fr.md) · 🇬🇧 English

MCP server for European territorial data — Eurostat, Copernicus and
OpenStreetMap brought to a single grain, **zone × indicator × period**, and
served entirely offline.

Designed for a mid-size local model (reference: Qwen3.8-27B): 7 tools, narrow
schemas, server-side validation, bounded and self-describing outputs. The model
never builds a source query — no SDMX URL, no Overpass QL, no CDS request.

## See it in action

Ask a question that no single source answers:

> *Compare the NUTS2 regions of France, Belgium and Luxembourg: oldest
> population, weakest hospital supply, decent GDP per capita. Give me a
> justified top 5 and state how reliable each source is.*

The model chains `search_indicators` → `list_zones` → `get_indicators` (and drops
to the native Eurostat grain when it needs more), then reasons on the quality
flags: provisional values, differing definitions, incomplete OSM coverage, data
holes. Other real runs cross all three sources — heatwaves × ageing × hospitals, or climate × jobs × schools and
rail for a family move. **[Example prompts and full transcripts → `docs/examples.md`](docs/examples.md)**

Reference document: `architecture-spec-mcp-territorial.md`.
Deviations and implementation choices: `DECISIONS.md`.

> Tool outputs and error messages are in French (project convention); the
> examples below are shown as the server returns them.

## Quick start: use the hosted server

No install needed: a public demo server runs at `https://nutshell.scamp.fr/mcp`
(streamable HTTP, no key; best-effort availability).

**Claude Code plugin (marketplace)**

```
/plugin marketplace add scampion/nutshell-mcp
/plugin install nutshell@nutshell
```

**Claude Code, without the plugin**

```bash
claude mcp add --transport http nutshell https://nutshell.scamp.fr/mcp
```

**Any other MCP client** (Claude Desktop custom connector, Cursor, …): add a
remote server with the URL above.

To run your own copy (offline, private), see [Installation](#installation).

## Architecture

```
   INGESTION (online, scheduled)            python -m nutshell_mcp.sync
   ┌───────────────────────────────────────────────────────────────────┐
   │ GISCO      → geo.py          NUTS/city geometries + geo table     │
   │ Eurostat   → mirror.py       bulk TSV.gz → native Parquet         │
   │              project_eurostat.py  → projection to canonical grain │
   │ OpenStreetMap → ingest_osm.py     Geofabrik extracts → POIs       │
   │ Copernicus    → ingest_cds.py     rasters → zonal statistics      │
   └───────────────────────────────┬───────────────────────────────────┘
                                   ▼
   STORAGE (local, rsync-able)
   ┌───────────────────────────────────────────────────────────────────┐
   │ mirror/eurostat/{dataset}.parquet          native grain           │
   │ mirror/indicators/indicator={id}/…         canonical grain        │
   │ mirror/geo/*.geojson                       GISCO geometries       │
   │ eurostat.db                FTS5 catalogue, DSD, registry, sync    │
   │ registry/*.yaml            indicator definitions (versioned)      │
   └───────────────────────────────┬───────────────────────────────────┘
                                   ▼
   SERVING (offline)                        python -m nutshell_mcp.server
   ┌───────────────────────────────────────────────────────────────────┐
   │ unified layer : search_indicators, list_zones, get_indicators     │
   │ native grain  : search_datasets, get_structure, list_codes,       │
   │                 query_data                                        │
   └───────────────────────────────────────────────────────────────────┘
```

Ingestion and serving are decoupled: the server only reads from disk. An outage
of the source APIs never affects a conversation in progress.

## Installation

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"

.venv/bin/python -m nutshell_mcp.server                      # stdio
MCP_TRANSPORT=http .venv/bin/python -m nutshell_mcp.server   # streamable HTTP
```

Optional extras, needed only by the matching ingestion pipelines:
`.[osm]`, `.[copernicus]`. The server starts without them.

MCP client config (stdio):

```json
{
  "mcpServers": {
    "nutshell": {
      "command": "python",
      "args": ["-m", "nutshell_mcp.server"],
      "cwd": "/path/to/nutshell-mcp",
      "env": { "NUTSHELL_OFFLINE": "1" }
    }
  }
}
```

## The 7 tools

### Unified layer — crossing sources

| tool | purpose | output |
|---|---|---|
| `search_indicators(query, source="", limit=10)` | find an indicator in the registry | `id \| label \| unit \| freq \| geo levels \| source` |
| `list_zones(level, parent="", contains="")` | browse the geographic reference | `geo_code \| name \| level \| parent` |
| `get_indicators(indicators, zones, time_from="", time_to="")` | values, **one column per indicator** | pivoted table + provenance line |

### Native Eurostat grain — all dimensions

`search_datasets` → `get_structure` → `list_codes` → `query_data`, over the
10,301 datasets of the catalogue, including those no indicator projects.

### Typical agent sequence

```
1. search_indicators("chômage PIB population")
     → gdp_per_capita, unemployment_rate, population, median_age…
2. list_zones("NUTS2", parent="FR")
     → FR10 Ile-de-France, FRK2 Rhône-Alpes, FRE1 Nord-Pas de Calais…
3. get_indicators(["gdp_per_capita", "unemployment_rate", "median_age"],
                  ["FR10", "FRK2", "FRJ1", "FRE1"])
```

```
geo_code | time | gdp_per_capita | unemployment_rate | median_age
FR10     | 2025 |                | 8.8 [d]           | 38.4 [p]
FR10     | 2024 | 69500 [p]      | 8 [bd]            | 38.2 [p]
FRK2     | 2024 | 43400 [p]      | 6.8 [bd]          | 41.4 [p]
[Source : eurostat (30.06.2026)]
```

Guardrails: at most 5 indicators and 100 zones per call; without a time
filter, the last 3 periods; at most 400 rows, and any truncation states the
corrective action. Brackets after a value carry the quality flag (`p`
provisional, `d` different definition, `recoded`, `osm_completeness_unknown`…).
`SNAPSHOT` indicators (OSM counts dated to the extract month) describe the
current state: their latest value is repeated on every period row of the zone,
tagged `[snapshot 2026-08]`, outside the time window, with a reminder line
giving the date and quality (ADR-L1-15).

Every error is actionable:

```
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux
disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).

Indicateur 'lst_summer_mean' non matérialisé et mode offline actif.
Lancer : python -m nutshell_mcp.sync --source copernicus --indicators lst_summer_mean
```

Note for Qwen3.8-27B: force a medium/low reasoning level (the default `xhigh`
over-thinks simple tool chains).

## Synchronization

```bash
# Geographic reference (monthly) — 18 GISCO files, ~173 MB
.venv/bin/python -m nutshell_mcp.sync --source geo

# Eurostat indicators from the registry (daily) — TOC-driven, idempotent
.venv/bin/python -m nutshell_mcp.sync --source eurostat

# A single indicator
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators gdp_per_capita

# Everything, ignoring freshness signals
.venv/bin/python -m nutshell_mcp.sync --source all --full
```

Idempotent, designed for cron. Each source publishes a freshness signal
(`last update of data` from the Eurostat TOC, GISCO ETag) compared with the
local state in `eurostat.db`: nothing is re-downloaded without reason, and
there is no TTL. A failure on one indicator does not interrupt the batch; the
final report lists updated / unchanged / failed.

The native mirror can also be driven on its own:

```bash
.venv/bin/python -m nutshell_mcp.mirror --datasets nama_10_gdp,une_rt_m
.venv/bin/python -m nutshell_mcp.mirror --resync        # TOC-driven
.venv/bin/python -m nutshell_mcp.mirror --project-only  # re-project, zero network
.venv/bin/python -m nutshell_mcp.mirror --all           # ~24 GB compressed!
```

## OSM pipeline

```bash
.venv/bin/python -m nutshell_mcp.sync --source osm             # configured extracts
NUTSHELL_OSM_EXTRACTS=europe/luxembourg,europe/belgium \
  .venv/bin/python -m nutshell_mcp.sync --source osm --full    # full re-materialisation
```

Scope: a comma-separated list of Geofabrik country extracts
(`continent/country`) in `NUTSHELL_OSM_EXTRACTS`, or the keywords `europe`
(every country of the NUTS reference, ~30 GB downloaded in total, country by
country, peak disk ≈ 4.5 GB) and `eu27`, which can be combined with explicit
extracts. The default is deliberately restricted to `europe/luxembourg` alone —
never a continental extract or all of Europe by default (30 GB). Recommended
cadence: monthly (§7.4), as Geofabrik republishes its extracts at about that
rate.

Sequence per synchronisation: streaming `httpx` download of each `.osm.pbf`
extract, verified against its `.md5` sidecar (the sidecar, a few bytes, is
compared with the local state *before* any `.pbf` download, to avoid
re-downloading an unchanged extract); the definitive freshness signal comes once
the file is obtained: `osmium fileinfo -e -g header.option.timestamp` (the
timestamp embedded in the file, more reliable than the CDN-dependent HTTP
`Last-Modified`); a single `osmium tags-filter` pass combining the tags of all
OSM indicators in the registry; `osmium export` to GeoJSON, then DuckDB
re-filtering (exact `properties[key]==value`) and conversion to GeoParquet
(`mirror/osm/poi_{extract}.parquet`); `ST_Within` spatial join against the
GISCO geometries per level (`NUTS2`, `NUTS3`, `CITY`) with cross-border clipping
(a POI is counted only in a zone whose country matches that of its source
extract — otherwise the same hospital near a border would be counted twice if
both neighbouring countries are ingested); writing of the canonical partition,
explicit zero for any zone in scope without POIs, systematic `quality =
"osm_completeness_unknown"`, `time` and `source_date` set to the month of the
most recent extract used (`YYYY-MM`).

Known limitations:

- **Uneven completeness.** OSM coverage varies widely between territories; this
  is why `quality` systematically carries `osm_completeness_unknown` rather than
  a completeness estimate.
- **Node/way duplicates are not deduplicated.** The same physical entity (e.g.
  a hospital) may be mapped both as an isolated node and as a building
  footprint; no standard OSM tag formally links the two, and the pipeline does
  not attempt to merge them.
- **`railway=halt` excluded from `train_stations_count`** (stops without a
  passenger building): scope deliberately restricted to `railway=station` for a
  reproducible "station" count rather than a station/stop mix that varies by
  country.
- `.[osm]` installs no additional Python dependency for this pipeline: it
  relies on the `osmium` binary (`brew install osmium-tool`) via `subprocess`,
  and on the DuckDB spatial extension (`INSTALL spatial`), downloaded
  automatically by DuckDB on first use.

## Copernicus pipeline

```bash
# Recommended cadence: weekly (products are annual, the CDS queue is slow)
.venv/bin/python -m nutshell_mcp.sync --source copernicus --indicators lst_summer_mean
```

The pipeline turns a raster into canonical rows: acquisition and temporal
aggregation (`temporal_agg`), reprojection to EPSG:4326, `exactextract` zonal
statistics against the GISCO geometries of each declared level, partition
writing, **purge of the raw raster** (the heaviest item is disposable). The
raster is never kept, only the aggregates are — a few hundred kilobytes per
indicator.

### Three raster providers

`NUTSHELL_CDS_PROVIDER` forces the provenance for the whole batch. Without it,
the provider is inferred from the registry `product`: an ERA5 reanalysis goes to
`cds` if `~/.cdsapirc` exists and to `arco` otherwise; any other product goes to
`local`.

| provider | source | key | quality |
|---|---|---|---|
| `cds` | `cdsapi`, dataset `reanalysis-era5-land-monthly-means` | yes | exact |
| `arco` | public ARCO-ERA5 zarr on GCS, anonymous access | no | `sampled` |
| `local` | hand-dropped GeoTIFF | no | exact |

**`cds` — the official route.** Create an account at
<https://cds.climate.copernicus.eu>, get the personal token from the profile
page, then write `~/.cdsapirc`:

```
url: https://cds.climate.copernicus.eu/api
key: <PERSONAL-TOKEN>
```

Also accept the dataset's terms of use **on its web page**: without this,
`retrieve()` fails. CDS queues last for hours: the pipeline submits all the
batch's requests first, persists the request identifiers in `sync_state`, then
collects — an interruption re-submits nothing.

**`arco` — the keyless fallback.** Anonymous read of
`gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3`. The
store is chunked by global time step: **one network request per requested
hour**, 3 to 9 s each, regardless of the spatial subset. An exact hourly JJA
mean (2208 steps) would take hours. The provider therefore samples
`NUTSHELL_ARCO_SAMPLES_PER_MONTH` time steps per month (default 4, at the
synoptic hours 00/06/12/18 on spread-out days) and marks the result
`quality = "sampled"`: it is an **estimate**, not the climatological mean.
Measured cost: ~1 min for one summer (12 time steps) over LU + BE + FR, 281
NUTS2/NUTS3/CITY zones.

**`local` — the CLMS route.** The Copernicus Land Monitoring Service requires
authentication that the pipeline does not handle: this is the intended path for
`imperviousness_share`. Download the raster from
<https://land.copernicus.eu/en/products/high-resolution-layer-imperviousness>,
reproject it if needed (`gdalwarp -t_srs EPSG:4326 …`) and drop it under
`NUTSHELL_RASTER_DIR/{indicator}/{year}.tif`. The pipeline does the rest. If it
is missing, the error names the expected path and the download URL.

### Configuration

| variable | purpose | default |
|---|---|---|
| `NUTSHELL_CDS_PROVIDER` | `cds` \| `arco` \| `local` | `cds` if key, else `arco` |
| `NUTSHELL_CDS_YEARS` | `2023`, `2020,2023`, `2020-2023` | last complete year |
| `NUTSHELL_CDS_COUNTRIES` | spatial scope, e.g. `LU,BE,FR` | whole reference |
| `NUTSHELL_CDS_BBOX` | forced extent `west,south,east,north` (e.g. `-12,34,35,72` = continental Europe); zones outside the extent are ignored | extent of the zones |
| `NUTSHELL_ARCO_SAMPLES_PER_MONTH` | time steps sampled per month | `4` |
| `NUTSHELL_RASTER_DIR` | root of the `local` provider's rasters | `{data}/rasters` |
| `NUTSHELL_CDS_KEEP_RASTERS` | keep intermediate rasters (debug) | purge |
| `NUTSHELL_CDS_TIMEOUT` / `NUTSHELL_CDS_POLL` | CDS wait and polling (s) | `3600` / `30` |

`NUTSHELL_CDS_COUNTRIES` and `NUTSHELL_CDS_BBOX` are the cost levers: without
them, the extent covers the whole GISCO reference (including the outermost
regions, from Guadeloupe to Réunion), meaning a much heavier CDS request and a
few thousand zones to aggregate.

```bash
NUTSHELL_CDS_PROVIDER=arco NUTSHELL_CDS_COUNTRIES=LU,BE,FR NUTSHELL_CDS_YEARS=2023 \
  .venv/bin/python -m nutshell_mcp.sync --source copernicus --indicators lst_summer_mean
```

```
[copernicus] 1 mis à jour, 0 inchangés, 0 échecs
  ✓ lst_summer_mean (281 lignes, années 2023)
  · périmètre LU, BE, FR : 281 zones sur 3 niveau(x), emprise -63.2/-21.4 → 55.8/51.5
  · fournisseur 'arco'
  · lst_summer_mean 2023 : 12 pas de temps échantillonnés
```

The freshness signal is the last materialised year
(`sync_state("copernicus", "{id}:last_year")`): a year already present is not
recomputed, earlier years are re-read and kept. `--full` ignores this signal.

### Value quality

`sampled` (sampled estimate, `arco` provider) and `partial_coverage` (the zone
is not fully covered by the raster: extent edge, cell with no data) appear in
brackets in `get_indicators`. Temperatures are converted from kelvins to degrees
Celsius to match the registry's `DEG_C` unit.

## Adding an indicator = one YAML file

No code. Drop `registry/{id}.yaml` (the file name must be the `id`), validate,
synchronise:

```yaml
# registry/gdp_per_capita.yaml
id: gdp_per_capita
label: "PIB par habitant (prix courants)"
unit: EUR_HAB
source: eurostat              # eurostat | copernicus | osm
frequency: A                  # A | Q | M | SNAPSHOT
geo_levels: [NUTS0, NUTS1, NUTS2]
nuts_vintage: 2024            # optional (2024 by default, 2021 accepted)
description: "…"              # optional, indexed for search
extraction:                   # section specific to the declared source
  dataset: nama_10r_2gdp
  filters: { freq: A, unit: EUR_HAB }
  value_dim: geo              # dimension projected onto geo_code
```

```bash
.venv/bin/python -m nutshell_mcp.registry validate     # put this in CI
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators gdp_per_capita
```

`extraction` sections for the other sources:

```yaml
source: copernicus
extraction:
  product: reanalysis-era5-land
  variable: skin_temperature
  temporal_agg: { months: [6, 7, 8], stat: mean }
  zonal_stat: mean

source: osm
extraction:
  tags: [{ key: amenity, value: hospital }]   # several pairs = combined with OR
  geometry: [node, way, relation]             # a hospital is often a way or relation
  aggregation: count
```

The server reloads the registry as soon as the YAML files change: a new
indicator shows up in `search_indicators` without a restart. Until it is
materialised, `get_indicators` returns the sync command to run.

Shipped registry: `gdp_per_capita`, `unemployment_rate`, `population`,
`median_age`, `old_age_dependency` (Eurostat, materialisable);
`lst_summer_mean` (Copernicus, materialisable), `imperviousness_share`
(Copernicus, CLMS raster to be dropped in — see *Copernicus pipeline*);
`hospitals_count`, `train_stations_count`, `schools_count` (OSM, batch 2).

## Data layout

Everything is relative to `NUTSHELL_DATA_DIR` (default: repository root).

```
mirror/eurostat/{dataset}.parquet          native grain (dims…, time, value, flag)
mirror/indicators/indicator={id}/part-0.parquet
                                           canonical grain, 9 columns, zstd
mirror/geo/NUTS_RG_{01M|10M}_{2024|2021}_4326_LEVL_{0..3}.geojson
mirror/geo/URAU_RG_100K_{2024|2021}_4326_CITIES.geojson
eurostat.db                                FTS5 catalogue, DSD, registry, sync state
work/                                      temporary, purgeable
registry/*.yaml                            indicator definitions (versioned)
```

Canonical table: `indicator, geo_code, time, value, unit, quality, source,
source_date, ingested_at`. Hive partitioning by indicator, atomic writes (an
indicator is never readable half re-materialised).

Replicating an instance: `rsync` of `mirror/` + `eurostat.db`. The server is
stateless.

Orders of magnitude: catalogue + DSD ~150 MB; GISCO geometries ~173 MB; thematic
native mirror 1–2 GB (24 GB for the whole catalogue); canonical table < 500 MB
even with 100 indicators at NUTS3 level.

## Offline mode

```bash
NUTSHELL_OFFLINE=1 .venv/bin/python -m nutshell_mcp.server
```

No network calls: catalogue, structures and data are served from disk with no
TTL consideration; anything missing returns the sync command to run. In
connected mode, the *serve-stale-on-error* rule applies everywhere — dated local
data is always preferred to an error, and the freshness date is always shown.

Legacy alias kept: `EUROSTAT_OFFLINE=1`.

## Tests

```bash
.venv/bin/pytest -q                                    # no network
.venv/bin/pytest -m network --override-ini="addopts="  # real GISCO + Eurostat ingestion
.venv/bin/ruff check .
```

## Status and next steps

Batch 1 (unified foundation) delivered: geographic reference, registry,
canonical table, Eurostat projection, 3 unified tools.

Batch 2 (OSM) delivered: `nutshell_mcp/ingest_osm.py`, Geofabrik extracts → POIs
→ DuckDB spatial join → counts (`hospitals_count`, `train_stations_count`,
`schools_count`) — see "OSM pipeline" above.

Batch 3 (Copernicus) delivered: `nutshell_mcp/ingest_cds.py`, three raster
providers, `exactextract` zonal statistics — see "Copernicus pipeline".
Remaining:

- **batch 3, follow-ups**: plug in a real CDS key (the `cdsapi` path is
  implemented and tested by mock, never run against the real service) and drop
  in the CLMS imperviousness raster;
- **batch 4 — hardening**: authenticated HTTP, hybrid embedding search, derived
  indicators (densities, distances), full vintage conversion.

Each ingestion module exposes `sync(specs, full) -> SyncReport` and never writes
Parquet itself: the exact contract is documented at the top of
`nutshell_mcp/sync.py` and `nutshell_mcp/indicators.py`.

## License

[GNU Affero General Public License v3.0 or later](LICENSE) (AGPL-3.0-or-later).
If you run a modified version of this server for users over a network, you must
offer them its source code.

Data served by the server remains under its sources' terms: © Eurostat,
© EuroGeographics for the GISCO boundaries, © OpenStreetMap contributors (ODbL),
Copernicus.
