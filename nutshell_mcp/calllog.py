"""Journal quotidien des appels de tools : fonction, arguments, durée, statut.

Une ligne par appel dans ``<données>/logs/nutshell.log``, rotation à minuit
(``NUTSHELL_LOG_DAYS`` jours conservés, 30 par défaut). Le journal n'est actif
que si ``setup()`` a été appelé (démarrage du serveur) : les tests et imports
n'écrivent rien. ``NUTSHELL_CALL_LOG=0`` le désactive.
"""

from __future__ import annotations

import functools
import inspect
import json
import logging
import os
import time
from logging.handlers import TimedRotatingFileHandler

from . import config, quota

MAX_VALUE_CHARS = 300  # au-delà, les valeurs d'arguments sont tronquées

log = logging.getLogger("nutshell.calls")
log.addHandler(logging.NullHandler())
log.propagate = False
log.setLevel(logging.INFO)


def setup() -> None:
    """Attache le fichier rotatif quotidien (idempotent)."""
    if os.environ.get("NUTSHELL_CALL_LOG") == "0":
        return
    if any(isinstance(h, TimedRotatingFileHandler) for h in log.handlers):
        return
    path = config.logs_dir()
    path.mkdir(parents=True, exist_ok=True)
    handler = TimedRotatingFileHandler(
        path / "nutshell.log", when="midnight", encoding="utf-8",
        backupCount=int(os.environ.get("NUTSHELL_LOG_DAYS", "30")),
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", "%Y-%m-%dT%H:%M:%S"))
    log.addHandler(handler)


def _short(value):
    if isinstance(value, str) and len(value) > MAX_VALUE_CHARS:
        return value[:MAX_VALUE_CHARS] + "…"
    return value


def logged(fn):
    """Décore un tool async : journalise nom, arguments, durée et statut."""
    sig = inspect.signature(fn)

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        try:
            bound = sig.bind_partial(*args, **kwargs)
            shown = json.dumps(
                {k: _short(v) for k, v in bound.arguments.items()},
                ensure_ascii=False, default=str,
            )
        except Exception:  # le journal ne doit jamais casser un appel
            shown = "?"
        start = time.perf_counter()
        status = "ok"
        try:
            result = await fn(*args, **kwargs)
            if isinstance(result, str) and result.startswith("Erreur : quota"):
                status = "quota"
            elif isinstance(result, str) and result.startswith("Erreur : trop d'appels"):
                status = "burst"
            elif isinstance(result, str) and result.startswith(("Aucun", "Erreur")):
                status = "vide"
            return result
        except Exception as exc:
            status = f"error:{type(exc).__name__}"
            raise
        finally:
            ms = round((time.perf_counter() - start) * 1000)
            client = quota.current_client()
            log.info("tool=%s args=%s ms=%d status=%s client=%s", fn.__name__, shown,
                     ms, status, client.label if client else "local")

    return wrapper
