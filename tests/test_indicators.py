"""Table canonique : écriture atomique, lecture partitionnée, pivot, temporalité."""

from __future__ import annotations

import pyarrow.parquet as pq
import pytest

from nutshell_mcp import indicators, registry


def test_schema_des_neuf_colonnes(materialized):
    path = indicators.partition_path("gdp_per_capita")
    assert path.exists()
    table = pq.read_table(path)
    assert table.column_names == [
        "indicator", "geo_code", "time", "value", "unit",
        "quality", "source", "source_date", "ingested_at",
    ]
    assert set(table.column("indicator").to_pylist()) == {"gdp_per_capita"}
    assert set(table.column("unit").to_pylist()) == {"EUR_HAB"}
    assert set(table.column("source").to_pylist()) == {"eurostat"}


def test_partition_hive_et_compression(materialized):
    path = indicators.partition_path("gdp_per_capita")
    assert path.parent.name == "indicator=gdp_per_capita"
    metadata = pq.ParquetFile(path).metadata
    assert metadata.row_group(0).column(0).compression == "ZSTD"


def test_materialized_info(materialized):
    info = indicators.materialized_info("gdp_per_capita")
    assert info["rows"] == 7
    assert info["source_date"] == "21.08.2026"
    assert (info["time_min"], info["time_max"]) == ("2020", "2023")
    assert indicators.materialized_info("hospitals_count") is None
    assert indicators.materialized_ids() == ["gdp_per_capita", "population"]


def test_ecriture_atomique_remplace_la_partition(materialized):
    spec = registry.get("gdp_per_capita")
    indicators.write_partition(
        spec, [{"geo_code": "FR10", "time": "2024", "value": 70000.0}],
        source_date="22.08.2026",
    )
    info = indicators.materialized_info("gdp_per_capita")
    assert info["rows"] == 1  # l'ancienne partition a disparu, pas d'accumulation
    assert not indicators.partition_dir("gdp_per_capita.tmp").exists()


def test_colonnes_obligatoires(materialized):
    spec = registry.get("gdp_per_capita")
    with pytest.raises(ValueError, match="value"):
        indicators.write_partition(spec, [{"geo_code": "FR10", "time": "2024"}], "x")


def test_pivot_une_colonne_par_indicateur(materialized):
    columns, rows, provenance = indicators.query(
        ["gdp_per_capita", "population"], ["FR10", "FRK2"]
    )
    assert columns == ["geo_code", "time", "gdp_per_capita", "population"]
    assert rows[0] == ["FR10", "2023", "66800 [p]", "12300000"]
    # La période la plus récente vient en premier pour chaque zone.
    assert [r[1] for r in rows if r[0] == "FR10"] == ["2023", "2022", "2021"]
    assert provenance["gdp_per_capita"]["source_date"] == "21.08.2026"
    assert provenance["population"]["source"] == "eurostat"


def test_trois_dernieres_periodes_par_defaut(materialized):
    _, rows, _ = indicators.query(["gdp_per_capita"], ["FR10"])
    assert [r[1] for r in rows] == ["2023", "2022", "2021"]  # 2020 exclu


def test_filtre_temporel_inclusif(materialized):
    _, rows, _ = indicators.query(["gdp_per_capita"], ["FR10"], "2021", "2022")
    assert [r[1] for r in rows] == ["2022", "2021"]
    _, rows, _ = indicators.query(["gdp_per_capita"], ["FR10"], time_from="2022")
    assert [r[1] for r in rows] == ["2023", "2022"]


def test_filtre_temporel_couvre_les_sous_periodes(materialized):
    spec = registry.get("population")
    indicators.write_partition(
        spec,
        [
            {"geo_code": "FR10", "time": "2023-Q1", "value": 1.0},
            {"geo_code": "FR10", "time": "2023-Q4", "value": 4.0},
            {"geo_code": "FR10", "time": "2024-Q1", "value": 5.0},
        ],
        source_date="20.08.2026",
    )
    # time_to="2023" doit inclure 2023-Q1 et 2023-Q4, pas 2024-Q1 (§8.3).
    _, rows, _ = indicators.query(["population"], ["FR10"], "2023", "2023")
    assert sorted(r[1] for r in rows) == ["2023-Q1", "2023-Q4"]


def test_zone_ou_indicateur_absent_ne_leve_pas(materialized):
    _, rows, provenance = indicators.query(["hospitals_count"], ["FR10"])
    assert rows == [] and provenance == {}
    _, rows, _ = indicators.query(["gdp_per_capita"], ["XX99"])
    assert rows == []
