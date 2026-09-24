"""Résolution centralisée des chemins de données et des modes de fonctionnement.

Tout le paquet passe par ce module : aucun autre fichier ne construit de chemin
en dur. Les valeurs sont lues à chaque appel (fonctions, pas de constantes) pour
que les tests puissent basculer `NUTSHELL_DATA_DIR` vers un `tmp_path` sans
réimporter le paquet.

Variables d'environnement
-------------------------
``NUTSHELL_DATA_DIR``
    Racine des données (défaut : racine du dépôt). Contient ``mirror/``,
    ``eurostat.db``, ``logs/`` et ``work/``.
``NUTSHELL_REGISTRY_DIR``
    Répertoire des YAML d'indicateurs (défaut : ``registry/`` du dépôt). Le
    registre est du code versionné, pas de la donnée : il ne suit pas
    ``NUTSHELL_DATA_DIR`` sauf demande explicite.
``NUTSHELL_OFFLINE=1`` (alias historique ``EUROSTAT_OFFLINE=1``)
    Verrouille le service sur le disque : aucun appel réseau.

Layout des données
------------------
``mirror/eurostat/{dataset}.parquet``      grain natif Eurostat (§6.2)
``mirror/indicators/indicator={id}/…``     grain canonique (§6.1)
``mirror/geo/``                            géométries GISCO (§4)
``eurostat.db``                            catalogue, DSD, registre, états sync
``work/``                                  temporaire purgeable
"""

from __future__ import annotations

import os
from pathlib import Path

#: Racine du dépôt (parent du paquet). Sert de défaut à ``NUTSHELL_DATA_DIR``.
REPO_ROOT = Path(__file__).resolve().parent.parent

#: Millésime NUTS courant du système (§4).
DEFAULT_NUTS_VINTAGE = 2024
#: Millésime précédent, géré pour la conversion à l'ingestion.
PREVIOUS_NUTS_VINTAGE = 2021
#: Résolution des géométries utilisée par les pipelines d'ingestion.
INGEST_RESOLUTION = "01M"
#: Résolution légère, destinée à l'affichage côté client.
DISPLAY_RESOLUTION = "10M"


def data_dir() -> Path:
    """Racine des données locales."""
    raw = os.environ.get("NUTSHELL_DATA_DIR")
    return Path(raw).expanduser().resolve() if raw else REPO_ROOT


def mirror_dir() -> Path:
    """``mirror/`` : tout ce qui est matérialisé sur disque."""
    return data_dir() / "mirror"


def logs_dir() -> Path:
    """Journaux d'appels de tools (rotation quotidienne)."""
    return data_dir() / "logs"


def eurostat_mirror_dir() -> Path:
    """Miroir natif Eurostat, un Parquet par dataset."""
    return mirror_dir() / "eurostat"


def indicators_dir() -> Path:
    """Table canonique partitionnée par indicateur (partitionnement Hive)."""
    return mirror_dir() / "indicators"


def geo_dir() -> Path:
    """Géométries GISCO brutes (GeoJSON 4326) consommées par les ingestions."""
    return mirror_dir() / "geo"


def db_path() -> Path:
    """Base SQLite : catalogue FTS5, DSD, registre, états de synchronisation."""
    return data_dir() / "eurostat.db"


def work_dir() -> Path:
    """Espace de travail temporaire, purgeable sans perte."""
    return data_dir() / "work"


def registry_dir() -> Path:
    """Répertoire des définitions d'indicateurs (``registry/*.yaml``)."""
    raw = os.environ.get("NUTSHELL_REGISTRY_DIR")
    return Path(raw).expanduser().resolve() if raw else REPO_ROOT / "registry"


def offline() -> bool:
    """Vrai si le mode offline total est actif (aucun appel réseau autorisé)."""
    return (
        os.environ.get("NUTSHELL_OFFLINE") == "1"
        or os.environ.get("EUROSTAT_OFFLINE") == "1"
    )


def ensure_dirs() -> None:
    """Crée les répertoires de données manquants (idempotent)."""
    for path in (
        mirror_dir(),
        eurostat_mirror_dir(),
        indicators_dir(),
        geo_dir(),
        work_dir(),
    ):
        path.mkdir(parents=True, exist_ok=True)
