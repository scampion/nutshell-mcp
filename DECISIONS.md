# Décisions d'implémentation (ADR courts)

Écarts et choix non tranchés par `architecture-spec-mcp-territorial.md`.
Format : contexte → décision → conséquence.

---

## ADR-L1-1. URLs GISCO retenues

**Contexte.** La spec (§4) dit « construire le référentiel depuis GISCO » sans
nommer de fichier. Le service de distribution publie 7 millésimes NUTS, 5
résolutions, 3 projections et 6 formats.

**Décision.** Vérifiées par requête réelle avant codage, les URLs retenues sont :

| usage | URL |
|---|---|
| NUTS, niveaux 0-3 | `https://gisco-services.ec.europa.eu/distribution/v2/nuts/geojson/NUTS_RG_{01M\|10M}_{2024\|2021}_4326_LEVL_{0..3}.geojson` |
| Villes Urban Audit | `…/v2/urau/geojson/URAU_RG_100K_{2024\|2021}_4326_CITIES.geojson` |
| Correspondance de millésimes | `https://ec.europa.eu/eurostat/documents/345175/629341/NUTS2021-NUTS2024.xlsx` |

- `RG` (region) et non `BN` (boundaries) : ce sont les polygones qui servent aux
  statistiques zonales et aux jointures spatiales.
- EPSG **4326** partout, pour que `exactextract`, GDAL et DuckDB spatial lisent
  les fichiers sans reprojection préalable et que les rasters ERA5-Land
  (également en 4326) se recouvrent directement.
- `01M` pour l'ingestion (§4 : « 1:1M pour les statistiques zonales »), `10M`
  pour l'affichage. Les attributs (codes, noms, parents) sont identiques dans
  les deux : la table `geo` est construite depuis le 10M, dix fois plus léger.
- Urban Audit n'existe qu'en `100K` : la résolution est ignorée pour `CITY`.

**Conséquence.** 18 fichiers, 173 Mo sur disque — sous le budget de 500 Mo
annoncé au §10.

---

## ADR-L1-2. Géométries conservées en GeoJSON brut

**Contexte.** La spec autorise « GeoJSON/GeoParquet » (§4).

**Décision.** Les fichiers GISCO sont stockés tels quels, sans conversion.

**Conséquence.** `exactextract` (lot 3) les lit via GDAL, l'extension spatiale de
DuckDB via `ST_Read` (lot 2), `ogr2ogr` sans option. Une conversion en
GeoParquet aurait ajouté une dépendance spatiale au socle, que le serveur doit
pouvoir démarrer sans (CLAUDE.md). Le nom de la propriété portant le code de
zone est exposé par `geo.geometry_code_property(level)` : `NUTS_ID` pour les
NUTS, `URAU_CODE` pour les villes.

---

## ADR-L1-3. La table `geo` ne porte que le millésime courant

**Contexte.** La spec impose `geo(geo_code PK, …)` **et** la gestion de deux
millésimes (§4). Les deux sont incompatibles : `FRK2` existe en 2021 et en 2024.

**Décision.** `geo` contient le seul millésime courant (NUTS 2024 + villes 2024),
`geo_code` reste clé primaire. L'historique vit dans `nuts_changes`, qui contient
**tous** les codes 2021 (la colonne `old_code` couvre l'intégralité du millésime
précédent, y compris les codes inchangés).

**Conséquence.** `list_zones` ne montre jamais de région retirée. La projection
d'un indicateur déclaré `nuts_vintage: 2021` interroge `nuts_changes`, pas `geo`.
Les géométries 2021 restent téléchargées et accessibles par
`geo.geometry_path(level, vintage=2021)` pour les pipelines qui en auraient
besoin.

---

## ADR-L1-4. Bijectivité dérivée de la colonne « Change » du classeur Eurostat

**Contexte.** La spec parle d'une « table de correspondance GISCO entre
millésimes ». Le service de distribution GISCO n'en publie pas ; le classeur
officiel `NUTS2021-NUTS2024.xlsx` (feuille « NUTS2021- NUTS2024 ») en tient lieu.

**Décision.** Le classeur est lu avec la stdlib (`zipfile` + `ElementTree`) — un
XLSX est un zip de XML, aucune dépendance Excel n'est ajoutée. Colonnes
utilisées : C (code 2021), D (code 2024), H (nature du changement).
`bijective = 1` si les deux codes sont renseignés **et** que le changement est
vide, `Code change` ou `Name change`. Tout le reste (`Boundary shift`, `Merged`,
`Split`, `art. 5(2a)`, `New region`) donne `bijective = 0`.

**Conséquence.** 1 647 correspondances chargées, dont 83 non bijectives. La
projection ne recode que les 16 vrais changements de code (les identités n'ont
pas besoin d'être recodées) et marque `quality = 'recoded'`. Les zones 2021
supprimées disparaissent de la table canonique — elles n'ont pas d'équivalent
2024 et une valeur reportée serait fausse.

---

## ADR-L1-5. Villes Urban Audit incluses dès le lot 1

**Contexte.** Le lead autorisait un TODO si les villes posaient friction.

**Décision.** Elles sont ingérées : le fichier existe, pèse 13 Mo, et porte déjà
`NUTS3_2024`, ce qui donne `parent_code` sans jointure spatiale.

**Conséquence.** 739 villes de niveau `CITY` dans `geo`, immédiatement utilisables
par les indicateurs OSM et Copernicus qui déclarent ce niveau. `list_zones("CITY",
parent="FR")` fonctionne (le filtre parent accepte un préfixe de code NUTS).

---

## ADR-L1-6. `geometry_path` prend le niveau en premier argument

**Contexte.** L'interface demandée était `geometry_path(vintage, resolution)`.

**Décision.** La signature est `geometry_path(level, vintage=2024,
resolution="01M")`. GISCO publie un fichier **par niveau** : sans le niveau, la
fonction ne peut pas désigner un fichier.

**Conséquence.** Les pipelines appellent `geo.geometry_path("NUTS3")` pour le cas
courant.

---

## ADR-L1-7. `ingested_at` en timestamp UTC naïf

**Contexte.** Le schéma §6.1 dit « timestamp ».

**Décision.** `pa.timestamp("us")` sans fuseau, valeur en UTC.

**Conséquence.** DuckDB exige le module `pytz` pour convertir un `TIMESTAMP WITH
TIME ZONE` vers Python ; `pytz` n'est pas dans les dépendances et n'a pas à y
entrer pour une colonne d'horodatage interne. La convention UTC est documentée
dans le module.

---

## ADR-L1-8. Le registre est du code, pas de la donnée

**Contexte.** `NUTSHELL_DATA_DIR` déplace tout l'état sur disque.

**Décision.** `registry/*.yaml` ne suit pas `NUTSHELL_DATA_DIR` : il est
versionné dans le dépôt, comme le code. Une variable dédiée,
`NUTSHELL_REGISTRY_DIR`, permet de le déplacer (utilisée par les tests).

**Conséquence.** `rsync` du répertoire `mirror/` + `eurostat.db` réplique bien
l'état vivant (§9), et un déploiement met à jour le registre par un `git pull`.

---

## ADR-L1-9. Le registre se re-matérialise tout seul au service

**Contexte.** La spec ne dit pas quand `registry` est écrit dans SQLite.

**Décision.** `registry.ensure_materialized()` compare une empreinte
(nom + mtime + taille de chaque YAML) à celle enregistrée et re-matérialise si
elle a changé. Elle est appelée par `search_indicators` et `get_indicators`.

**Conséquence.** Ajouter un indicateur = déposer un YAML ; il est visible au tool
suivant, sans relancer de sync. Un registre devenu invalide ne casse pas le
serveur : la matérialisation échoue silencieusement et l'ancienne version
continue d'être servie (la validation bruyante, c'est `registry validate` en CI).

---

## ADR-L1-10. Jeu de règles `ruff` figé dans `pyproject.toml`

**Contexte.** `ruff check .` doit passer (CLAUDE.md), mais le jeu de règles par
défaut varie d'une version de ruff à l'autre.

**Décision.** `select = ["E", "F", "W", "I", "UP", "B", "C4", "SIM", "RUF"]`.
`BLE` (blind except) est délibérément exclu : §7 impose qu'un échec d'indicateur
n'interrompe pas le lot, ce qui se traduit par des `except Exception` assumés
dans chaque pipeline. `RUF001-003` sont exclus (apostrophes typographiques des
messages français), `B008` aussi (idiome `Field(...)` de pydantic).

---

## ADR-L1-11. Sans filtre temporel, les 3 dernières périodes sont globales

**Contexte.** §8.3 : « sans filtre temporel, seules les 3 dernières périodes sont
renvoyées ». Ambigu : 3 par zone, par indicateur, ou en tout ?

**Décision.** Les 3 périodes les plus récentes **de l'ensemble du résultat**.

**Conséquence.** Le tableau reste rectangulaire et comparable entre zones — ce
qui est le point du pivot. Une zone dont la dernière valeur est plus ancienne
apparaît avec des cellules vides, ce qui est une information utile, plutôt
qu'avec des périodes décalées qui rendraient la lecture trompeuse.

---

## ADR-L1-12. La ligne de provenance détaille les dates quand elles diffèrent

**Contexte.** §8.3 montre `[Source : eurostat (21.08.2026), copernicus (v2023),
osm (extrait 2026-08)]` sans dire quoi faire de deux indicateurs Eurostat de
dates différentes. Une première version ne gardait que la date la plus récente
par source ; la revue du lot 1 a jugé que cela masquait une donnée plus ancienne
et contredisait l'objectif de traçabilité (§1).

**Décision (révisée).** Une entrée par source. Si tous les indicateurs d'une
source partagent la même `source_date`, forme courte `eurostat (21.08.2026)` ;
sinon le détail par indicateur : `eurostat (gdp_per_capita 10.02.2026,
unemployment_rate 30.06.2026)`. De même, un indicateur demandé mais sans valeur
sur la fenêtre conserve sa colonne (vide) et est signalé par une ligne
`[Sans valeur sur la fenêtre demandée : … (données disponibles 2014–2025)]`.

**Conséquence.** La ligne reste courte dans le cas courant (P5) et la traçabilité
par valeur est garantie dans le cas mixte ; le modèle ne peut plus confondre
« indicateur absent » et « indicateur sans valeur ».

---

## ADR-L1-13. `quality` non vide s'affiche entre crochets dans la cellule

**Contexte.** La table canonique porte `quality` (flag Eurostat, `recoded`,
`osm_completeness_unknown`…), mais la sortie pivotée n'a pas de colonne pour lui.

**Décision.** La valeur est suffixée : `66800 [p]`, `41 [osm_completeness_unknown]`.

**Conséquence.** Le modèle voit la réserve au moment où il lit le chiffre, sans
colonne supplémentaire ni ligne de note à corréler. Une cellule sans crochets est
une valeur sans réserve.

---

## ADR-L1-14. `--project-only` vit dans `mirror.py`, pas dans `sync.py`

**Contexte.** Le lead demandait « une commande pour projeter sans re-télécharger ».

**Décision.** `python -m nutshell_mcp.mirror --project-only [--datasets a,b]`.

**Conséquence.** `sync.py` garde une interface unique et orthogonale
(`--source`), tandis que `mirror.py` reste l'outil bas niveau du miroir natif,
conformément à sa conservation demandée « comme aujourd'hui ».

---

## ADR-L1-15. Les instantanés sont répétés sur chaque période de la zone

**Contexte.** §6.1 date les indicateurs `SNAPSHOT` (comptages OSM) du mois de
l'extrait (`2026-08`) alors que les autres sont annuels/trimestriels. Dans le
pivot de `get_indicators`, la jointure recherchée par l'agent se retrouvait
alors sur deux lignes par zone (`2026-08` pour OSM, `2023` pour le reste) — peu
lisible pour un 27B, et l'instantané sortait de toute fenêtre `time_from/time_to`.

**Décision (validée le 23 août 2026).** Un instantané décrit l'état courant, pas
une période : sa dernière valeur est **répétée sur chaque ligne de période de la
zone** avec le marqueur `[snapshot AAAA-MM]` ; il n'est pas filtré par la fenêtre
temporelle et ne compte pas dans les « 3 dernières périodes ». Une ligne
`[Instantanés, état courant répété sur chaque période : hospitals_count (2026-08,
osm_completeness_unknown)]` rappelle la date et la qualité. Une zone qui n'a que
des instantanés garde sa ligne datée de l'instantané, cellules avec leur qualité.

**Conséquence.** Une seule ligne par zone × période porte les trois sources ; la
date et la qualité de l'instantané restent tracées dans la note, pas dans chaque
cellule (P5, cellules courtes).

---

## ADR-L1-16. Quotas du serveur de démo, en mémoire et par identité HTTP

**Contexte.** Le serveur public (`nutshell.arcamens.ai`) est ouvert sans clé.
La spec ne prévoit ni authentification ni quota. Il faut protéger le service et
orienter l'usage intensif vers l'offre opérationnelle, sans gêner l'auto-hébergement.

**Décision.** Module `quota.py`, inactif sauf `NUTSHELL_QUOTA=1` en transport
HTTP. Un middleware ASGI pose l'identité du client dans une `ContextVar` (le SDK
MCP 2.x la propage jusqu'au handler du tool). L'identité est une clé d'API
(`api_keys.tsv`, tiers `free`/`pro`) ou, à défaut, l'IP. Les sorties des
connecteurs claude.ai (`NUTSHELL_SHARED_NETS`) partagent un compteur, sinon
tous leurs utilisateurs seraient bloqués ensemble. Défauts : 30 appels/min,
100/jour en anonyme, 500 avec une clé gratuite, 5000 pour le réseau partagé ;
`get_indicators` et `query_data` comptent double. Un refus est une **sortie de
tool en texte** (Annexe A), pas un HTTP 429 : le modèle relaie à l'utilisateur
les liens `#contact` et `#self-host`. Le journal d'appels enregistre l'identité
pseudonymisée (`client=ip:<sha256 tronqué>`) pour calibrer les seuils.

**Conséquence.** Les compteurs vivent en mémoire d'un seul processus : un
redémarrage les remet à zéro, et plusieurs workers ne partagent pas leurs
compteurs. C'est acceptable pour une démo mono-processus ; un backend partagé
(SQLite, Redis) ne sera utile que si le service passe à plusieurs workers.
Derrière un proxy, `NUTSHELL_PROXY_HOPS` doit valoir le nombre de proxys de
confiance, sinon tous les clients ont l'IP du proxy.

---

## ADR-L1-17. Playground navigateur : le visiteur apporte son modèle

**Contexte.** La landing page montre des exemples figés. Pour essayer sans
installer de client MCP, le visiteur doit pouvoir poser une question depuis la
page. La spec ne prévoit pas de client web, et le serveur de démo ne doit pas
payer l'inférence.

**Décision.** `site/app.js`, sans dépendance ni build : le navigateur est lui-même
le client MCP (streamable HTTP : `initialize`, `tools/list`, `tools/call`, réponses
JSON ou SSE) et mène la boucle de tool calling avec le fournisseur choisi par le
visiteur et **sa** clé. Deux formats couvrent les principaux fournisseurs :
Messages API d'Anthropic (en-tête `anthropic-dangerous-direct-browser-access`) et
chat completions compatible OpenAI (OpenAI, Google Gemini, Mistral, OpenRouter,
serveur local Ollama/LM Studio). OpenRouter est proposé par défaut : il accepte les
appels navigateur, fournit une clé par OAuth PKCE sans copier-coller, et donne
accès à des modèles ouverts de ~27B, la cible du projet (§8.5). Appels HTTP bruts
plutôt que SDK : une page statique multi-fournisseurs sans build.

La clé reste en `sessionStorage` (onglet courant) et ne part qu'au fournisseur.
Une CSP stricte (`script-src 'self'`, `connect-src` limité aux fournisseurs, au
serveur et à `localhost`) limite l'exfiltration en cas d'injection ; les réponses
du modèle sont échappées avant un rendu Markdown minimal.

Les appels MCP partent de l'IP du visiteur : le quota anonyme par IP
(ADR-L1-16) s'applique tel quel. En production, la page et `/mcp` partagent
l'origine `nutshell.arcamens.ai`, sans CORS. Pour les autres cas (dev local,
instance auto-hébergée), `NUTSHELL_CORS_ORIGINS` active un middleware CORS qui
expose `Mcp-Session-Id`, et ajoute ces origines à la protection DNS rebinding.

**Conséquence.** Un fournisseur qui refuse le CORS échoue avec un message
renvoyant vers OpenRouter. La qualité de la démo dépend du modèle choisi ; c'est
voulu, puisqu'elle montre aussi le comportement d'un petit modèle.

---

## Lot 2 — OSM

### ADR-L2-1. Périmètre configuré par variable d'environnement, défaut Luxembourg seul

**Contexte.** §7.3 laisse le choix du périmètre (« Europe entière ~30 Go, ou par
pays ») sans mécanisme de configuration. Deux options envisageables : variable
d'environnement, ou fichier `osm_extracts.txt`.

**Décision.** `NUTSHELL_OSM_EXTRACTS="europe/luxembourg,europe/belgium"`
(chemins Geofabrik complets, séparés par des virgules), sur le modèle des
autres variables du socle (`NUTSHELL_DATA_DIR`, `NUTSHELL_REGISTRY_DIR`) plutôt
qu'un fichier dédié — un pipeline de plus qui lirait son propre fichier de
config aurait cassé l'uniformité « tout se configure par variable
d'environnement » déjà en place. Défaut si absente : `("europe/luxembourg",)`
seul — jamais un extrait continental par défaut, conformément à la contrainte
d'environnement (ne jamais déclencher un gros téléchargement par accident).

**Conséquence.** `ingest_osm.configured_extracts()` est une fonction pure,
testable sans effet de bord. Étendre le périmètre à un troisième pays ne
touche aucun code, seulement la variable d'environnement (ou le cron qui
l'exporte).

### ADR-L2-2. Signal de fraîcheur en deux temps : md5 sidecar puis timestamp d'en-tête

**Contexte.** Le spike (A1) établit que le timestamp fiable est celui embarqué
dans l'en-tête du `.pbf` (`osmium fileinfo -e -g header.option.timestamp`), pas
le `Last-Modified` HTTP. Mais ce timestamp n'est lisible qu'une fois le fichier
téléchargé — potentiellement des centaines de Mo pour rien si l'extrait n'a pas
changé.

**Décision.** Le sidecar `.md5` (quelques octets) est récupéré et comparé à
l'état local *avant* tout téléchargement du `.pbf`. Un md5 inchangé implique un
contenu inchangé, donc un timestamp d'en-tête inchangé — le téléchargement et
le retraitement (filtrage, jointure) sont alors sautés, et le GeoParquet POI
déjà présent sur disque est réutilisé tel quel pour l'union multi-extraits.

**Conséquence.** Rejouer `sync --source osm` sans changement côté Geofabrik ne
retélécharge jamais l'extrait (vérifié empiriquement sur le Luxembourg réel,
voir rapport de mission). Économie substantielle pour la Belgique (~600 Mo) à
chaque cron mensuel où rien n'a changé.

### ADR-L2-3. Clip transfrontalier par préfixe pays du `geo_code`

**Contexte.** Piège n°3 du spike : un extrait pays Geofabrik déborde toujours
un peu sur les pays voisins (POI géométriquement situés en France/Belgique/
Allemagne dans l'extrait Luxembourg). Sans traitement, ingérer deux extraits
limitrophes (LU + BE) compterait deux fois les POI proches de la frontière.

**Décision.** Un POI d'un extrait n'est retenu que s'il tombe dans une zone dont
le préfixe pays du `geo_code` (2 premiers caractères, convention NUTS/Eurostat)
correspond au pays déclaré de l'extrait (`ingest_osm.GEOFABRIK_COUNTRY`, indexé
par nom court d'extrait). Un POI qui déborde géométriquement chez le voisin
est donc écarté par l'extrait d'origine, et n'est compté par l'extrait voisin
que si ce dernier le possède réellement dans son propre fichier — sinon il est
perdu, ce qui est le comportement correct (mieux vaut un POI en bordure non
compté qu'un double comptage systématique).

**Conséquence.** La convention NUTS est utilisée plutôt que l'ISO 3166-1 : la
Grèce (`EL`, pas `GR`) et le Royaume-Uni (`UK`, pas `GB`) auraient sinon cassé
silencieusement le clip pour ces deux pays si l'extension venait à les couvrir.
`GEOFABRIK_COUNTRY` documente ce choix en commentaire.

### ADR-L2-4. Zéro explicite pour toute zone du périmètre sans POI

**Contexte.** §7.3 demande d'inclure les zones à 0 POI, distinctes des zones hors
périmètre.

**Décision.** « Périmètre » = union des pays couverts par au moins un extrait
configuré (préfixe `geo_code`). Toute zone de ce périmètre reçoit une ligne
(valeur 0 si aucun POI ne correspond) ; toute zone d'un pays non couvert
n'apparaît pas du tout dans la partition.

**Conséquence.** `get_indicators(["hospitals_count"], ["LU000", "BE100"])`
renvoie une valeur pour les deux même si l'une vaut 0, alors qu'une zone
allemande n'apparaît jamais tant qu'aucun extrait allemand n'est configuré —
la distinction entre « aucun hôpital » et « donnée non collectée » reste
lisible par le modèle.

### ADR-L2-5. Une seule partition par indicateur, union de tous les extraits

**Contexte.** `indicators.write_partition` remplace toujours la partition
entière (pas d'append). Avec plusieurs extraits, il faut donc décider où vit
l'agrégation multi-extraits.

**Décision.** `ingest_osm.sync()` calcule les comptages de **tous** les extraits
configurés (en relisant le GeoParquet des extraits inchangés plutôt qu'en les
retraiter) avant un unique appel `write_partition` par indicateur. `time` et
`source_date` du batch entier prennent le mois le plus récent parmi les
extraits utilisés (`f"extrait {AAAA-MM}"`) — le schéma canonique ne porte
qu'une `source_date` par écriture, pas une par ligne.

**Conséquence.** La partition d'un indicateur OSM est toujours cohérente et
complète après un `sync`, jamais un mélange de deux écritures partielles. Un
indicateur n'est re-matérialisé que si au moins un extrait a changé (ou
`--full`), sinon il est rapporté `unchanged` sans toucher au disque.

### ADR-L2-6. `railway=halt` exclu de `train_stations_count`

**Contexte.** §7.3 ne tranche pas si les arrêts sans bâtiment voyageurs
(`railway=halt`) comptent comme des « gares ».

**Décision.** Exclus. `train_stations_count` ne couvre que `railway=station`.

**Conséquence.** Le nombre reste comparable à travers l'Europe (le partage
gare/halte varie fortement par pays et n'est pas toujours cartographié de
façon cohérente) et concorde avec la valeur de plausibilité mesurée sur le
Luxembourg réel (~65). Un futur indicateur `railway_stops_count` (station +
halt) pourrait être ajouté comme fichier YAML séparé sans toucher au pipeline.

### ADR-L2-7. `geometry: [node, way, relation]` pour les trois indicateurs

**Contexte.** Le registre initial ne déclarait que `[node, way]` pour les trois
indicateurs OSM. Le spike a mesuré, sur le Luxembourg réel, que les hôpitaux
sont 13 way + 2 relation (0 node), et les écoles 352 way + 34 node + 7
relation : omettre `relation` sous-compte silencieusement.

**Décision.** Les trois YAML déclarent `geometry: [node, way, relation]`, y
compris `train_stations_count` (65 node, 0 way/relation sur le Luxembourg) par
précaution pour d'autres pays où de grandes gares peuvent être cartographiées
en relation.

**Conséquence.** Aucun coût mesurable (une expression `osmium tags-filter` de
plus par catégorie) ; couverture correcte dès le premier extrait ingéré.

### ADR-L2-8. Doublons node/way non dédupliqués (limite connue, assumée)

**Contexte.** Piège n°4 du spike : un hôpital peut être cartographié à la fois
comme nœud isolé et comme empreinte de bâtiment ; aucun tag OSM standard ne
relie les deux représentations.

**Décision.** Aucune déduplication. Documenté en commentaire de code
(`ingest_osm.py`, docstring de module) et dans le README.

**Conséquence.** Cohérent avec `quality = "osm_completeness_unknown"`, déjà
systématique sur tous les indicateurs OSM (§7.3) : le modèle est prévenu que
ces comptages sont approximatifs, sans prétendre à une précision que la donnée
source ne permet pas de garantir à ce stade.

### ADR-L2-9. `sync_pipeline` : duck-typing plutôt qu'`isinstance` sur `SyncReport`

**Contexte.** Bug du socle découvert en validant réellement `python -m
nutshell_mcp.sync --source osm` (le pipeline OSM est le premier module
concret importé dynamiquement par `sync_pipeline`, jusqu'ici toujours en
`ImportError`) : la commande matérialisait correctement les partitions mais
affichait `[osm] 0 mis à jour, 0 inchangés, 0 échecs` — un rapport vide alors
que le travail avait bien eu lieu. Cause : `python -m nutshell_mcp.sync`
exécute `sync.py` comme `__main__` ; `sync_pipeline` y appelle
`importlib.import_module("nutshell_mcp.ingest_osm")`, dont l'import relatif
`from .sync import SyncReport` réimporte le **même fichier** sous son nom réel
`nutshell_mcp.sync`. Le module `sync.py` est donc exécuté deux fois sous deux
identités différentes, produisant deux classes `SyncReport` distinctes en
mémoire : `isinstance(result, SyncReport)` compare alors deux classes
non-identiques et échoue silencieusement, même quand `result` est un rapport
parfaitement valide.

**Décision.** Remplacer le contrôle par duck-typing (`hasattr(result,
"render")` et `hasattr(result, "ok")`) plutôt que par identité de classe.

**Conséquence.** `python -m nutshell_mcp.sync --source osm` affiche désormais
le vrai rapport. Un pipeline dont `sync()` ne respecte pas le contrat (retourne
`None` ou un objet sans `render`/`ok`) tombe toujours sur le `report` local
vide plutôt que de faire planter l'orchestration — comportement inchangé pour
ce cas. Ce piège concerne potentiellement aussi le futur `ingest_cds.py`
(lot 3) : la correction est faite une fois dans `sync_pipeline`, pas à
dupliquer par pipeline.

## Lot 3 — Copernicus

### ADR-L3-1. Trois fournisseurs de rasters derrière une interface unique

**Contexte.** La spec (§7.2) ne connaît qu'un chemin d'acquisition : `cdsapi`.
Or la machine de développement n'a pas de clé CDS, et le Copernicus Land
Monitoring Service (produit `imperviousness_share`) exige une authentification
qu'aucune API publique ne contourne — le spike a vérifié que le catalogue STAC
du Copernicus Data Space est navigable sans jeton mais que **le téléchargement
des assets ne l'est pas**, et qu'aucune collection « imperviousness » n'y
figure.

**Décision.** L'acquisition passe par un fournisseur, `fetch(spec, year) ->
Raster`. `NUTSHELL_CDS_PROVIDER` l'impose pour tout le lot ; sans consigne, il
est **déduit du produit déclaré au registre** : `reanalysis-*` va vers `cds` si
`~/.cdsapirc` existe et vers `arco` sinon, tout autre produit vers `local` —
`cds` comme `arco` ne servent que des réanalyses ERA5, et router un produit CLMS
vers eux ne produirait qu'un « variable absente du store » incompréhensible.
Le choix est mentionné dans le rapport de sync. Tout l'aval — recalage,
statistiques zonales, conversion d'unité, écriture, purge — est commun, et un
même lot peut mêler plusieurs fournisseurs.

**Conséquence.** Le pipeline est complet et testable sans clé ni réseau, et la
voie officielle CDS n'est pas un TODO : elle est implémentée, testée par mock
(construction de la requête, reprise sur `request_id`, échec de requête) et
prête à servir dès qu'une clé est configurée. `Raster` porte, en plus du chemin,
la `source_date`, l'unité de la source, la qualité de base et la valeur maximale
observée — la signature de la spec (« → chemin ») aurait obligé chaque
fournisseur à écrire ces métadonnées ailleurs.

### ADR-L3-2. ARCO-ERA5 échantillonné, marqué `sampled`

**Contexte.** `gs://gcp-public-data-arco-era5/ar/full_37-1h-0p25deg-chunk-1.zarr-v3`
est lisible **anonymement** et couvre 1940 → aujourd'hui. Mais il est chunké
`(1, 721, 1440)` : un chunk = une grille mondiale pour **un** pas de temps
horaire. Un sous-ensemble spatial ne réduit donc pas le nombre de requêtes
réseau (3 à 9 s chacune) ; une moyenne JJA horaire exacte (2208 pas) demande
1 à 2 h par indicateur et par année.

Les stores 6-horaires du même bucket ont été inspectés pour voir s'ils faisaient
mieux : `1959-2022-6h-1440x721.zarr` s'arrête au **31 décembre 2021**, ne
contient pas `skin_temperature`, et est chunké exactement pareil — un chunk par
pas de temps. Aucun gain, et une couverture temporelle qui exclut les années
récentes.

**Décision.** Le store horaire complet est conservé, et le fournisseur
**échantillonne** `NUTSHELL_ARCO_SAMPLES_PER_MONTH` pas de temps par mois
(défaut 4), aux heures synoptiques 00/06/12/18 réparties sur des jours espacés.
Les quatre heures sont systématiquement représentées : un échantillonnage à midi
seul surestimerait la moyenne de plusieurs degrés. Chaque valeur produite porte
`quality = "sampled"`.

**Conséquence.** Un été coûte ~1 min au lieu de 1-2 h. Les valeurs sont des
estimations : LU00 ressort à 18,98 °C pour JJA 2023 (le spike, en ne lisant que
des pas de temps de midi, trouvait 20,41 °C — l'écart est exactement le biais
diurne évité). Le flag remonte jusqu'à l'utilisateur du tool, entre crochets,
comme prévu par l'ADR-L1-13 : le modèle voit la réserve au moment où il lit le
chiffre. Le jour où une clé CDS est configurée, le fournisseur `cds` produit la
même partition sans ce flag.

### ADR-L3-3. `reanalysis-era5-land-monthly-means` plutôt que le produit horaire

**Contexte.** Le registre déclare `product: reanalysis-era5-land`. Le produit
horaire demanderait ~2208 pas de temps par été et par zone d'emprise.

**Décision.** Le fournisseur `cds` interroge
`reanalysis-era5-land-monthly-means` avec
`product_type = monthly_averaged_reanalysis` : 3 valeurs mensuelles au lieu de
2208 valeurs horaires pour un `temporal_agg` JJA. Le champ `product` du registre
reste la **famille** de produit, pas le nom exact du dataset CDS.

**Conséquence.** Requête légère, file d'attente plus courte, et `temporal_agg.stat`
s'applique aux moyennes mensuelles — ce qui est la définition attendue d'une
« moyenne estivale » et non une moyenne pondérée par le nombre d'heures. Pour un
`stat` autre que `mean`, la nuance compte (le maximum de trois moyennes
mensuelles n'est pas le maximum horaire de l'été) : c'est documenté dans le
module.

### ADR-L3-4. `imperviousness_share` passe par le fournisseur `local`

**Contexte.** Aucune voie automatisable sans authentification n'a été trouvée
pour les couches haute résolution CLMS.

**Décision.** Le produit est ingéré depuis un GeoTIFF EPSG:4326 déposé sous
`NUTSHELL_RASTER_DIR/{indicateur}/{année}.tif`. En son absence, l'erreur nomme
le chemin exact attendu, l'URL de téléchargement CLMS et la variable qui déplace
la racine ; un CRS autre que 4326 produit la ligne `gdalwarp` à exécuter.
`temporal_agg.months: []` signifie « pas d'agrégation temporelle », et `time`
vaut le millésime du raster.

**Conséquence.** L'indicateur n'est pas matérialisable en CI, mais il l'est en
une commande dès que l'utilisateur a téléchargé le fichier — sans code
supplémentaire. Aucune reprojection n'est faite par le pipeline : reprojeter une
couche CLMS à 10 m sur toute l'Europe est un travail de plusieurs dizaines de Go
qui n'a pas sa place dans un `sync` (§10 : l'espace de travail est budgété pour
des rasters ERA5, pas pour du 10 m continental).

### ADR-L3-5. Couverture partielle mesurée par l'aire de la géométrie

**Contexte.** §6.1 prévoit `quality = 'partial_coverage'`. `exactextract`
renvoie bien la somme des fractions de mailles couvertes (`count`), mais
seulement pour les mailles **valides et dans l'emprise du raster** : ce nombre
seul ne dit pas si la zone débordait.

**Décision.** Le dénominateur est calculé côté pipeline : aire planaire de la
géométrie GeoJSON (formule des lacets, trous déduits, ~20 lignes de stdlib)
divisée par l'aire d'une maille. En deçà de 99,9 % du ratio, la valeur est
marquée `partial_coverage`. Une zone entièrement hors emprise (valeur nulle ou
NaN) est simplement omise de la partition.

**Conséquence.** Le contrôle couvre les deux causes réelles — maille sans donnée
(ERA5-Land sur la mer, CLMS hors couverture) et zone débordant l'emprise — sans
ajouter shapely ni geopandas aux dépendances. `partial_coverage` **remplace**
la qualité de base plutôt que de s'y ajouter : une cellule ne porte qu'un flag,
conformément à l'ADR-L1-13, et la réserve la plus forte gagne.

### ADR-L3-6. `exactextract` reçoit des Features GeoJSON, pas un chemin

**Contexte.** Le spike (B3) a montré que `exact_extract(raster, chemin_vecteur,
ops)` exige GDAL/`ogr`, `fiona` ou `geopandas` côté Python.

**Décision.** Le pipeline lit lui-même le GeoJSON GISCO (stdlib `json`) et passe
la **liste de dicts Feature** à `exact_extract`. L'extra `copernicus` perd
`geopandas` et gagne `gcsfs` + `zarr` (fournisseur `arco`).

**Conséquence.** L'extra reste raisonnable, et le filtrage du périmètre
(`NUTSHELL_CDS_COUNTRIES` sur `CNTR_CODE`, à défaut le préfixe du code de zone)
se fait sur les mêmes objets, sans seconde lecture.

### ADR-L3-7. Une partition Copernicus porte une seule `source_date`

**Contexte.** `indicators.write_partition` réécrit la partition d'un bloc avec
une `source_date` unique, alors que le pipeline accumule les années.

**Décision.** Les années déjà matérialisées sont relues et fusionnées avec les
nouvelles, et la partition prend la `source_date` du dernier raster acquis.

**Conséquence.** Une valeur de 2021 réécrite en même temps qu'une valeur de 2024
affiche la version du produit la plus récente. C'est cohérent avec l'ADR-L1-12
(la provenance agrège par source, pas par ligne) et sans effet sur le contrat de
§6.1, qui ne demande pas une date par ligne. Une `source_date` par période
exigerait de changer la signature de `write_partition` — hors périmètre du lot.

### ADR-L3-8. `python -m nutshell_mcp.sync` délègue au module canonique

**Contexte (bug réel, découvert à la première validation).** Lancé par
`python -m nutshell_mcp.sync`, le fichier est chargé sous le nom `__main__` ;
`ingest_cds` faisant `from .sync import SyncReport`, Python importait le module
une **seconde** fois sous son vrai nom, avec une classe `SyncReport` distincte.
Le `isinstance(result, SyncReport)` de `sync_pipeline` échouait, et le rapport
du pipeline était silencieusement remplacé par un rapport vide — les données
étaient pourtant bien écrites.

**Décision.** Le bloc `if __name__ == "__main__"` de `sync.py` réimporte
`nutshell_mcp.sync` et appelle son `main`.

**Conséquence.** Un seul objet module, une seule classe `SyncReport`, et le
piège est neutralisé pour les deux pipelines (lot 2 compris) sans toucher au
contrat documenté.

### ADR-L2-10. Export osmium limité aux clés du registre ; md5 relu après téléchargement

**Contexte.** Premier passage `NUTSHELL_OSM_EXTRACTS=europe` en production : 12
pays sur 42 échouaient dans `ST_Read` (« duplicate column name "fixme" »,
`ref:HU:om`, `phone:nl`…) — `osmium export` émet toutes les clés OSM en
propriétés GeoJSON et DuckDB, insensible à la casse, refuse un fichier où deux
clés ne diffèrent que par la casse. L'Allemagne échouait sur « md5 invalide » :
Geofabrik avait republié l'extrait pendant les ~4 Go de téléchargement, le
sidecar lu avant ne correspondait plus.

**Décision.** (1) `osmium export -c` avec `{"include_tags": [clés du registre]}` :
seules les clés réellement utilisées (`amenity`, `railway`, …) deviennent des
colonnes, en casse exacte. (2) En cas d'écart md5, le sidecar est relu une fois
après téléchargement ; si le fichier correspond à la nouvelle version, il est
accepté et c'est ce md5 qui est stocké — sinon c'est une corruption réelle et
le fichier est rejeté.

**Conséquence.** Le GeoParquet POI ne porte plus que `@type, @id, <clés>, geom`
— plus léger et stable ; un extrait republié en cours de route ne fait plus
échouer le lot. Rappel : la partition canonique est l'union des extraits
*configurés* lors du sync (ADR-L2-1) — lancer toujours avec le même
`NUTSHELL_OSM_EXTRACTS` (le mettre dans l'environnement du cron).
