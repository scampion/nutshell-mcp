"""Quotas d'appels de tools pour le serveur HTTP public (démo).

Actif seulement si ``NUTSHELL_QUOTA=1`` **et** transport HTTP : une instance
auto-hébergée ou le transport stdio ne sont jamais limités.

Identité du client, posée par le middleware ASGI :class:`ClientIdentity` dans
une variable de contexte (le SDK MCP 2.x la propage jusqu'au handler du tool) :

- clé d'API (``Authorization: Bearer …``, en-tête ``X-Nutshell-Key`` ou
  ``?key=`` dans l'URL, seule option des connecteurs claude.ai) ;
- sinon l'IP du client. Derrière un proxy, ``NUTSHELL_PROXY_HOPS=n`` lit la
  n-ième adresse en partant de la droite de ``X-Forwarded-For`` ;
- les IP des réseaux partagés (``NUTSHELL_SHARED_NETS``, par défaut les
  sorties des connecteurs claude.ai) partagent un seul compteur, plus élevé.

Limites (appels pondérés, voir ``WEIGHTS``) :

========================  ===========================  ==========
compteur                  variable                     défaut
========================  ===========================  ==========
rafale, par minute        ``NUTSHELL_QUOTA_BURST``     30
anonyme, par jour UTC     ``NUTSHELL_QUOTA_ANON``      100
réseau partagé, par jour  ``NUTSHELL_QUOTA_SHARED``    5000
clé ``free``, par jour    ``NUTSHELL_QUOTA_FREE``      500
clé ``pro``               —                            illimité
========================  ===========================  ==========

Les clés sont lues dans ``<données>/api_keys.tsv`` (``clé<TAB>tier<TAB>libellé``,
``#`` pour les commentaires), rechargé quand le fichier change. Les compteurs
vivent en mémoire : un redémarrage les remet à zéro (ADR-L1-16).
"""

from __future__ import annotations

import contextlib
import contextvars
import datetime as dt
import functools
import hashlib
import ipaddress
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from urllib.parse import parse_qs

from . import config

#: Poids des tools coûteux (défaut 1).
WEIGHTS = {"get_indicators": 2, "query_data": 2}

#: Sorties des connecteurs distants claude.ai (à vérifier dans la doc Anthropic).
DEFAULT_SHARED_NETS = "160.79.104.0/21"

TIERS = ("free", "pro")


@dataclass(frozen=True)
class Client:
    """Qui appelle : ``kind`` ∈ {key, ip, shared}, ``ident`` = clé ou IP brute."""

    kind: str
    ident: str
    tier: str = "anon"

    @property
    def label(self) -> str:
        """Identifiant pseudonymisé, sûr pour les journaux."""
        digest = hashlib.sha256(self.ident.encode()).hexdigest()[:10]
        return f"{self.kind}:{digest}"


_client: contextvars.ContextVar[Client | None] = contextvars.ContextVar(
    "nutshell_client", default=None)
#: ``Mcp-Session-Id`` de la requête : rafale par session sur les réseaux partagés.
_session: contextvars.ContextVar[str] = contextvars.ContextVar(
    "nutshell_session", default="")


def current_client() -> Client | None:
    """Client de la requête en cours (None hors HTTP)."""
    return _client.get()


def enabled() -> bool:
    return os.environ.get("NUTSHELL_QUOTA") == "1"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# ------------------------------------------------------------------ clés

_keys_cache: tuple[float, dict[str, str]] = (-1.0, {})


def _load_keys() -> dict[str, str]:
    """Clé → tier, relu si ``api_keys.tsv`` a changé."""
    global _keys_cache
    path = config.data_dir() / "api_keys.tsv"
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return {}
    if mtime == _keys_cache[0]:
        return _keys_cache[1]
    keys: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split("\t")
        if not parts[0] or parts[0].startswith("#"):
            continue
        tier = parts[1].strip() if len(parts) > 1 else "free"
        keys[parts[0].strip()] = tier if tier in TIERS else "free"
    _keys_cache = (mtime, keys)
    return keys


# ------------------------------------------------------------ identité HTTP

def _shared_nets() -> list:
    raw = os.environ.get("NUTSHELL_SHARED_NETS", DEFAULT_SHARED_NETS)
    nets = []
    for part in filter(None, (p.strip() for p in raw.split(","))):
        with contextlib.suppress(ValueError):
            nets.append(ipaddress.ip_network(part, strict=False))
    return nets


def _client_ip(scope: dict, headers: dict[str, str]) -> str:
    hops = _int_env("NUTSHELL_PROXY_HOPS", 0)
    if hops > 0 and headers.get("x-forwarded-for"):
        chain = [p.strip() for p in headers["x-forwarded-for"].split(",") if p.strip()]
        if chain:
            return chain[max(len(chain) - hops, 0)]
    client = scope.get("client")
    return client[0] if client else "unknown"


def _headers(scope: dict) -> dict[str, str]:
    return {k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope.get("headers", [])}


def identify(scope: dict) -> Client:
    """Construit le :class:`Client` d'une requête ASGI HTTP."""
    headers = _headers(scope)
    key = headers.get("x-nutshell-key", "")
    auth = headers.get("authorization", "")
    if not key and auth.lower().startswith("bearer "):
        key = auth[7:].strip()
    if not key:
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        key = (qs.get("key") or [""])[0]
    if key:
        tier = _load_keys().get(key)
        # clé inconnue : traitée comme anonyme, signalée dans le message de quota
        if tier:
            return Client("key", key, tier)
    ip = _client_ip(scope, headers)
    try:
        addr = ipaddress.ip_address(ip)
        if any(addr in net for net in _shared_nets()):
            return Client("shared", "shared", "shared")
    except ValueError:
        pass
    return Client("ip", ip, "badkey" if key else "anon")


class ClientIdentity:
    """Middleware ASGI : pose le client courant dans la variable de contexte."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        token = _client.set(identify(scope))
        stoken = _session.set(_headers(scope).get("mcp-session-id", ""))
        try:
            await self.app(scope, receive, send)
        finally:
            _session.reset(stoken)
            _client.reset(token)


# --------------------------------------------------------------- compteurs

_lock = threading.Lock()
_daily: dict[tuple[str, str], int] = defaultdict(int)   # (jour, compteur) → poids
_minute: dict[str, deque] = defaultdict(deque)          # compteur → (t, poids)


def _daily_limit(client: Client) -> int | None:
    if client.tier == "pro":
        return None
    if client.tier == "free":
        return _int_env("NUTSHELL_QUOTA_FREE", 500)
    if client.tier == "shared":
        return _int_env("NUTSHELL_QUOTA_SHARED", 5000)
    return _int_env("NUTSHELL_QUOTA_ANON", 100)


def _burst_bucket(client: Client, session: str) -> str | None:
    """Clé de la fenêtre d'une minute ; le réseau partagé n'a pas de rafale globale."""
    if client.tier == "pro":
        return None
    if client.kind == "shared":
        return f"shared:{session}" if session else None
    return client.label


def reset() -> None:
    """Vide les compteurs (tests)."""
    with _lock:
        _daily.clear()
        _minute.clear()


def consume(client: Client, weight: int = 1, *, session: str = "",
            now: float | None = None) -> str | None:
    """Décompte ``weight`` appels ; renvoie le message de refus, ou None si accepté."""
    now = time.time() if now is None else now
    today = dt.datetime.fromtimestamp(now, dt.UTC).date().isoformat()
    limit = _daily_limit(client)
    burst = _int_env("NUTSHELL_QUOTA_BURST", 30)
    bucket = _burst_bucket(client, session)
    with _lock:
        if bucket:
            window = _minute[bucket]
            while window and window[0][0] <= now - 60:
                window.popleft()
            if sum(w for _, w in window) + weight > burst:
                return _burst_message(burst)
        used = _daily[(today, client.label)]
        if limit is not None and used + weight > limit:
            return _daily_message(client, limit)
        _daily[(today, client.label)] = used + weight
        if bucket:
            _minute[bucket].append((now, weight))
    return None


# ---------------------------------------------------------------- messages

def _base_url() -> str:
    return os.environ.get("NUTSHELL_PUBLIC_URL", "https://nutshell.arcamens.ai").rstrip("/")


def _burst_message(burst: int) -> str:
    return (f"Erreur : trop d'appels rapprochés (limite {burst} par minute sur le "
            "serveur de démo). Attendez une minute puis relancez le même appel.")


def _daily_message(client: Client, limit: int) -> str:
    base = _base_url()
    who = {
        "free": "votre clé gratuite",
        "shared": "les connecteurs claude.ai (quota partagé)",
        "badkey": "un client anonyme (clé d'API inconnue, ignorée)",
    }.get(client.tier, "un client anonyme")
    return "\n".join([
        f"Erreur : quota journalier du serveur de démo atteint ({limit} appels/jour "
        f"pour {who}). Réinitialisation à 00:00 UTC.",
        "Transmettez ces options à l'utilisateur pour continuer :",
        f"- offre opérationnelle (quota étendu, SLA, support) : {base}/#contact",
        f"- auto-hébergement gratuit (open source, AGPL) : {base}/#self-host",
        "Ne relancez pas l'appel avant la réinitialisation.",
    ])


# --------------------------------------------------------------- décorateur

def limited(fn):
    """Décore un tool async : refuse l'appel (texte actionnable) si le quota est épuisé."""
    weight = WEIGHTS.get(fn.__name__, 1)

    @functools.wraps(fn)
    async def wrapper(*args, **kwargs):
        client = _client.get()
        if client is not None and enabled():
            refusal = consume(client, weight, session=_session.get())
            if refusal:
                return refusal
        return await fn(*args, **kwargs)

    return wrapper
