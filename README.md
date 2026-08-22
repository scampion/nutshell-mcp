# eurostat-mcp

Serveur MCP d'accès aux données Eurostat, conçu pour des modèles locaux
(testé pour Qwen3.8-27B) : 4 tools, schémas étroits, validation côté
serveur, sorties compactées.

## Architecture

```
Modèle (Qwen3.8-27B via vLLM / llama.cpp + harness MCP)
   │  tool calls
   ▼
server.py        4 tools : search_datasets, get_structure, list_codes, query_data
   │             validation DSD + suggestions difflib + plafond 400 cellules
   ▼
store.py         SQLite : catalogue en FTS5 (TTL 24h), structures DSD (TTL 24h)
   ▼
eurostat_client.py   API dissémination Eurostat (catalogue TSV + Statistics JSON-stat)
```

Le modèle ne construit jamais d'URL SDMX. Toute requête passe par
`query_data`, qui valide dimensions et codes contre le DSD en cache et
renvoie des erreurs actionnables (`Code 'FRA' inconnu. Vouliez-vous : FR ?`).

## Installation

```bash
pip install "mcp>=1.2" httpx pyarrow duckdb   # SDK mcp 1.x et 2.x
python -m territorial_mcp.server                      # stdio
MCP_TRANSPORT=http python -m territorial_mcp.server   # streamable HTTP
```

Config client MCP (stdio) :

```json
{
  "mcpServers": {
    "eurostat": {
      "command": "python",
      "args": ["-m", "territorial_mcp.server"],
      "cwd": "/chemin/vers/eurostat-mcp"
    }
  }
}
```

## Séquence type côté modèle

1. `search_datasets("GDP quarterly")` → codes candidats
2. `get_structure("namq_10_gdp")` → dimensions, codes tronqués
3. `list_codes("namq_10_gdp", "geo", contains="fr")` si besoin
4. `query_data("namq_10_gdp", {"geo": "FR+BE", "na_item": "B1GQ",
   "unit": "CP_MEUR"}, time_from="2022")`

Note pour Qwen3.8-27B : forcer un niveau de raisonnement moyen/bas
(le défaut `xhigh` sur-réfléchit les enchaînements de tools simples).

## Mode offline total

```bash
# 1. (en ligne) construire le miroir — TOC-driven, idempotent
python -m territorial_mcp.mirror --datasets nama_10_gdp,une_rt_m
python -m territorial_mcp.mirror --all        # tout le catalogue, ~24 Go compressés
python -m territorial_mcp.mirror --resync     # cron quotidien : ne retélécharge
                                           # que ce que le TOC signale comme modifié

# 2. (hors ligne) servir uniquement depuis le miroir + caches
EUROSTAT_OFFLINE=1 python -m territorial_mcp.server
```

- Données : Parquet zstd long format (dims, time, value, flag), un fichier
  par dataset, interrogé par DuckDB. `query_data` sert le miroir en priorité
  même hors mode offline, et affiche la date des données ("miroir local,
  données Eurostat du JJ.MM.AAAA").
- Structures + catalogue : mis à jour à chaque sync, servis sans TTL en
  mode offline ; serve-stale-on-error quand Eurostat est injoignable.
- L'invalidation est pilotée par les colonnes `last update of data` du TOC,
  pas par un TTL : `--resync` ne touche que les datasets modifiés.

## Limites du squelette et évolutions

- **Recherche** : FTS5/BM25 seul. Ajouter une recherche hybride avec
  embeddings (ex. bge-m3 dans sqlite-vec) pour les requêtes vagues.
- **Structures** : récupérées via l'astuce `lastTimePeriod=1` sur l'API
  Statistics. Pour les très gros datasets, basculer sur l'endpoint SDMX
  2.1 `datastructure` (XML) avec parsing dédié.
- **Cache données** : seules les structures sont cachées. Ajouter un
  cache des réponses `query_data` (TTL 24h — Eurostat publie à 11h/23h).
- **Agrégations** : migrer store.py vers DuckDB pour offrir des
  agrégations côté serveur (moyennes, croissance) au lieu de renvoyer
  des données brutes au modèle.
- **HTTP multi-utilisateurs** : ajouter auth (bearer) et rate limiting
  devant le transport streamable HTTP.
