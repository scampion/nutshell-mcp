# Exemples de prompts — à quoi sert nutshell-mcp

🇫🇷 Français · [🇬🇧 English](examples.md) · [← README](../README.fr.md)

Chaque exemple est un prompt à coller dans n'importe quel client MCP connecté
au serveur (`https://nutshell.scamp.fr/mcp`, ou votre propre instance). Le
modèle n'écrit jamais d'URL SDMX, de requête Overpass ni de requête CDS : il
choisit un tool, le serveur valide et répond depuis les données locales.

> Les sorties de tools sont en français. Le modèle répond dans la langue de
> votre prompt.

| # | Exemple | Tools enchaînés | Montre |
|---|---|---|---|
| 1 | [Où ouvrir une clinique gériatrique ?](#1-où-ouvrir-une-clinique-gériatrique-) | couche unifiée + grain natif | croisement Eurostat / OSM, flags qualité |
| 2 | [Comparer quatre régions](#2-comparer-quatre-régions) | 3 tools unifiés | un tableau, une colonne par indicateur |
| 3 | [Une faute de frappe corrigée par le serveur](#3-une-faute-de-frappe-corrigée-par-le-serveur) | `get_indicators` | erreurs actionnables |
| 4 | [Le tourisme, au-delà du registre](#4-le-tourisme-au-delà-du-registre) | grain natif Eurostat | le catalogue de 10 301 datasets |
| 5 | [Un nouvel indicateur en un fichier YAML](#5-un-nouvel-indicateur-en-un-fichier-yaml) | registre + `sync` | étendre le serveur sans code |

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

**Ce qu'un vrai run a produit** (extrait condensé de la réponse du modèle) :

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
- Il a remarqué que les données françaises portaient sur la géographie régionale
  d'avant 2016 (Poitou-Charentes plutôt que Nouvelle-Aquitaine) et recommandé de
  refaire l'analyse en NUTS 2021 avant toute décision.

La recommandation finale est nuancée en conséquence — c'est tout l'intérêt : un
modèle qui voit les flags qualité se comporte en analyste, pas en moteur de
recherche.

---

## 2. Comparer quatre régions

Le prompt utile le plus court — une question, trois appels de tools.

```
Compare le chômage, l'âge médian et le PIB par habitant de l'Île-de-France,
de l'Oberbayern, de la Lombardie et de la Catalogne. Laquelle paraît la plus
dynamique, et pourquoi ?
```

**Enchaînement attendu.**

```
search_indicators("chômage âge médian PIB")
list_zones("NUTS2", contains="Oberbayern")        # ×4, pour obtenir FR10, DE21, ITC4, ES51
get_indicators(["unemployment_rate", "median_age", "gdp_per_capita"],
               ["FR10", "DE21", "ITC4", "ES51"])
```

La réponse est un tableau pivoté, une colonne par indicateur, avec une ligne de
provenance (`[Source : eurostat (date)]`). Sans filtre temporel, le serveur
renvoie les 3 dernières périodes : le modèle voit la tendance sans effort.

---

## 3. Une faute de frappe corrigée par le serveur

```
Donne-moi le gdp_capita de FR10 sur les 3 dernières années.
```

`gdp_capita` n'existe pas. Au lieu d'échouer, le serveur répond :

```
Indicateur 'gdp_capita' inconnu. Vouliez-vous : gdp_per_capita ?
Utilisez search_indicators pour explorer.
```

et le modèle réessaie seul. Chaque erreur nomme l'action corrective et propose
3 suggestions au plus (`difflib`) — c'est ce qui permet à un modèle local de 27B
de suivre des enchaînements de tools sans humain.

Même principe pour la granularité :

```
Donne-moi le PIB par habitant de la zone NUTS3 FR101.
```

```
'gdp_per_capita' n'existe pas au niveau NUTS3 (zone 'FR101') ; niveaux
disponibles : NUTS0, NUTS1, NUTS2.
Séparez la requête ou demandez la zone englobante 'FR10' (niveau NUTS2).
```

---

## 4. Le tourisme, au-delà du registre

Le registre contient un jeu d'indicateurs choisis ; le grain natif expose tout
Eurostat.

```
Trouve dans Eurostat un dataset sur les nuitées dans les hébergements
touristiques par région. Quelles sont les cinq régions NUTS2 d'Espagne et
d'Italie avec le plus de nuitées la dernière année disponible ? Indique-moi les
filtres utilisés.
```

**Enchaînement attendu.** `search_datasets("nuitées hébergements touristiques")`
→ `get_structure("tour_occ_nin2")` (dimensions, tailles, plage temporelle) →
`list_codes("tour_occ_nin2", "nace_r2")` et `list_codes("tour_occ_nin2", "unit")`
pour choisir des codes valides → `query_data(...)` avec filtres. La description
de chaque tool nomme le suivant : le modèle n'a pas besoin de connaître le
dataset à l'avance. `query_data` est plafonné à 400 lignes et indique comment
restreindre la requête en cas de troncature.

---

## 5. Un nouvel indicateur en un fichier YAML

Pour la personne qui exploite le serveur, pas pour le modèle. Ajouter un
indicateur ne demande aucun code — voir
[Ajouter un indicateur](../README.fr.md#ajouter-un-indicateur--un-fichier-yaml) :

```yaml
# registry/my_indicator.yaml — même schéma pour tout dataset Eurostat
id: my_indicator
label: "…"
unit: …
source: eurostat
frequency: A
geo_levels: [NUTS2]
extraction:
  dataset: <code trouvé avec search_datasets>
  filters: { … }
  value_dim: geo
```

```bash
.venv/bin/python -m nutshell_mcp.registry validate
.venv/bin/python -m nutshell_mcp.sync --source eurostat --indicators my_indicator
```

Le serveur relit le registre à chaud : l'indicateur apparaît dans
`search_indicators` sans redémarrage, et l'exemple 1 peut alors l'utiliser.

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
