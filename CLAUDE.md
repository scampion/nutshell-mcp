# territorial-mcp — conventions de travail

Serveur MCP de données territoriales européennes (Eurostat, Copernicus, OSM).
**Document de référence : `architecture-spec-mcp-territorial.md`** — toute implémentation
doit s'y conformer (principes P1–P5, §6 stockage, §7 pipelines, §8 tools, Annexe A contrat d'erreur).
En cas d'écart nécessaire, le documenter dans `DECISIONS.md` (ADR court) plutôt que de dévier en silence.

## Décisions figées (ne pas rediscuter)
- Package Python : `territorial_mcp` (la spec dit `platform.*` — impossible, `platform` est un module stdlib).
  Point d'entrée sync : `python -m territorial_mcp.sync`. Serveur : `python -m territorial_mcp.server`.
- Offline : `TERRITORIAL_OFFLINE=1` (alias conservé : `EUROSTAT_OFFLINE=1`).
- Données à la racine du projet (configurable par `TERRITORIAL_DATA_DIR`, défaut = racine du dépôt) :
  `mirror/eurostat/{dataset}.parquet`, `mirror/indicators/indicator={id}/part-0.parquet`,
  `mirror/geo/`, `eurostat.db` (SQLite : catalogue FTS5, DSD, registry, états de sync), `work/` (temporaire purgeable).
- Registre : `registry/*.yaml`, un indicateur par fichier, validé par pydantic (`territorial_mcp/registry.py`).
- Langue : code/identifiants en anglais, docstrings, messages utilisateur et sorties de tools en **français**
  (cohérent avec l'existant). Commentaires concis.
- Dépendances : stdlib + duckdb + pyarrow + httpx + pydantic + pyyaml + mcp. Les dépendances lourdes
  (xarray, exactextract, shapely…) vont dans les extras `[osm]` / `[copernicus]` de `pyproject.toml`,
  importées paresseusement dans leur module d'ingestion uniquement. Le serveur doit démarrer sans ces extras.
- Écritures Parquet atomiques (`.tmp` puis `rename`). Pas de TTL pour l'invalidation : signaux de fraîcheur source (P3).
- Sorties de tools : texte tabulaire `a | b | c`, plafond 400 lignes, ligne de provenance finale, erreurs actionnables
  avec suggestions difflib (3 max). Pas de JSON renvoyé au modèle.

## Environnement
- Python système = 3.9 (inutilisable). Utiliser `.venv` (3.12) : `uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python -e ".[dev]"`.
  Toujours invoquer `.venv/bin/python` / `.venv/bin/pytest`.
- Outils système présents : `osmium`, GDAL (`gdalinfo`, `ogr2ogr`). Pas de clé CDS (`~/.cdsapirc` absent).
- Disque : ~44 Go libres. **Ne jamais lancer `--all` / miroir complet (24 Go) ni télécharger l'Europe OSM entière (30 Go).**
  Tests sur petits périmètres : datasets Eurostat ciblés, extrait Geofabrik Luxembourg/Malte, rasters synthétiques.
- Réseau autorisé pour : API Eurostat, GISCO, Geofabrik (petits extraits). Rate-limit Eurostat ≤ 2 req/s.

## Tests et qualité
- `tests/` en pytest (`asyncio_mode=auto`). Tests unitaires sans réseau par défaut ; tests réseau marqués `@pytest.mark.network`.
- `.venv/bin/ruff check .` doit passer. Pas de tests qui dépendent d'un miroir complet.
- Vérifier qu'un modèle 27B peut suivre : descriptions de tools courtes, qui nomment le tool suivant attendu (§8.5).

## Git
- Commits atomiques en français, impératif : "Ajoute le référentiel geo GISCO". Pas de fichiers de données
  (`mirror/`, `eurostat.db`, `work/`) dans git (.gitignore). Ne pas committer `.venv`.
