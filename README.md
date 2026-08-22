# territorial-mcp

Serveur MCP de données territoriales européennes — Eurostat, Copernicus et
OpenStreetMap ramenés à un grain unique **zone × indicateur × période**, servi
entièrement hors ligne.

Conçu pour un modèle local de taille moyenne (référence : Qwen3.8-27B) : 7 tools,
schémas étroits, validation côté serveur, sorties bornées et auto-descriptives.
Le modèle ne construit jamais de requête source — ni URL SDMX, ni Overpass QL,
ni requête CDS.

Document de référence : `architecture-spec-mcp-territorial.md`.
Écarts et choix d'implémentation : `DECISIONS.md`.

## Architecture

```
   INGESTION (en ligne, planifiée)          python -m territorial_mcp.sync
   ┌───────────────────────────────────────────────────────────────────┐
   │ GISCO      → geo.py          géométries NUTS/villes + table geo   │
   │ Eurostat   → mirror.py       bulk TSV.gz → Parquet natif          │
   │              project_eurostat.py  → projection au grain canonique │
   │ OpenStreetMap → ingest_osm.py     (lot 2, à venir)                │
   │ Copernicus    → ingest_cds.py     (lot 3, à venir)                │
   └───────────────────────────────┬───────────────────────────────────┘
                                   ▼
   STOCKAGE (local, rsyncable)
   ┌───────────────────────────────────────────────────────────────────┐
   │ mirror/eurostat/{dataset}.parquet          grain natif            │
   │ mirror/indicators/indicator={id}/…         grain canonique        │
   │ mirror/geo/*.geojson                       géométries GISCO       │
   │ eurostat.db                catalogue FTS5, DSD, registre, sync    │
   │ registry/*.yaml            définitions d'indicateurs (versionné)  │
   └───────────────────────────────┬───────────────────────────────────┘
                                   ▼
   SERVICE (offline)                        python -m territorial_mcp.server
   ┌───────────────────────────────────────────────────────────────────┐
   │ couche unifiée : search_indicators, list_zones, get_indicators    │
   │ grain natif    : search_datasets, get_structure, list_codes,      │
   │                  query_data                                       │
   └───────────────────────────────────────────────────────────────────┘
```

Ingestion et service sont découplés : le serveur ne lit que le disque. Une panne
des APIs sources n'affecte jamais une conversation en cours.

## Installation

```bash
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ".[dev]"

.venv/bin/python -m territorial_mcp.server                      # stdio
MCP_TRANSPORT=http .venv/bin/python -m territorial_mcp.server   # streamable HTTP
```

Extras optionnels, nécessaires aux seuls pipelines d'ingestion correspondants :
`.[osm]`, `.[copernicus]`. Le serveur démarre sans eux.

Config client MCP (stdio) :

```json
{
  "mcpServers": {
    "territorial": {
      "command": "python",
      "args": ["-m", "territorial_mcp.server"],
      "cwd": "/chemin/vers/territorial-mcp",
      "env": { "TERRITORIAL_OFFLINE": "1" }
    }
  }
}
```

## Les 7 tools

### Couche unifiée — croiser les sources

| tool | rôle | sortie |
|---|---|---|
| `search_indicators(query, source="", limit=10)` | trouver un indicateur dans le registre | `id \| label \| unité \| freq \| niveaux geo \| source` |
| `list_zones(level, parent="", contains="")` | parcourir le référentiel géographique | `geo_code \| name \| level \| parent` |
| `get_indicators(indicators, zones, time_from="", time_to="")` | valeurs, **une colonne par indicateur** | tableau pivoté + ligne de provenance |

### Grain natif Eurostat — toutes dimensions

`search_datasets` → `get_structure` → `list_codes` → `query_data`, sur les
10 301 datasets du catalogue, y compris ceux qu'aucun indicateur ne projette.

### Séquence type côté agent

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

Garde-fous : 5 indicateurs et 100 zones maximum par appel ; sans filtre
temporel, les 3 dernières périodes ; 400 lignes maximum, toute troncature
indiquant l'action corrective. Les crochets après une valeur portent le flag
qualité (`p` provisoire, `d` définition différente, `recoded`,
`osm_completeness_unknown`…).

Toute erreur est actionnable :

```
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux
disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).

Indicateur 'lst_summer_mean' non matérialisé et mode offline actif.
Lancer : python -m territorial_mcp.sync --source copernicus --indicators lst_summer_mean
```

Note pour Qwen3.8-27B : forcer un niveau de raisonnement moyen/bas (le défaut
`xhigh` sur-réfléchit les enchaînements de tools simples).

## Synchronisation

```bash
# Référentiel géographique (mensuel) — 18 fichiers GISCO, ~173 Mo
.venv/bin/python -m territorial_mcp.sync --source geo

# Indicateurs Eurostat du registre (quotidien) — TOC-driven, idempotent
.venv/bin/python -m territorial_mcp.sync --source eurostat

# Un indicateur précis
.venv/bin/python -m territorial_mcp.sync --source eurostat --indicators gdp_per_capita

# Tout, en ignorant les signaux de fraîcheur
.venv/bin/python -m territorial_mcp.sync --source all --full
```

Idempotent, conçu pour un cron. Chaque source publie un signal de fraîcheur
(`last update of data` du TOC Eurostat, ETag GISCO) comparé à l'état local dans
`eurostat.db` : rien n'est retéléchargé sans raison, il n'y a pas de TTL. Un
échec sur un indicateur n'interrompt pas le lot ; le rapport final liste mis à
jour / inchangés / échecs.

Le miroir natif reste pilotable seul :

```bash
.venv/bin/python -m territorial_mcp.mirror --datasets nama_10_gdp,une_rt_m
.venv/bin/python -m territorial_mcp.mirror --resync        # TOC-driven
.venv/bin/python -m territorial_mcp.mirror --project-only  # reprojette, zéro réseau
.venv/bin/python -m territorial_mcp.mirror --all           # ~24 Go compressés !
```

## Ajouter un indicateur = un fichier YAML

Aucun code. Déposer `registry/{id}.yaml` (le nom du fichier doit être l'`id`),
valider, synchroniser :

```yaml
# registry/gdp_per_capita.yaml
id: gdp_per_capita
label: "PIB par habitant (prix courants)"
unit: EUR_HAB
source: eurostat              # eurostat | copernicus | osm
frequency: A                  # A | Q | M | SNAPSHOT
geo_levels: [NUTS0, NUTS1, NUTS2]
nuts_vintage: 2024            # optionnel (2024 par défaut, 2021 accepté)
description: "…"              # optionnel, indexé pour la recherche
extraction:                   # section propre à la source déclarée
  dataset: nama_10r_2gdp
  filters: { freq: A, unit: EUR_HAB }
  value_dim: geo              # dimension projetée sur geo_code
```

```bash
.venv/bin/python -m territorial_mcp.registry validate     # à mettre en CI
.venv/bin/python -m territorial_mcp.sync --source eurostat --indicators gdp_per_capita
```

Sections `extraction` des autres sources :

```yaml
source: copernicus
extraction:
  product: reanalysis-era5-land
  variable: skin_temperature
  temporal_agg: { months: [6, 7, 8], stat: mean }
  zonal_stat: mean

source: osm
extraction:
  tags: [{ key: amenity, value: hospital }]
  geometry: [node, way]
  aggregation: count
```

Le serveur relit le registre dès que les YAML changent : un nouvel indicateur
apparaît dans `search_indicators` sans redémarrage. Tant qu'il n'est pas
matérialisé, `get_indicators` renvoie la commande de sync à lancer.

Registre livré : `gdp_per_capita`, `unemployment_rate`, `population`,
`median_age`, `old_age_dependency` (Eurostat, matérialisables) ;
`lst_summer_mean`, `imperviousness_share` (Copernicus, lot 3) ;
`hospitals_count`, `train_stations_count`, `schools_count` (OSM, lot 2).

## Layout des données

Tout est relatif à `TERRITORIAL_DATA_DIR` (défaut : racine du dépôt).

```
mirror/eurostat/{dataset}.parquet          grain natif (dims…, time, value, flag)
mirror/indicators/indicator={id}/part-0.parquet
                                           grain canonique, 9 colonnes, zstd
mirror/geo/NUTS_RG_{01M|10M}_{2024|2021}_4326_LEVL_{0..3}.geojson
mirror/geo/URAU_RG_100K_{2024|2021}_4326_CITIES.geojson
eurostat.db                                catalogue FTS5, DSD, registre, états sync
work/                                      temporaire, purgeable
registry/*.yaml                            définitions d'indicateurs (versionné)
```

Table canonique : `indicator, geo_code, time, value, unit, quality, source,
source_date, ingested_at`. Partitionnement Hive par indicateur, écriture
atomique (un indicateur n'est jamais lisible à moitié re-matérialisé).

Réplication d'une instance : `rsync` de `mirror/` + `eurostat.db`. Le serveur est
sans état.

Ordres de grandeur : catalogue + DSD ~150 Mo ; géométries GISCO ~173 Mo ; miroir
natif thématique 1-2 Go (24 Go pour l'intégralité du catalogue) ; table canonique
< 500 Mo même à 100 indicateurs au niveau NUTS3.

## Mode offline

```bash
TERRITORIAL_OFFLINE=1 .venv/bin/python -m territorial_mcp.server
```

Aucun appel réseau : catalogue, structures et données servis depuis le disque
sans considération de TTL ; tout élément absent renvoie la commande de sync à
exécuter. En mode connecté, la règle *serve-stale-on-error* s'applique partout —
une donnée locale datée est toujours préférée à une erreur, la date de fraîcheur
étant systématiquement affichée.

Alias historique conservé : `EUROSTAT_OFFLINE=1`.

## Tests

```bash
.venv/bin/pytest -q                                    # sans réseau
.venv/bin/pytest -m network --override-ini="addopts="  # ingestion GISCO + Eurostat réelles
.venv/bin/ruff check .
```

## État et suite

Lot 1 (socle unifié) livré : référentiel géographique, registre, table canonique,
projection Eurostat, 3 tools unifiés. Restent à implémenter :

- **lot 2 — OSM** : `territorial_mcp/ingest_osm.py`, extraits Geofabrik → POI →
  jointure spatiale DuckDB → comptages ;
- **lot 3 — Copernicus** : `territorial_mcp/ingest_cds.py`, requêtes CDS →
  agrégation temporelle xarray → statistiques zonales `exactextract` ;
- **lot 4 — durcissement** : HTTP authentifié, recherche hybride par embeddings,
  indicateurs dérivés (densités, distances), conversion complète des millésimes.

Chaque module d'ingestion expose `sync(specs, full) -> SyncReport` et n'écrit
jamais de Parquet lui-même : le contrat exact est documenté en tête de
`territorial_mcp/sync.py` et `territorial_mcp/indicators.py`.
