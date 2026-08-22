# Serveur MCP de données territoriales européennes
## Document d'architecture et de spécification technique

**Version** 0.9 (draft) — 22 août 2026
**Périmètre** : généralisation du serveur MCP Eurostat à trois sources (Eurostat, Copernicus, OpenStreetMap) selon un pattern d'ingestion et un format de requête unifiés, avec mode offline total.

---

## 1. Contexte et objectifs

Le serveur MCP Eurostat existant a validé un pattern : un modèle de langage local de taille moyenne (référence : Qwen3.8-27B) devient fiable sur des données statistiques complexes à condition que le serveur porte toute la complexité — recherche, validation, compaction — et que le modèle ne manipule que des concepts. Le présent document spécifie l'extension de ce pattern à un socle multi-sources dans lequel données socio-économiques (Eurostat), environnementales (Copernicus) et infrastructurelles (OpenStreetMap) convergent vers un même grain d'interrogation : **zone géographique × indicateur × période**.

Les objectifs sont, dans l'ordre de priorité : (1) permettre à un agent de joindre les trois sources sans étape de réconciliation, en s'appuyant sur les codes NUTS comme clé commune ; (2) garantir un fonctionnement offline total, les APIs sources n'étant sollicitées qu'à l'ingestion ; (3) rester exploitable par un modèle 27B local, ce qui impose des schémas de tools étroits et des sorties bornées ; (4) conserver la traçabilité de chaque valeur jusqu'à sa source et sa date de fraîcheur.

Sont hors périmètre de cette version : les données à grain infra-communal (adresses, bâtiments individuels), le temps réel, l'écriture vers les sources, et la génération cartographique (le serveur renvoie des données tabulaires ; la visualisation appartient au client).

## 2. Principes d'architecture

Cinq principes gouvernent l'ensemble et arbitrent tout choix de conception.

**P1 — Le modèle ne construit jamais de requête source.** Ni URL SDMX, ni Overpass QL, ni requête CDS. Chaque source expose un DSL piégeux qu'un modèle 27B produira incorrectement. Les tools exposent un vocabulaire fermé ; le serveur traduit, valide et exécute.

**P2 — Ingestion et service sont découplés.** Les pipelines d'ingestion tournent en tâche planifiée, en ligne, et matérialisent tout en Parquet local. Le serveur MCP ne lit que le disque. Une panne ou une lenteur des APIs sources n'affecte jamais une conversation en cours.

**P3 — Invalidation événementielle, pas de TTL.** Chaque source publie un signal de fraîcheur (TOC Eurostat, versioning des datasets CDS, timestamps de réplication Geofabrik). La synchronisation compare ces signaux à l'état local et ne retélécharge que le delta. Le TTL n'existe qu'en garde-fou de dernier recours.

**P4 — Grain canonique unique pour l'interrogation croisée.** Toute donnée destinée aux jointures inter-sources est projetée au grain zone × indicateur × période dans une table unique, quel que soit son format d'origine (cube SDMX, raster, géométries vectorielles). L'accès au grain natif Eurostat (dimensions complètes) reste disponible en parallèle.

**P5 — Sorties bornées et auto-descriptives.** Toute réponse de tool est plafonnée (400 lignes), indique sa source et sa date de données, et toute erreur est actionnable (suggestion de code proche, commande de sync à lancer).

## 3. Vue d'ensemble

```
                        ┌──────────────  INGESTION (en ligne, planifiée)  ─────────────┐
                        │                                                              │
  Eurostat ────────────►│ mirror.py        bulk TSV.gz → Parquet natif (par dataset)   │
  (TOC + bulk SDMX)     │                  + projection indicateurs enregistrés        │
                        │                                                              │
  Copernicus ──────────►│ ingest_cds.py    rasters ERA5-Land / CLMS → statistiques     │
  (CDS / Data Space)    │                  zonales (exactextract) par zone NUTS        │
                        │                                                              │
  OpenStreetMap ───────►│ ingest_osm.py    extraits Geofabrik .pbf → filtrage POI      │
  (Geofabrik)           │                  (osmium) → jointure spatiale → comptages    │
                        │                                                              │
  GISCO ───────────────►│ ingest_geo.py    géométries NUTS / villes + table geo        │
                        └───────────────────────────┬──────────────────────────────────┘
                                                    ▼
                        ┌────────────────  STOCKAGE (local)  ──────────────────────────┐
                        │  mirror/eurostat/{dataset}.parquet     grain natif           │
                        │  mirror/indicators.parquet             grain canonique       │
                        │  mirror/geo/                           géométries + refs     │
                        │  eurostat.db (SQLite)                  catalogue FTS5, DSD,  │
                        │                                        registre, états sync  │
                        └───────────────────────────┬──────────────────────────────────┘
                                                    ▼
                        ┌────────────────  SERVICE (offline)  ─────────────────────────┐
                        │  server.py (FastMCP + DuckDB)                                │
                        │  tools natifs Eurostat : search_datasets, get_structure,     │
                        │                          list_codes, query_data              │
                        │  tools unifiés :         search_indicators, get_indicators,  │
                        │                          list_zones                          │
                        └───────────────────────────┬──────────────────────────────────┘
                                                    ▼
                              Agent (Qwen3.8-27B via vLLM / llama.cpp)
```

## 4. Référentiel géographique

La clé de jointure de tout le système est le code de zone. Le référentiel est construit depuis GISCO (service géographique d'Eurostat), ce qui garantit la cohérence avec les codes utilisés dans les datasets Eurostat eux-mêmes.

La table `geo` recense chaque zone : `geo_code` (clé, ex. `FR101`), `level` (`NUTS0` à `NUTS3`, `CITY` pour les codes Urban Audit), `name`, `parent_code`, `valid_from` (millésime NUTS). Les géométries (GeoJSON/GeoParquet, résolution 1:1M pour les statistiques zonales, 1:10M pour l'affichage) sont stockées dans `mirror/geo/` et ne servent qu'à l'ingestion (statistiques zonales, jointures spatiales) — elles ne transitent jamais vers le modèle.

Le système gère le millésime NUTS courant (NUTS 2024) et le précédent (NUTS 2021). Chaque indicateur déclare son millésime ; la table de correspondance GISCO entre millésimes permet la conversion à l'ingestion. Les données historiques Eurostat publiées en NUTS 2021 sont projetées vers NUTS 2024 quand la correspondance est bijective, et marquées `quality = 'recoded'` sinon.

## 5. Registre d'indicateurs

Le registre est le contrat central du système : c'est lui qui définit ce qui existe au grain canonique. Un indicateur est une définition déclarative versionnée (fichiers YAML sous `registry/`), qui spécifie comment le matérialiser depuis sa source.

```yaml
# registry/gdp_per_capita.yaml
id: gdp_per_capita
label: "PIB par habitant (prix courants)"
unit: EUR_HAB
source: eurostat
frequency: A
geo_levels: [NUTS0, NUTS1, NUTS2]
extraction:
  dataset: nama_10r_2gdp
  filters: { unit: EUR_HAB }
  value_dim: geo            # la dimension projetée sur geo_code

# registry/lst_summer_mean.yaml
id: lst_summer_mean
label: "Température de surface moyenne, juin-août"
unit: DEG_C
source: copernicus
frequency: A
geo_levels: [NUTS2, NUTS3, CITY]
extraction:
  product: reanalysis-era5-land
  variable: skin_temperature
  temporal_agg: { months: [6, 7, 8], stat: mean }
  zonal_stat: mean

# registry/hospitals_count.yaml
id: hospitals_count
label: "Hôpitaux (comptage OSM)"
unit: COUNT
source: osm
frequency: SNAPSHOT
geo_levels: [NUTS2, NUTS3, CITY]
extraction:
  tags: [{ key: amenity, value: hospital }]
  geometry: [node, way]
  aggregation: count
```

Ajouter un indicateur = ajouter un fichier YAML ; aucun code. Le pipeline de la source concernée lit le registre, matérialise, et le tool `search_indicators` l'expose immédiatement. La validation du registre (schéma pydantic) fait partie de la CI : `id` unique, source connue, spécification d'extraction complète pour la source déclarée.

## 6. Modèle de stockage

### 6.1 Table canonique `indicators.parquet`

| colonne | type | description |
|---|---|---|
| `indicator` | string | id du registre (`gdp_per_capita`) |
| `geo_code` | string | code de zone du référentiel (`FR101`) |
| `time` | string | période au format Eurostat (`2023`, `2023-Q1`, `2023-01`) |
| `value` | double | valeur |
| `unit` | string | unité (dénormalisée depuis le registre) |
| `quality` | string | vide, ou flag source Eurostat, ou `recoded`, `partial_coverage`… |
| `source` | string | `eurostat` / `copernicus` / `osm` |
| `source_date` | string | date des données à la source (TOC, version CDS, date d'extrait .pbf) |
| `ingested_at` | timestamp | date de matérialisation locale |

Partitionnement Hive par `indicator` (`indicators/indicator=gdp_per_capita/part-0.parquet`), compression zstd. Le partitionnement rend les requêtes mono-indicateur (le cas dominant) quasi gratuites en pruning DuckDB, et permet la re-matérialisation atomique d'un indicateur sans toucher aux autres.

Le format `time` reprend les conventions Eurostat pour toutes les sources : les données Copernicus annualisées sont émises en `AAAA`, les snapshots OSM en `AAAA-MM` de l'extrait. La comparaison temporelle inclusive spécifiée en §8.3 s'applique uniformément.

### 6.2 Miroir natif Eurostat

Inchangé par rapport à l'existant : un Parquet long format par dataset (`dims…, time, value, flag`) sous `mirror/eurostat/`, alimenté par les bulk TSV.gz, état de synchronisation piloté par le TOC. C'est le niveau de détail complet, servi par `query_data`. Dimensionnement mesuré : ~2,8 octets compressés par valeur, soit ~24 Go pour l'intégralité du catalogue (8,48 milliards de valeurs), ou 1-2 Go pour un sous-ensemble thématique de quelques centaines de datasets.

### 6.3 Métadonnées SQLite (`eurostat.db`)

Quatre familles de tables : le catalogue Eurostat en FTS5 (recherche full-text), les structures DSD (validation et `list_codes`), le registre matérialisé (`registry` : payload YAML parsé + FTS5 sur id/label pour `search_indicators`), et les états de synchronisation par source (`mirror_state`, `sync_state_cds`, `sync_state_osm` : signal de fraîcheur distant vs. local).

## 7. Pipelines d'ingestion

Chaque pipeline suit le même contrat : lire le signal de fraîcheur distant, comparer à l'état local, matérialiser le delta en écriture atomique (fichier `.tmp` puis `rename`), mettre à jour l'état, journaliser. Un échec sur un indicateur n'interrompt pas le lot ; le rapport final liste mis à jour / inchangés / échecs.

### 7.1 Eurostat (`mirror.py`, existant, étendu)

Le pipeline existant est conservé et étendu d'une étape de projection : après matérialisation du Parquet natif d'un dataset, chaque indicateur du registre pointant vers ce dataset est re-matérialisé — une requête DuckDB applique les `filters` du registre, renomme la dimension `value_dim` en `geo_code`, joint la table `geo` pour ne garder que les codes du référentiel, et écrit la partition. Signal de fraîcheur : colonnes `last update of data` du TOC, comme aujourd'hui.

### 7.2 Copernicus (`ingest_cds.py`)

Séquence par indicateur : (1) soumission de la requête CDS (`cdsapi`) pour la fenêtre temporelle manquante — les files d'attente CDS pouvant durer des heures, le pipeline soumet toutes les requêtes du lot puis collecte les résultats de façon asynchrone, avec reprise sur interruption ; (2) agrégation temporelle du NetCDF selon `temporal_agg` (xarray) ; (3) statistiques zonales contre les géométries GISCO du niveau demandé (`exactextract`, qui gère correctement les pixels partiellement couverts) ; (4) écriture de la partition. Signal de fraîcheur : les datasets CDS étant versionnés et append-only sur l'axe temps, l'état local enregistre la dernière période matérialisée ; la synchronisation ne demande que les périodes nouvelles.

Dimensionnement : les rasters bruts (le poste le plus lourd, ~5-15 Go par indicateur×décennie en ERA5-Land Europe) sont supprimables après matérialisation ; les statistiques zonales pèsent quelques Mo par indicateur. Prévoir un volume de travail temporaire de 50 Go pour l'ingestion, un stockage pérenne négligeable.

### 7.3 OpenStreetMap (`ingest_osm.py`)

Séquence : (1) téléchargement de l'extrait Geofabrik (Europe entière ~30 Go .pbf, ou par pays pour un périmètre restreint) ; (2) filtrage des tags de tous les indicateurs OSM du registre en une seule passe `osmium tags-filter` → GeoParquet des POI (~1-2 Go pour l'Europe) ; (3) jointure spatiale POI × géométries NUTS/villes en DuckDB (extension `spatial`) et agrégation selon le registre (`count`, à terme `density`, `nearest_distance`) ; (4) écriture des partitions, `time` = mois de l'extrait, `quality = 'osm_completeness_unknown'` systématique — la complétude d'OSM varie fortement selon les territoires et le modèle doit pouvoir le restituer. Signal de fraîcheur : timestamp de l'extrait Geofabrik publié ; cadence mensuelle recommandée.

### 7.4 Orchestration

Un point d'entrée unique `python -m platform.sync [--source eurostat|copernicus|osm|geo] [--indicators id,…] [--full]`, idempotent, conçu pour un cron quotidien (Eurostat), hebdomadaire (Copernicus) et mensuel (OSM + référentiel geo). Pas d'orchestrateur externe requis ; les états en SQLite suffisent à la reprise.

## 8. Spécification des tools MCP

Le serveur expose sept tools : les quatre tools natifs Eurostat existants (inchangés, spécifiés dans le squelette actuel) et trois tools unifiés. Règles transverses : toute sortie est du texte tabulaire compact plafonné à 400 lignes ; toute troncature est signalée avec l'action corrective ; toute réponse de données se termine par la ligne de provenance `[Source : {source}, données du {source_date}, ingérées le {ingested_at}]` ; toute erreur de vocabulaire renvoie les 3 candidats les plus proches (difflib).

### 8.1 `search_indicators(query: str, source: str = "", limit: int = 10) -> str`

Recherche FTS5 sur id + label du registre, filtre optionnel par source. Sortie : `id | label | unit | freq | niveaux geo | source`. C'est le point d'entrée de toute session agentique croisée.

### 8.2 `list_zones(level: str, parent: str = "", contains: str = "") -> str`

Parcours du référentiel geo : zones d'un niveau (`NUTS2`), optionnellement sous un parent (`FR`) ou filtrées par sous-chaîne sur le nom. Sortie : `geo_code | name | level | parent`. Remplace, pour la couche unifiée, l'exploration de la codelist `geo` d'Eurostat.

### 8.3 `get_indicators(indicators: list[str], zones: list[str], time_from: str = "", time_to: str = "") -> str`

Le tool central. Validation : chaque id contre le registre, chaque zone contre le référentiel (avec suggestions), compatibilité niveau des zones × `geo_levels` des indicateurs (erreur explicite sinon : « `lst_summer_mean` n'existe pas au niveau NUTS0 ; niveaux disponibles : NUTS2, NUTS3, CITY »). Exécution : requête DuckDB sur les partitions concernées, filtre temporel inclusif (`time <= borne OR time LIKE borne || '-%'`). Sortie **pivotée par indicateur** quand plusieurs sont demandés — une colonne par indicateur, une ligne par zone × période — précisément pour matérialiser la jointure que l'agent cherche :

```
geo_code | time | gdp_per_capita | lst_summer_mean | hospitals_count
FR101    | 2023 | 59300          | 27.9            | 41
BE100    | 2023 | 71200          | 26.4            | 38
[Source : eurostat (21.08.2026), copernicus (v2023), osm (extrait 2026-08)]
```

Garde-fous : maximum 5 indicateurs et 100 zones par appel ; sans filtre temporel, seules les 3 dernières périodes sont renvoyées.

### 8.4 Tools natifs Eurostat

`search_datasets`, `get_structure`, `list_codes`, `query_data` restent la voie d'accès au grain complet (toutes dimensions) des 10 301 datasets, y compris ceux qu'aucun indicateur du registre ne projette. La description de `query_data` oriente l'agent : « pour croiser avec des indicateurs environnementaux ou d'infrastructure, préférer get_indicators ».

### 8.5 Note sur le dimensionnement pour un modèle 27B

Sept tools est un maximum délibéré. Les descriptions de tools mentionnent explicitement le tool suivant attendu (`search_indicators` → `get_indicators` ; `search_datasets` → `get_structure` → `query_data`) pour guider le chaînage. Les paramètres sont des types simples (listes de chaînes, pas d'objets imbriqués) ; le vocabulaire (ids d'indicateurs, codes de zones) est toujours découvrable par un tool amont, jamais supposé connu.

## 9. Modes de fonctionnement et résilience

`EUROSTAT_OFFLINE=1` (à renommer `PLATFORM_OFFLINE=1`) verrouille le service sur le disque : aucun appel réseau, structures et catalogue servis sans considération de TTL, et tout élément absent renvoie la commande de sync à exécuter. En mode connecté, la règle serve-stale-on-error s'applique partout : une donnée locale datée est toujours préférée à une erreur, la date de fraîcheur étant systématiquement affichée (P5). Le transport est stdio en usage local mono-utilisateur, streamable HTTP conteneurisé sinon ; en HTTP multi-utilisateurs, ajouter authentification bearer et rate limiting en frontal — le serveur lui-même reste sans état, tout l'état vivant est dans SQLite et les Parquet, ce qui rend la réplication triviale (rsync du répertoire `mirror/` + `eurostat.db`).

## 10. Dimensionnement récapitulatif

| poste | volume | notes |
|---|---|---|
| Catalogue + DSD complets (SQLite) | ~150 Mo | mesuré : 8 Ko/structure × 10 301 |
| Miroir natif Eurostat complet | ~24 Go | mesuré : 2,8 o/valeur × 8,48 Md |
| Miroir natif Eurostat thématique | 1-2 Go | quelques centaines de datasets |
| Table canonique `indicators` | < 500 Mo | même à 100 indicateurs × NUTS3 |
| Géométries GISCO (2 résolutions, 2 millésimes) | ~500 Mo | |
| POI OSM Europe filtrés (GeoParquet) | 1-2 Go | agrégats seuls : quelques Mo |
| Espace de travail ingestion (rasters, .pbf) | 50-80 Go | purgeable après matérialisation |

Configuration cible recommandée : 100 Go de stockage pour la version complète avec espace de travail ; 10 Go pour une version thématique sans re-ingestion Copernicus/OSM locale.

## 11. Plan de mise en œuvre

**Lot 1 — Socle unifié (l'existant + canonique)** : table `geo` depuis GISCO, registre YAML + validation, projection des indicateurs Eurostat depuis le miroir natif, tools `search_indicators`, `list_zones`, `get_indicators`. Critère de sortie : la démo « briefing offline » fonctionne sur indicateurs Eurostat purs.

**Lot 2 — OSM** : pipeline Geofabrik → POI → agrégats, 3 indicateurs (hôpitaux, gares, établissements scolaires). Critère : démo « régions en décrochage » complète.

**Lot 3 — Copernicus** : pipeline CDS → zonal stats, 2 indicateurs (`lst_summer_mean`, `imperviousness_share`). Critère : démo « chaleur urbaine et populations vulnérables » complète.

**Lot 4 — Durcissement** : mode HTTP authentifié, recherche hybride (embeddings) sur registre et catalogue, indicateurs dérivés (densités, distances au plus proche), conversion complète des millésimes NUTS.

Les lots 2 et 3 sont indépendants et parallélisables ; leur seul prérequis commun est le lot 1.

---

## Annexe A — Contrat d'erreur (exemples normatifs)

```
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

Zone 'FR10' de niveau NUTS2 : 'lst_summer_mean' n'y est pas disponible
au niveau demandé pour 'hospitals_count' (CITY). Séparez la requête ou
utilisez list_zones("NUTS3", parent="FR10").

Indicateur 'imperviousness_share' non matérialisé et mode offline actif.
Lancer : python -m platform.sync --source copernicus --indicators imperviousness_share
```

## Annexe B — Décisions d'architecture (ADR condensés)

**ADR-1. Parquet + DuckDB plutôt que PostgreSQL/PostGIS.** Le système est en lecture seule au service, mono-écrivain à l'ingestion, sans besoin transactionnel. Parquet donne la portabilité (rsync = réplication), DuckDB les performances analytiques et l'extension spatiale pour l'ingestion OSM. PostGIS redeviendrait pertinent si des requêtes spatiales devaient être servies en ligne — hors périmètre (P4 : le spatial est résolu à l'ingestion).

**ADR-2. Registre déclaratif plutôt que code par indicateur.** Le coût marginal d'un indicateur doit être un fichier YAML relu en revue, pas du code testé. La complexité reste concentrée dans trois pipelines génériques par source.

**ADR-3. Grain canonique zone × indicateur × période plutôt que fédération de schémas.** Une fédération (chaque source son schéma, jointure à la volée) est plus expressive mais reporte la complexité sur le modèle — inacceptable pour un 27B (P1). La perte d'expressivité est compensée par le maintien de l'accès natif Eurostat.

**ADR-4. Codes NUTS/GISCO comme référentiel unique.** Alternative considérée : grilles régulières (Eurostat GRID, H3). Rejetée en v1 : les NUTS sont le langage des utilisateurs cibles et des données Eurostat elles-mêmes ; les grilles restent une évolution possible pour les cas où le découpage administratif est un artefact (chaleur urbaine intra-ville).
