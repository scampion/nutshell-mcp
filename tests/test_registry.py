"""Validation du registre d'indicateurs : cas valides et cas rejetés."""

from __future__ import annotations

import textwrap

import pytest

from nutshell_mcp import registry

INVALID = {
    # 1. source inconnue → aucun membre de l'union discriminée ne correspond
    "bad_source": """
        id: bad_source
        label: "Indicateur à source inventée"
        unit: PC
        source: insee
        frequency: A
        geo_levels: [NUTS2]
        extraction:
          dataset: foo
    """,
    # 2. extraction incomplète pour la source déclarée (tags manquants)
    "bad_extraction": """
        id: bad_extraction
        label: "Comptage OSM sans tags"
        unit: COUNT
        source: osm
        frequency: SNAPSHOT
        geo_levels: [NUTS3]
        extraction:
          geometry: [node]
          aggregation: count
    """,
    # 3. niveau géographique hors vocabulaire
    "bad_level": """
        id: bad_level
        label: "Indicateur au niveau communal"
        unit: NR
        source: eurostat
        frequency: A
        geo_levels: [LAU2]
        extraction:
          dataset: demo_r_pjanaggr3
          value_dim: geo
    """,
}


def test_registre_valide(registry_dir):
    specs = registry.load_all()
    assert {s.id for s in specs} == {"gdp_per_capita", "population", "hospitals_count"}
    gdp = next(s for s in specs if s.id == "gdp_per_capita")
    assert gdp.source == "eurostat"
    assert gdp.extraction.dataset == "nama_10r_2gdp"
    assert gdp.extraction.filters == {"freq": "A", "unit": "EUR_HAB"}
    assert gdp.nuts_vintage == 2024  # défaut


def test_filtre_par_source(registry_dir):
    assert [s.id for s in registry.load_all(source="osm")] == ["hospitals_count"]
    osm = registry.load_all(source="osm")[0]
    assert osm.extraction.tags[0].key == "amenity"
    assert osm.extraction.aggregation == "count"


@pytest.mark.parametrize("name", sorted(INVALID))
def test_registre_invalide(registry_dir, name):
    (registry_dir / f"{name}.yaml").write_text(
        textwrap.dedent(INVALID[name]), encoding="utf-8"
    )
    with pytest.raises(registry.RegistryError) as exc:
        registry.load_all()
    assert name in str(exc.value)


def test_id_doit_egaler_le_nom_de_fichier(registry_dir):
    (registry_dir / "mismatch.yaml").write_text(
        textwrap.dedent(
            """
            id: autre_nom
            label: "Identifiant incohérent"
            unit: PC
            source: eurostat
            frequency: A
            geo_levels: [NUTS2]
            extraction:
              dataset: foo
              value_dim: geo
            """
        ),
        encoding="utf-8",
    )
    with pytest.raises(registry.RegistryError, match=r"mismatch\.yaml"):
        registry.load_all()


def test_materialisation_et_recherche(data_dir, registry_dir):
    assert registry.materialize() == 3
    assert registry.all_ids() == ["gdp_per_capita", "hospitals_count", "population"]
    hits = registry.search("PIB")
    assert [h["id"] for h in hits] == ["gdp_per_capita"]
    assert [h["id"] for h in registry.search("", source="osm")] == ["hospitals_count"]
    assert registry.get("gdp_per_capita").unit == "EUR_HAB"
    assert registry.get("inexistant") is None


def test_rematerialisation_si_les_yaml_changent(data_dir, registry_dir):
    registry.materialize()
    (registry_dir / "gdp_per_capita.yaml").unlink()
    registry.ensure_materialized()
    assert "gdp_per_capita" not in registry.all_ids()


def test_cli_validate(data_dir, registry_dir, capsys):
    assert registry.main(["validate"]) == 0
    assert "3 indicateurs" in capsys.readouterr().out
    (registry_dir / "bad_level.yaml").write_text(
        textwrap.dedent(INVALID["bad_level"]), encoding="utf-8"
    )
    assert registry.main(["validate"]) == 1
