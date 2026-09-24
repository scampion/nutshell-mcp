# Exemples de prompts — à quoi sert nutshell-mcp

🇫🇷 Français · [🇬🇧 English](examples.md) · [← README](../README.fr.md)

Chaque exemple est un prompt à coller dans n'importe quel client MCP connecté
au serveur (`https://nutshell.arcamens.ai/mcp`, ou votre propre instance). Le
modèle n'écrit jamais d'URL SDMX, de requête Overpass ni de requête CDS : il
choisit un tool, le serveur valide et répond depuis les données locales.

> Les sorties de tools sont en français. Le modèle répond dans la langue de
> votre prompt.

| # | Exemple | Tools enchaînés | Montre |
|---|---|---|---|
| 1 | [Où ouvrir une clinique gériatrique ?](#1-où-ouvrir-une-clinique-gériatrique-) | couche unifiée + grain natif | croisement Eurostat / OSM, flags qualité |
| 2 | [Comparer quatre régions](#2-comparer-quatre-régions) | 3 tools unifiés | un tableau, une colonne par indicateur |
| 3 | [Quand le registre s'arrête à NUTS2](#3-quand-le-registre-sarrête-à-nuts2) | couche unifiée → grain natif | repli sur NUTS3, erreurs actionnables |
| 4 | [Le tourisme, au-delà du registre](#4-le-tourisme-au-delà-du-registre) | grain natif Eurostat | le catalogue de 10 301 datasets |
| 5 | [Un nouvel indicateur en un fichier YAML](#5-un-nouvel-indicateur-en-un-fichier-yaml) | grain natif → registre | le modèle rédige le YAML |
| 6 | [Canicules et personnes âgées](#6-canicules-et-personnes-âgées) | couche unifiée, 3 lots | climat × vieillissement × hôpitaux (3 sources) |
| 7 | [Déménager avec de jeunes enfants](#7-déménager-avec-de-jeunes-enfants) | un seul appel `get_indicators` | 5 indicateurs issus de 3 sources |
| 8 | [Tourisme d'été, chaleur et train](#8-tourisme-dété-chaleur-et-train) | grain natif + couche unifiée | série mensuelle × chaleur × train (3 sources) |
| 9 | [Écoles et enfants](#9-écoles-et-enfants) | registre → grain natif | un dénominateur trouvé dans le catalogue |
| 10 | [Convergence Est-Ouest](#10-convergence-est-ouest) | un appel `get_indicators`, 11 ans | séries temporelles, ruptures, valeurs provisoires |

---

## 1. Où ouvrir une clinique gériatrique ?

La démo phare : une question de décision qu'aucune source ne traite seule.

```
Je dois choisir la région européenne où ouvrir une clinique gériatrique.
Compare les régions NUTS2 de la France, de la Belgique et du Luxembourg :
je veux celles où la population est la plus âgée, où l'offre hospitalière
(OSM) est la plus faible rapportée à la population, avec un PIB par habitant
correct. Donne-moi un top 5 justifié, avec un tableau des chiffres, et
précise la fiabilité de chaque source.
```

**Ce qui se passe.** Le modèle découvre les indicateurs avec
`search_indicators`, liste les zones de chaque pays avec `list_zones`, puis
appelle `get_indicators` en plusieurs lots (limite : 5 indicateurs et 100 zones
par appel). Insatisfait du *nombre* d'hôpitaux OSM (il compte des sites, pas des
lits), il descend au grain natif — `search_datasets` → `get_structure` →
`list_codes` → `query_data` — pour trouver les vrais *lits* d'hôpitaux par
région.

**Ce qu'un vrai run a produit** (extrait condensé — [réponse complète](results/01-geriatric-clinic.md)) :

| # | Région (NUTS2) | Dépendance 65+ | Lits / 100 000 hab. | PIB / hab. |
|---|---|---|---|---|
| 1 | Brabant wallon (BE31) | 33,4 % | 225,3 | 69 500 € |
| 2 | Poitou-Charentes (FRI3) | 47,3 % | 492,9 | 34 900 € |
| 3 | Vlaams-Brabant (BE24) | 32,5 % | 377,4 | 57 100 € |
| 4 | Basse-Normandie (FRD1) | 44,3 % | 557,2 | 34 600 € |
| 5 | Corse (FRM0) | 43,2 % | 552,0 | 37 500 € |

Le classement est un score composite (z-scores) calculé par le modèle
(pondérations : 40 % âge, 40 % offre, 20 % PIB), sur 39 zones.

**Pourquoi c'est convaincant.** L'intérêt n'est pas le tableau, mais ce que la
couche de provenance a permis au modèle d'en dire :

- Les lits belges portent tous le flag `d` (*définition différente*) : le modèle
  a averti que la comparaison FR/BE est *indicative, pas une mesure* — et que les
  rangs 1 et 3 sont belges.
- OSM renvoyait 0 hôpital pour les cinq départements d'outre-mer ; le modèle a
  repéré le défaut de complétude (`osm_completeness_unknown`) et les a exclus.
- Le Luxembourg ne renvoyait aucune donnée de lits ; le modèle a signalé *un
  trou de données, pas un mauvais score*, et l'a classé sur la seule démographie.
- Les valeurs `[p]` (provisoires) de 2025 ont été signalées comme telles.

La recommandation finale est nuancée en conséquence — c'est tout l'intérêt : un
modèle qui voit les flags qualité se comporte en analyste, pas en moteur de
recherche.

**Ce que le modèle a mal lu.** Il a averti que les données françaises portaient
sur la « géographie régionale d'avant 2016 » (Poitou-Charentes plutôt que
Nouvelle-Aquitaine) et recommandé de refaire l'analyse en NUTS 2021. C'est une
erreur de lecture : en NUTS 2021 comme en 2024, les régions françaises actuelles
forment le niveau NUTS1 (`FRI` Nouvelle-Aquitaine), tandis que le niveau NUTS2
conserve les anciennes régions (`FRI3` Poitou-Charentes). Les données étaient à
jour ; c'est le niveau NUTS2 qui ne correspond pas aux régions administratives
d'aujourd'hui.

---

## 2. Comparer quatre régions

Le prompt utile le plus court — une question, trois appels de tools.

```
Compare le chômage, l'âge médian et le PIB par habitant de l'Île-de-France,
de l'Oberbayern, de la Lombardie et de la Catalogne. Laquelle paraît la plus
dynamique, et pourquoi ?
```

**Vrai run** avec Qwen3.8-27B (prompt en anglais) —
[transcript complet](results/02-compare-regions.md). Le modèle a lancé en
parallèle 3 `search_indicators` et 4 `list_zones`, a relancé une fois
`list_zones` (`contains="Île-de-France"` ne trouve rien : le nom GISCO est
`Ile-de-France`, sans accent), puis 2 appels `get_indicators` :

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

Réponse (extrait, traduit) :

| Région | Chômage | Âge médian | PIB / hab. |
|---|---|---|---|
| **Oberbayern** (DE21) | **2,7 %** (2024) | 43,3 | **75 700 €** |
| **Île-de-France** (FR10) | 8,0 % (2024) | **38,2** | 69 500 € |
| **Lombardia** (ITC4) | 3,7 % (2024) | 48,1 | 50 400 € |
| **Cataluña** (ES51) | 8,9 % (2024) | 44,4 | 37 500 € |

> **L'Oberbayern est la plus dynamique *aujourd'hui* (richesse + plein
> emploi).** Si l'on entend le dynamisme comme un *potentiel de croissance*,
> c'est la population jeune de l'Île-de-France qui se distingue.

Sans filtre temporel, le serveur renvoie les 3 dernières périodes : le modèle
voit la tendance sans effort. Point de vigilance avec un modèle 27B : dans son
raisonnement, il a pris le flag `[d]` pour « non disponible » au lieu de
*définition différente* — demander explicitement la fiabilité (exemple 1) pousse
le modèle à vérifier.

---

## 3. Quand le registre s'arrête à NUTS2

```
Give me the gdp_capita of FR10 for the last 3 years, then the GDP per capita
of the NUTS3 zone FR101.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/03-nuts3-fallback.md).
Le modèle n'a jamais envoyé la faute de frappe : il a d'abord appelé
`search_indicators("GDP per capita")` et utilisé le bon identifiant,
`gdp_per_capita`. Le registre s'arrête à NUTS2 : il a obtenu FR10 via
`get_indicators`, puis est descendu au grain natif pour Paris :

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

Réponse : FR10 63 200 € → 66 800 € → 69 500 €, FR101 123 100 € → 125 300 € →
133 700 € (2022–2024, toutes provisoires).

**Erreurs actionnables.** Si le modèle avait envoyé la faute de frappe ou
demandé NUTS3 au registre, le serveur aurait répondu avec la correction
(vraies sorties du serveur) :

```
get_indicators(["gdp_capita"], ["FR10"])
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.

get_indicators(["gdp_per_capita"], ["FR101"])
'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).
```

Chaque erreur nomme l'action corrective et propose 3 suggestions au plus
(`difflib`) : c'est ce qui permet à un modèle de 27B de suivre des enchaînements
de tools sans humain.

> *Ce run a révélé une faiblesse depuis corrigée :* quatre appels à
> `search_datasets` (« gross domestic product regions », « GDP regions »…) ne
> renvoyaient rien, car la recherche exigeait chaque mot à l'identique. Elle
> accepte désormais les pluriels et, si aucun titre ne contient tous les mots,
> se replie sur « au moins un mot » en le signalant.

---

## 4. Le tourisme, au-delà du registre

Le registre contient un jeu d'indicateurs choisis ; le grain natif expose tout
Eurostat.

```
Find in Eurostat a dataset on nights spent at tourist accommodation by region.
Which five NUTS2 regions of Spain and Italy had the most nights in the latest
year available? Tell me which filters you used.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/04-tourism.md). Le
modèle a cherché dans le catalogue, comparé `tour_occ_nin2` et `tour_occ_nin2dc`
avec `get_structure`, listé les codes espagnols et italiens avec `list_codes`,
puis lancé un seul `query_data` sur les 40 régions :

| Rang | Région | Code | Année | Nuitées |
|---|---|---|---|---|
| 1 | Canarias | ES70 | 2024 | 99 488 821 |
| 2 | Cataluña | ES51 | 2024 | 88 670 191 |
| 3 | Andalucía | ES61 | 2024 | 77 308 673 |
| 4 | Veneto | ITH3 | 2025 | 74 157 131 |
| 5 | Illes Balears | ES53 | 2024 | 73 845 222 |

Il a indiqué ses filtres (`unit=NR`, `c_resid=TOTAL`, `nace_r2=I551-I553`,
`freq=A`) et signalé de lui-même que la dernière année est 2024 pour l'Espagne et
2025 pour l'Italie — puis vérifié qu'une comparaison à année égale donne le même
top 5. Tous les chiffres correspondent au miroir.

> *Un premier run a révélé une faiblesse du serveur, depuis corrigée* —
> [transcript](results/04-tourism-before-fix.md). `list_codes(contains="ES")`
> cherchait aussi dans les libellés (« Bruxell**es** », « H**es**sen »…), qui
> occupaient 36 des 60 lignes affichées ; ES63, ES64 et ES70 tombaient après la
> coupure. Le modèle a ignoré l'indication `… et 53 autres, affinez 'contains'`
> pour l'Espagne, a oublié les Canaries et donné un mauvais n° 1. Les codes qui
> commencent par le filtre passent désormais en premier, niveaux hauts d'abord.

---

## 5. Un nouvel indicateur en un fichier YAML

Ajouter un indicateur au registre ne demande aucun code — voir
[Ajouter un indicateur](../README.fr.md#ajouter-un-indicateur--un-fichier-yaml).
Le modèle peut même écrire le YAML :

```
I run a nutshell-mcp server and want to add a new indicator: hospital beds per
100,000 inhabitants at NUTS2 level. Find the right Eurostat dataset and the
filter codes, then write the registry YAML file using this schema: id, label,
unit, source: eurostat, frequency: A, geo_levels, extraction: {dataset,
filters, value_dim: geo}. Check that the codes you use really exist.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/05-new-indicator-yaml.md).
Le modèle a comparé trois datasets candidats avec `get_structure`, vérifié
chaque code avec `list_codes`, lancé un `query_data` de test, puis écrit :

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

Ce fichier passe tel quel `python -m nutshell_mcp.registry validate`. Le modèle
a aussi signalé de lui-même que le dataset mélange des générations NUTS (`DE1`,
`ITC4`) et s'arrête vers 2020.

**Ce qu'un humain doit encore vérifier.** Cette réserve est l'indice :
`hlth_rs_bdsrg` s'intitule *« Hospital beds by NUTS 2 region - historical data
(1993-2016) »*. La série courante est `hlth_rs_bdsrg2` (*Available beds in
hospitals by NUTS 2 region*, 1993–2025). Remplacer le dataset, puis :

```bash
.venv/bin/python -m nutshell_mcp.registry validate
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators hospital_beds_per_100k
```

Le serveur relit le registre à chaud : l'indicateur apparaît dans
`search_indicators` sans redémarrage, et l'exemple 1 peut alors l'utiliser via
`get_indicators` plutôt que par le grain natif. (Le modèle proposait aussi de
ranger le fichier sous `indicators/` ; le répertoire du registre est
`registry/`.)

---

## Croiser les trois sources

Les exemples précédents combinent surtout deux sources. Les questions
ci-dessous exigent les trois regards à la fois sur un territoire :
**socio-économique** (qui y vit — Eurostat), **géographique** (quel est le
milieu — Copernicus) et **infrastructures** (de quoi dispose-t-on —
OpenStreetMap).

## 6. Canicules et personnes âgées

```
Heatwaves hit the elderly hardest. Among the NUTS3 regions of Spain and Italy,
which ones combine the hottest summers, the oldest population and the fewest
hospitals per 100,000 inhabitants? Give me a ranked top 10 with the figures,
and explain how much each data source can be trusted.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/06-heat-ageing.md).
Le modèle a trouvé les quatre indicateurs (`lst_summer_mean`,
`old_age_dependency`, `population`, `hospitals_count`), listé les 159 régions
NUTS3 avec `list_zones`, puis écrit un petit script via l'outil `mcpScript` du
harness, qui appelle `get_indicators` en trois lots (limite de 100 zones par
appel) et classe les régions par centiles :

| # | Région | Temp. estivale (°C) | 65+ / 15–64 (%) | Hôpitaux (OSM) | Pour 100 000 |
|---|---|---|---|---|---|
| 1 | Asti (ITC17) | 25,1 | 45,2 | 2 | 0,97 |
| 2 | Lecce (ITF45) | 27,8 | 42,6 | 18 | 2,35 |
| 3 | Terni (ITI22) | 24,8 | 48,0 | 4 | 1,86 |
| 4 | Cagliari (ITG2G) | 25,9 | 49,5 | 4 | 2,70 |
| 5 | Trapani (ITG11) | 27,7 | 39,8 | 8 | 1,94 |
| … | | | | | |
| 10 | Salamanca (ES415) | 23,3 | 46,3 | 6 | 1,83 |

Sa section fiabilité classe les sources comme le ferait un analyste : Eurostat
« confiance élevée », température « modérée », comptages d'hôpitaux OSM
« confiance la plus faible, le maillon faible » — cartographie inégale, et un
ratio pour 100 000 qui bascule sur un seul hôpital manquant quand les effectifs
sont petits. Conclusion : *lire le top 10 comme une liste indicative, pas comme
un ordre précis.*

**Ce que nous avons vérifié.** Ratios de dépendance, nombres d'hôpitaux et
populations correspondent exactement au miroir. Pas les températures : le modèle
les annonce « 2024 », mais son script lisait la troisième ligne de chaque zone,
qui est **2023** (Asti 25,1 °C en 2023, 23,8 °C en 2024). Le classement est donc
un classement de chaleur 2023. Le modèle décrit aussi la température comme une
température de surface satellitaire ; c'est la température de peau de la
réanalyse ERA5-Land, marquée `[sampled]` sur ce serveur de démonstration
(estimation du fournisseur ARCO, sans clé).

## 7. Déménager avec de jeunes enfants

```
My family with two young children wants to move to Germany or Austria. Compare
their NUTS2 regions: we want mild summers, low unemployment, and as many
schools and train stations as possible relative to population. Suggest the 5
best regions with a table of figures, and tell me what the data cannot tell us.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/07-family-relocation.md).
Quatre `search_indicators`, deux `list_zones`, puis **un seul appel
`get_indicators`** : 5 indicateurs issus de 3 sources sur 45 régions —
exactement les limites d'un appel :

```
get_indicators(["lst_summer_mean", "unemployment_rate", "schools_count",
                "train_stations_count", "population"], [DE11 … AT34])
```

| # | Région | Été (°C) | Chômage | Écoles / 1 000 hab. | Gares / 1 000 hab. |
|---|---|---|---|---|---|
| 1 | Oberösterreich (AT31) | 19,7 | 3,8 % | 0,640 | 0,091 |
| 2 | Steiermark (AT22) | 18,4 | 4,4 % | 0,608 | 0,095 |
| 3 | Lüneburg (DE93) | 18,7 | 2,7 % | 0,488 | 0,078 |
| 4 | Oberfranken (DE24) | 18,4 | 2,7 % | 0,521 | 0,059 |
| 5 | Tübingen (DE14) | 18,4 | 2,8 % | 0,531 | 0,056 |

Tous les chiffres du tableau correspondent au miroir. Le modèle a rendu « doux »
explicite (17,5–20 °C), proposé l'autre lecture (des étés *frais* placent le
Tyrol en tête) et listé ce que les données ne disent pas : places en crèche, coût
du logement, fréquence des trains plutôt que nombre de gares, fréquence des
canicules plutôt qu'une moyenne estivale, et le biais par habitant qui favorise
les petites régions peu peuplées.

---

## D'autres questions

## 8. Tourisme d'été, chaleur et train

```
Summer tourism meets climate change. Among the NUTS2 regions of Spain, Italy,
Greece and Croatia, which ones receive the most tourist nights, have the
hottest summers, and how well are they served by rail relative to population?
Give a top 8 with the figures, and say which conclusions the data does and
does not support.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/08-tourism-heat-rail.md).
Les nuitées touristiques ne sont pas au registre : le modèle est descendu au
grain natif et a choisi la série **mensuelle** (`tour_occ_nin2m`) pour ne sommer
que juin–août, puis l'a croisée avec la température estivale (Copernicus) et le
nombre de gares par habitant (OSM + Eurostat) sur 56 régions :

| # | Région | Nuitées été 2024 | Temp. été 2024 | Gares / 100 000 hab. |
|---|---|---|---|---|
| 1 | Jadranska Hrvatska (HR03) | 63,0 M | 23,6 °C | 3,8 |
| 2 | Cataluña (ES51) | 40,3 M | 23,9 °C | 5,3 |
| 3 | Illes Balears (ES53) | 37,7 M | 26,9 °C | 2,9 |
| 4 | Veneto (ITH3) | 37,0 M | 22,0 °C | 2,4 |
| 5 | Andalucía (ES61) | 27,6 M | 27,7 °C | 2,4 |
| 6 | Canarias (ES70) | 25,6 M | *pas de donnée* | 0 |
| 7 | Notio Aigaio (EL42) | 24,3 M | 25,4 °C | 0 |
| 8 | Emilia-Romagna (ITH5) | 23,0 M | 23,7 °C | 4,8 |

Tous les chiffres du tableau correspondent au miroir. Les constats sont ceux
qu'attendrait un aménageur : les régions les plus chaudes (Attique, Melilla,
Pouilles) ne sont *pas* celles qui accueillent le plus ; volume et intensité
désignent des gagnants différents (la côte croate en volume, les îles grecques
par habitant) ; les destinations estivales les plus fréquentées sont parmi les
*moins* desservies par le train ; et les chiffres annuels surestiment le
tourisme « d'été » alpin, ce que la série mensuelle corrige. Il a gardé les
Canaries dans le classement en marquant leur température manquante (hors de
l'emprise Copernicus sur cette démo). Une erreur : il qualifie la Catalogne, la
Vénétie et l'Émilie-Romagne de « pôles enclavés ».

> *Comment le serveur a façonné ce run.* Le [premier run](results/08-tourism-heat-rail-run1.md)
> a passé dix appels à chercher la Grèce sous `GR` (son code NUTS est `EL`), lu
> les températures 2023 comme 2024 et inventé un été à ~24 °C pour les Canaries.
> Un [deuxième run](results/08-tourism-heat-rail-run2.md), après l'indication
> `GR → EL`, a trouvé la Grèce en un appel mais abandonné le volet tourisme :
> `search_indicators` disait que le registre n'avait rien, sans mentionner le
> catalogue. Le serveur renvoie désormais vers `search_datasets` dans ce cas —
> ce troisième run l'a suivi.

## 9. Écoles et enfants

```
Where in France and Germany are schools scarcest relative to the number of
children? Compare NUTS2 regions using the population aged under 15 and the
number of schools. Give the 5 regions with the fewest schools per 1,000
children and the 5 with the most, and explain the limits of this comparison.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/09-schools-children.md).
Le registre n'a pas d'indicateur « enfants » : le modèle a cherché dans le
catalogue, ouvert plusieurs structures et retenu `demo_r_pjangroup` (population
par tranche d'âge de 5 ans, NUTS2). Il a additionné les tranches 0–4, 5–9 et
10–14 avec `query_data` et les a croisées avec `schools_count` (OSM) :

| | Région | Moins de 15 ans | Écoles | Pour 1 000 enfants |
|---|---|---|---|---|
| le moins | Berlin (DE30) | 511 418 | 1 077 | 2,11 |
| | Hambourg (DE60) | 265 637 | 561 | 2,11 |
| | Darmstadt (DE71) | 580 000 | 1 391 | 2,40 |
| le plus | Bourgogne (FRC1) | 244 642 | 2 434 | 9,95 |
| | Limousin (FRI2) | 101 386 | 934 | 9,21 |
| | Franche-Comté (FRC2) | 193 006 | 1 647 | 8,53 |

Tous les chiffres correspondent au miroir. Le plus intéressant est la lecture
du modèle : l'écart est surtout **structurel, pas une pénurie** — la France
garde une petite école primaire dans presque chaque commune rurale, les villes
allemandes ont moins d'établissements mais plus grands. Il a aussi signalé
qu'OSM étiquette tous les types d'école de la même façon, et que les 0–5 ans
sont au dénominateur sans être scolarisés.

## 10. Convergence Est-Ouest

```
How have Poland, Romania, Czechia and Hungary converged with the rest of the
EU since 2014? For their capital regions and one other NUTS2 region per country
of your choice, show GDP per capita and unemployment over 2014-2024 and
summarise the trend. Point out breaks in series and provisional values.
```

**Vrai run** avec Qwen3.8-27B — [transcript complet](results/10-east-west-convergence.md).
Un seul appel `get_indicators` a renvoyé 11 ans × 8 régions × 2 indicateurs,
avec leurs flags. Pour se donner une référence européenne, le modèle a ensuite
interrogé les 27 États membres et fait leur moyenne :

| Région | PIB / hab. 2014 | 2024 | % de la moyenne UE27, 2014 → 2024 |
|---|---|---|---|
| Praha (CZ01) | 33 200 € | 62 400 € | 127 % → 150 % |
| Budapest (HU11) | 22 700 € | 47 600 € [p] | 87 % → 115 % |
| Warszawa (PL91) | 23 000 € | 45 300 € [p] | 88 % → 109 % |
| București-Ilfov (RO32) | 17 300 € | 45 200 € [p] | 66 % → 109 % |
| Sud-Muntenia (RO31) | 6 400 € | 13 200 € [p] | 24 % → 32 % |

Sa conclusion : les capitales ont rattrapé, voire dépassé, la moyenne
européenne, tandis que le reste de chaque pays reste loin derrière (Budapest
115 % contre Pest 44 %). Le chômage a baissé partout, sauf en Sud-Muntenia,
remonté à 7,3 %.

**Ce que nous avons vérifié.** Les séries régionales et les moyennes UE 2014 et
2024 (26 141 € et 41 548 €) correspondent au miroir ; la moyenne 2020 est fausse
dans la réponse (~27 000 € au lieu de 31 233 €). Le modèle précise lui-même
qu'une moyenne non pondérée de 27 pays, tirée vers le haut par l'Irlande et le
Luxembourg, n'est qu'indicative. Sa liste des ruptures de série est en partie
fausse (il signale le PIB de Varsovie en 2021, qui ne l'est pas).

> *Le premier run* ([transcript](results/10-east-west-convergence-before-fix.md))
> demandait la zone `EU27`, recevait « zone inconnue » et abandonnait la
> comparaison européenne — et plaçait Debrecen en HU31 et Cluj en RO12, deux
> erreurs. Le serveur explique désormais que `EU27` est un agrégat et renvoie
> vers les datasets natifs (`geo=EU27_2020`).

---

## Conseils pour une démo

- **Demandez la provenance.** « Précise la fiabilité de chaque source » déclenche
  le raisonnement sur les flags qualité qui fait la force de l'exemple 1.
- **Forcez un niveau de raisonnement moyen/bas** sur les petits modèles locaux :
  le défaut `xhigh` sur-réfléchit les enchaînements de tools simples.
- **Surveillez les limites.** 5 indicateurs et 100 zones par appel à
  `get_indicators` : un bon modèle fait des lots seul ; un modèle plus faible
  suivra le message de troncature.
- **Les indicateurs `SNAPSHOT`** (comptages OSM comme `hospitals_count`) décrivent
  l'état courant et sont répétés sur chaque période de la zone, marqués
  `[snapshot AAAA-MM]` — ne pas les lire comme une série temporelle.
