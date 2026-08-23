"""Tools unifiés : contrat d'erreur (Annexe A), garde-fous et sortie pivotée."""

from __future__ import annotations

import pytest

from nutshell_mcp import indicators, registry, server


async def test_sept_tools_exactement():
    tools = await server.mcp.list_tools()
    assert [t.name for t in tools] == [
        "search_indicators", "list_zones", "get_indicators",
        "search_datasets", "get_structure", "list_codes", "query_data",
    ]


# ------------------------------------------------------------ search_indicators

async def test_search_indicators(materialized):
    out = await server.search_indicators("PIB")
    assert out.splitlines()[0] == "id | label | unité | freq | niveaux geo | source"
    assert "gdp_per_capita | PIB par habitant" in out
    assert "EUR_HAB | A | NUTS0,NUTS1,NUTS2 | eurostat" in out


async def test_search_indicators_signale_le_non_materialise(materialized):
    out = await server.search_indicators("hôpitaux", source="osm")
    assert "hospitals_count" in out
    assert "(non matérialisé)" in out


async def test_search_indicators_sans_resultat(materialized):
    out = await server.search_indicators("zzzz")
    assert "Aucun indicateur" in out
    assert "gdp_per_capita" in out  # le registre complet est rappelé


async def test_search_indicators_source_inconnue(materialized):
    out = await server.search_indicators("PIB", source="insee")
    assert "Source 'insee' inconnue" in out


# ------------------------------------------------------------------ list_zones

async def test_list_zones(materialized):
    out = await server.list_zones("NUTS2", parent="FR")
    assert out.splitlines() == [
        "geo_code | name | level | parent",
        "FR10 | Ile-de-France | NUTS2 | FR1",
        "FRK2 | Rhône-Alpes | NUTS2 | FRK",
    ]


async def test_list_zones_niveau_inconnu(materialized):
    out = await server.list_zones("NUTS5")
    assert "Niveau 'NUTS5' inconnu" in out
    assert "NUTS3" in out


async def test_list_zones_parent_inconnu(materialized):
    out = await server.list_zones("NUTS2", parent="FQ")
    assert "Zone parente 'FQ' inconnue" in out
    assert "Vouliez-vous" in out


async def test_list_zones_sans_referentiel(data_dir, registry_dir):
    out = await server.list_zones("NUTS2")
    assert "Référentiel géographique absent" in out
    assert "sync --source geo" in out


# --------------------------------------------------------------- get_indicators

async def test_get_indicators_pivote(materialized):
    out = await server.get_indicators(["gdp_per_capita", "population"], ["FR10", "FRK2"])
    lines = out.splitlines()
    assert lines[0] == "geo_code | time | gdp_per_capita | population"
    assert lines[1] == "FR10 | 2023 | 66800 [p] | 12300000"
    # deux datasets Eurostat de dates différentes : provenance détaillée par indicateur
    assert lines[-1] == (
        "[Source : eurostat (gdp_per_capita 21.08.2026, population 20.08.2026)]"
    )


async def test_get_indicators_trois_dernieres_periodes(materialized):
    out = await server.get_indicators(["gdp_per_capita"], ["FR10"])
    periods = [line.split(" | ")[1] for line in out.splitlines()[1:-1]]
    assert periods == ["2023", "2022", "2021"]


async def test_get_indicators_filtre_temporel(materialized):
    out = await server.get_indicators(["gdp_per_capita"], ["FR10"], "2020", "2021")
    periods = [line.split(" | ")[1] for line in out.splitlines()[1:-1]]
    assert periods == ["2021", "2020"]


async def test_get_indicators_indicateur_inconnu(materialized):
    out = await server.get_indicators(["gdp_capita"], ["FR10"])
    assert out.startswith("Indicateur 'gdp_capita' inconnu.")
    assert "gdp_per_capita" in out
    assert "search_indicators" in out


async def test_get_indicators_zone_inconnue(materialized):
    out = await server.get_indicators(["gdp_per_capita"], ["FR1O"])
    assert out.startswith("Zone 'FR1O' inconnue.")
    assert "Vouliez-vous" in out
    assert "list_zones" in out


async def test_get_indicators_niveau_incompatible(materialized):
    out = await server.get_indicators(["gdp_per_capita"], ["FR101"])
    assert "n'existe pas au niveau NUTS3" in out
    assert "niveaux disponibles : NUTS0, NUTS1, NUTS2" in out
    assert "FR10" in out  # zone englobante proposée


async def test_get_indicators_niveau_trop_grossier(materialized):
    out = await server.get_indicators(["hospitals_count"], ["FR"])
    assert "n'existe pas au niveau NUTS0" in out
    assert 'list_zones("NUTS2", parent="FR")' in out


async def test_get_indicators_non_materialise_offline(
    materialized, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("NUTSHELL_OFFLINE", "1")
    out = await server.get_indicators(["hospitals_count"], ["FRK2"])
    assert out.splitlines() == [
        "Indicateur 'hospitals_count' non matérialisé et mode offline actif.",
        "Lancer : python -m nutshell_mcp.sync --source osm "
        "--indicators hospitals_count",
    ]


async def test_get_indicators_non_materialise_en_ligne(materialized):
    out = await server.get_indicators(["hospitals_count"], ["FRK2"])
    assert out.startswith("Indicateur 'hospitals_count' non matérialisé.")
    assert "--source osm" in out


async def test_get_indicators_garde_fous(materialized):
    out = await server.get_indicators(["a", "b", "c", "d", "e", "f"], ["FR10"])
    assert "maximum 5" in out
    out = await server.get_indicators(["gdp_per_capita"], [f"Z{i:03d}" for i in range(101)])
    assert "maximum 100" in out
    assert "Aucun indicateur demandé" in await server.get_indicators([], ["FR10"])
    assert "Aucune zone demandée" in await server.get_indicators(["gdp_per_capita"], [])


async def test_get_indicators_aucune_valeur(materialized):
    out = await server.get_indicators(["gdp_per_capita"], ["BE"], "1900", "1901")
    assert "Aucune valeur pour ces zones" in out


async def test_provenance_multi_source(materialized):
    line = server._provenance(
        {
            "gdp_per_capita": {"source": "eurostat", "source_date": "21.08.2026"},
            "lst_summer_mean": {"source": "copernicus", "source_date": "v2023"},
            "hospitals_count": {"source": "osm", "source_date": "extrait 2026-08"},
        }
    )
    assert line == (
        "[Source : copernicus (v2023), eurostat (21.08.2026), osm (extrait 2026-08)]"
    )


# ------------------------------------------------------------ instantanés

@pytest.fixture
def with_snapshot(materialized):
    """Ajoute un instantané OSM (hospitals_count) à FR10 et à BE10."""
    spec = registry.get("hospitals_count")
    indicators.write_partition(
        spec,
        [
            {"geo_code": "FR10", "time": "2026-07", "value": 40.0,
             "quality": "osm_completeness_unknown"},
            {"geo_code": "FR10", "time": "2026-08", "value": 41.0,
             "quality": "osm_completeness_unknown"},
            {"geo_code": "BE10", "time": "2026-08", "value": 38.0,
             "quality": "osm_completeness_unknown"},
        ],
        source_date="extrait 2026-08",
    )
    return materialized


async def test_snapshot_repete_sur_chaque_periode(with_snapshot):
    out = await server.get_indicators(["gdp_per_capita", "hospitals_count"], ["FR10"])
    lines = out.splitlines()
    assert lines[0] == "geo_code | time | gdp_per_capita | hospitals_count"
    # 3 dernières périodes *périodiques* : l'instantané 2026-08 n'en fait pas partie
    assert [ln.split(" | ")[1] for ln in lines[1:4]] == ["2023", "2022", "2021"]
    # dernier instantané (2026-08, pas 2026-07) répété sur chaque ligne
    assert all(ln.endswith("41 [snapshot 2026-08]") for ln in lines[1:4])
    assert "[Instantanés, état courant répété sur chaque période : " \
           "hospitals_count (2026-08, osm_completeness_unknown)]" in lines
    assert lines[-1] == "[Source : eurostat (21.08.2026), osm (extrait 2026-08)]"


async def test_snapshot_ignore_la_fenetre_temporelle(with_snapshot):
    out = await server.get_indicators(
        ["gdp_per_capita", "hospitals_count"], ["FR10"], "2020", "2021"
    )
    lines = out.splitlines()
    assert [ln.split(" | ")[1] for ln in lines[1:3]] == ["2021", "2020"]
    assert all("41 [snapshot 2026-08]" in ln for ln in lines[1:3])


async def test_snapshot_seul_garde_sa_ligne(with_snapshot):
    out = await server.get_indicators(["hospitals_count"], ["FR10", "BE10"])
    lines = out.splitlines()
    assert lines[1] == "BE10 | 2026-08 | 38 [osm_completeness_unknown]"
    assert lines[2] == "FR10 | 2026-08 | 41 [osm_completeness_unknown]"
    assert not any(ln.startswith("[Instantanés") for ln in lines)


async def test_snapshot_zone_sans_periode_garde_sa_ligne(with_snapshot):
    # BE10 a du PIB en 2023 seulement ; FRK2 n'a pas d'instantané : colonne vide.
    out = await server.get_indicators(["gdp_per_capita", "hospitals_count"], ["BE10", "FRK2"])
    lines = out.splitlines()
    assert lines[1] == "BE10 | 2023 | 71200 | 38 [snapshot 2026-08]"
    assert lines[2] == "FRK2 | 2023 | 42400 | "
