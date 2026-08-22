"""Fixtures communes : répertoire de données isolé, référentiel geo et registre.

Aucun test n'écrit dans le dépôt : `TERRITORIAL_DATA_DIR` pointe sur un
`tmp_path`, ce qui déplace `mirror/`, `eurostat.db` et `work/` avec lui.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from territorial_mcp import config, geo, indicators, registry

REGISTRY_YAML = {
    "gdp_per_capita": """
        id: gdp_per_capita
        label: "PIB par habitant (prix courants)"
        unit: EUR_HAB
        source: eurostat
        frequency: A
        geo_levels: [NUTS0, NUTS1, NUTS2]
        description: "Richesse produite par habitant"
        extraction:
          dataset: nama_10r_2gdp
          filters: { freq: A, unit: EUR_HAB }
          value_dim: geo
    """,
    "population": """
        id: population
        label: "Population au 1er janvier"
        unit: NR
        source: eurostat
        frequency: A
        geo_levels: [NUTS0, NUTS1, NUTS2, NUTS3]
        extraction:
          dataset: demo_r_pjanaggr3
          filters: { freq: A, unit: NR, sex: T, age: TOTAL }
          value_dim: geo
    """,
    "hospitals_count": """
        id: hospitals_count
        label: "Hôpitaux (comptage OSM)"
        unit: COUNT
        source: osm
        frequency: SNAPSHOT
        geo_levels: [NUTS2, NUTS3, CITY]
        extraction:
          tags:
            - key: amenity
              value: hospital
          geometry: [node, way]
          aggregation: count
    """,
}

#: Zones du référentiel de test : (code, niveau, nom, parent, pays).
GEO_FIXTURE = [
    ("FR", "NUTS0", "France", None, "FR"),
    ("BE", "NUTS0", "Belgique", None, "BE"),
    ("FR1", "NUTS1", "Ile-de-France", "FR", "FR"),
    ("FRK", "NUTS1", "Auvergne-Rhône-Alpes", "FR", "FR"),
    ("BE1", "NUTS1", "Région de Bruxelles-Capitale", "BE", "BE"),
    ("FR10", "NUTS2", "Ile-de-France", "FR1", "FR"),
    ("FRK2", "NUTS2", "Rhône-Alpes", "FRK", "FR"),
    ("BE10", "NUTS2", "Région de Bruxelles-Capitale", "BE1", "BE"),
    ("FR101", "NUTS3", "Paris", "FR10", "FR"),
    ("FRK26", "NUTS3", "Rhône", "FRK2", "FR"),
    ("FR001C", "CITY", "Paris", "FR101", "FR"),
]


@pytest.fixture
def data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isole tout l'état sur disque dans un tmp_path."""
    monkeypatch.setenv("TERRITORIAL_DATA_DIR", str(tmp_path))
    monkeypatch.delenv("TERRITORIAL_OFFLINE", raising=False)
    monkeypatch.delenv("EUROSTAT_OFFLINE", raising=False)
    config.ensure_dirs()
    return tmp_path


@pytest.fixture
def registry_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Registre de test à trois indicateurs (deux eurostat, un osm)."""
    directory = tmp_path / "registry"
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in REGISTRY_YAML.items():
        (directory / f"{name}.yaml").write_text(textwrap.dedent(body), encoding="utf-8")
    monkeypatch.setenv("TERRITORIAL_REGISTRY_DIR", str(directory))
    return directory


@pytest.fixture
def geo_table(data_dir: Path) -> Path:
    """Table `geo` peuplée avec quelques zones françaises et belges."""
    with geo._conn() as conn:
        conn.execute("DELETE FROM geo")
        conn.executemany(
            "INSERT INTO geo VALUES (?,?,?,?,?,?)",
            [(code, level, name, parent, 2024, country)
             for code, level, name, parent, country in GEO_FIXTURE],
        )
    return data_dir


@pytest.fixture
def materialized(data_dir: Path, registry_dir: Path, geo_table: Path):
    """Registre matérialisé + partitions canoniques pour gdp_per_capita et population."""
    registry.materialize()
    gdp = registry.get("gdp_per_capita")
    pop = registry.get("population")
    indicators.write_partition(
        gdp,
        [
            {"geo_code": "FR10", "time": "2023", "value": 66800.0, "quality": "p"},
            {"geo_code": "FR10", "time": "2022", "value": 63000.0},
            {"geo_code": "FR10", "time": "2021", "value": 60000.0},
            {"geo_code": "FR10", "time": "2020", "value": 57000.0},
            {"geo_code": "FRK2", "time": "2023", "value": 42400.0},
            {"geo_code": "FRK2", "time": "2022", "value": 40000.0},
            {"geo_code": "BE10", "time": "2023", "value": 71200.0},
        ],
        source_date="21.08.2026",
    )
    indicators.write_partition(
        pop,
        [
            {"geo_code": "FR10", "time": "2023", "value": 12300000.0},
            {"geo_code": "FRK2", "time": "2023", "value": 6600000.0},
        ],
        source_date="20.08.2026",
    )
    return data_dir
