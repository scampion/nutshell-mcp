"""Projection Eurostat (§7.1) et orchestration sync (§7.4)."""

from __future__ import annotations

import sys
import types

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from nutshell_mcp import config, geo, indicators, project_eurostat, registry, sync


def _write_native(dataset: str, rows: list[tuple]) -> None:
    """Écrit un miroir natif synthétique (freq, unit, geo, time, value, flag)."""
    path = config.eurostat_mirror_dir() / f"{dataset}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    columns = ("freq", "unit", "geo", "time", "value", "flag")
    table = pa.table(
        {
            name: pa.array([r[i] for r in rows],
                           type=pa.float64() if name == "value" else pa.string())
            for i, name in enumerate(columns)
        }
    )
    pq.write_table(table, path, compression="zstd")


def test_projection_applique_filtres_et_referentiel(data_dir, registry_dir, geo_table):
    registry.materialize()
    _write_native(
        "nama_10r_2gdp",
        [
            ("A", "EUR_HAB", "FR10", "2023", 66800.0, "p"),
            ("A", "EUR_HAB", "FRK2", "2023", 42400.0, ""),
            ("A", "MIO_EUR", "FR10", "2023", 999.0, ""),      # filtré : mauvaise unité
            ("A", "EUR_HAB", "EU27_2020", "2023", 100.0, ""),  # filtré : agrégat
            ("A", "EUR_HAB", "FR101", "2023", 1.0, ""),        # filtré : NUTS3 hors geo_levels
        ],
    )
    spec = registry.get("gdp_per_capita")
    assert project_eurostat.project(spec, source_date="21.08.2026") == 2

    table = pq.read_table(indicators.partition_path("gdp_per_capita"))
    assert table.column("geo_code").to_pylist() == ["FR10", "FRK2"]
    assert table.column("quality").to_pylist() == ["p", ""]
    assert set(table.column("unit").to_pylist()) == {"EUR_HAB"}
    assert set(table.column("source_date").to_pylist()) == {"21.08.2026"}


def test_projection_recode_les_millesimes_bijectifs(data_dir, registry_dir, geo_table):
    """Un indicateur NUTS 2021 dont le code est recodé bijectivement est converti."""
    (registry_dir / "gdp_per_capita.yaml").write_text(
        (registry_dir / "gdp_per_capita.yaml").read_text(encoding="utf-8")
        + "nuts_vintage: 2021\n",
        encoding="utf-8",
    )
    registry.materialize()
    with geo._conn() as conn:
        conn.executemany(
            "INSERT INTO nuts_changes VALUES (?,?,?,?,?,?)",
            [
                ("FRXX", "FRK2", 2021, 2024, 1, "Code change"),
                ("FRZZ", None, 2021, 2024, 0, "Merged"),
            ],
        )
    _write_native(
        "nama_10r_2gdp",
        [
            ("A", "EUR_HAB", "FRXX", "2023", 42400.0, ""),
            ("A", "EUR_HAB", "FRZZ", "2023", 1.0, ""),   # non bijectif : disparaît
            ("A", "EUR_HAB", "FR10", "2023", 66800.0, "p"),
        ],
    )
    assert project_eurostat.project(registry.get("gdp_per_capita"), "21.08.2026") == 2
    table = pq.read_table(indicators.partition_path("gdp_per_capita"))
    rows = dict(zip(table.column("geo_code").to_pylist(),
                    table.column("quality").to_pylist(), strict=True))
    assert rows == {"FRK2": "recoded", "FR10": "p"}


def test_projection_sans_miroir_natif(data_dir, registry_dir, geo_table):
    registry.materialize()
    with pytest.raises(project_eurostat.ProjectionError, match="miroir natif absent"):
        project_eurostat.project(registry.get("gdp_per_capita"))


def test_projection_sans_referentiel_geo(data_dir, registry_dir):
    registry.materialize()
    _write_native("nama_10r_2gdp", [("A", "EUR_HAB", "FR10", "2023", 1.0, "")])
    with pytest.raises(project_eurostat.ProjectionError, match="référentiel geo absent"):
        project_eurostat.project(registry.get("gdp_per_capita"))


def test_projection_sans_zone_au_bon_niveau(data_dir, registry_dir, geo_table):
    """Le référentiel existe mais ne contient aucune zone aux niveaux déclarés."""
    registry.materialize()
    with geo._conn() as conn:
        conn.execute("DELETE FROM geo WHERE level IN ('NUTS0','NUTS1','NUTS2')")
    _write_native("nama_10r_2gdp", [("A", "EUR_HAB", "FR10", "2023", 1.0, "")])
    with pytest.raises(project_eurostat.ProjectionError, match="aucune zone"):
        project_eurostat.project(registry.get("gdp_per_capita"))


def test_projection_filtre_inexistant(data_dir, registry_dir, geo_table):
    registry.materialize()
    _write_native("demo_r_pjanaggr3", [("A", "NR", "FR10", "2023", 1.0, "")])
    # population filtre sur sex et age, absents du miroir synthétique.
    with pytest.raises(project_eurostat.ProjectionError, match="filtre 'sex' absent"):
        project_eurostat.project(registry.get("population"))


def test_indicators_for_dataset(data_dir, registry_dir):
    ids = [s.id for s in project_eurostat.indicators_for_dataset("nama_10r_2gdp")]
    assert ids == ["gdp_per_capita"]
    assert project_eurostat.indicators_for_dataset("inconnu") == []


# ------------------------------------------------------------------ sync.py

def test_pipeline_non_implemente(data_dir, registry_dir, monkeypatch):
    # Les lots 2 et 3 sont livrés : on simule une source dont le module
    # d'ingestion n'existe pas pour garder la couverture du cas « pipeline absent ».
    monkeypatch.setitem(sync.PIPELINE_MODULES, "osm", "nutshell_mcp.ingest_inexistant")
    report = sync.sync_pipeline("osm", [], full=False)
    assert report.ok  # un lot non livré n'est pas un échec
    assert "pipeline non implémenté" in "\n".join(report.notes)
    assert "nutshell_mcp.ingest_inexistant" in "\n".join(report.notes)
