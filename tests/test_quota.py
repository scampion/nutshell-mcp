"""Quotas du serveur HTTP public : identité client, compteurs, refus actionnable."""

from __future__ import annotations

import socket
import threading
import time

import pytest

from nutshell_mcp import quota
from nutshell_mcp.quota import Client

ANON = Client("ip", "203.0.113.7")


@pytest.fixture(autouse=True)
def _clean(monkeypatch, tmp_path):
    monkeypatch.setenv("NUTSHELL_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("NUTSHELL_QUOTA", "1")
    for name in ("NUTSHELL_QUOTA_ANON", "NUTSHELL_QUOTA_BURST", "NUTSHELL_QUOTA_FREE",
                 "NUTSHELL_QUOTA_SHARED", "NUTSHELL_PROXY_HOPS", "NUTSHELL_SHARED_NETS"):
        monkeypatch.delenv(name, raising=False)
    quota.reset()
    yield
    quota.reset()


def _scope(ip="203.0.113.7", headers=(), query=b""):
    return {"type": "http", "client": (ip, 5000), "query_string": query,
            "headers": [(k.encode(), v.encode()) for k, v in headers]}


# ------------------------------------------------------------ compteurs

def test_daily_limit_then_actionable_refusal(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_ANON", "3")
    t = 1_700_000_000.0
    for i in range(3):
        assert quota.consume(ANON, now=t + i * 61) is None
    msg = quota.consume(ANON, now=t + 4 * 61)
    assert msg.startswith("Erreur : quota journalier")
    assert "#contact" in msg and "#self-host" in msg


def test_daily_counter_resets_at_utc_midnight(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_ANON", "1")
    midnight = 1_700_006_400.0  # 2023-11-15T00:00:00Z
    assert quota.consume(ANON, now=midnight - 100) is None
    assert quota.consume(ANON, now=midnight - 10) is not None
    assert quota.consume(ANON, now=midnight + 10) is None


def test_burst_window(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_BURST", "2")
    t = 1_700_000_000.0
    assert quota.consume(ANON, now=t) is None
    assert quota.consume(ANON, now=t + 1) is None
    assert quota.consume(ANON, now=t + 2).startswith("Erreur : trop d'appels")
    assert quota.consume(ANON, now=t + 61) is None


def test_weight_counts(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_ANON", "3")
    t = 1_700_000_000.0
    assert quota.consume(ANON, 2, now=t) is None
    assert quota.consume(ANON, 2, now=t + 1) is not None


def test_pro_is_unlimited(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_BURST", "1")
    pro = Client("key", "k", "pro")
    assert all(quota.consume(pro, now=1_700_000_000.0) is None for _ in range(50))


def test_shared_net_bursts_per_session(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_BURST", "1")
    shared = Client("shared", "shared", "shared")
    t = 1_700_000_000.0
    assert quota.consume(shared, session="a", now=t) is None
    assert quota.consume(shared, session="b", now=t) is None
    assert quota.consume(shared, session="a", now=t) is not None


# ------------------------------------------------------------ identité

def test_identify_ip_and_proxy_hops(monkeypatch):
    assert quota.identify(_scope()) == Client("ip", "203.0.113.7", "anon")
    monkeypatch.setenv("NUTSHELL_PROXY_HOPS", "1")
    scope = _scope(ip="10.0.0.1", headers=[("X-Forwarded-For", "1.1.1.1, 198.51.100.9")])
    assert quota.identify(scope).ident == "198.51.100.9"


def test_identify_shared_net():
    assert quota.identify(_scope(ip="160.79.105.3")).kind == "shared"


def test_identify_keys(tmp_path):
    (tmp_path / "api_keys.tsv").write_text("# clé\ttier\nabc\tpro\tACME\nxyz\tfree\n")
    assert quota.identify(_scope(headers=[("Authorization", "Bearer abc")])).tier == "pro"
    assert quota.identify(_scope(query=b"key=xyz")).tier == "free"
    assert quota.identify(_scope(headers=[("X-Nutshell-Key", "nope")])).tier == "badkey"


# ------------------------------------------------------------ décorateur

async def test_limited_only_with_client(monkeypatch):
    monkeypatch.setenv("NUTSHELL_QUOTA_ANON", "1")

    @quota.limited
    async def demo() -> str:
        return "ok"

    assert await demo() == "ok" and await demo() == "ok"  # hors HTTP : pas de quota
    token = quota._client.set(ANON)
    try:
        assert await demo() == "ok"
        assert (await demo()).startswith("Erreur : quota")
    finally:
        quota._client.reset(token)


# ------------------------------------------------------------ bout en bout

def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


async def test_http_end_to_end(monkeypatch):
    """Le client HTTP est bien vu dans le handler du tool (propagation contextvars)."""
    uvicorn = pytest.importorskip("uvicorn")
    from mcp.client.session import ClientSession
    from mcp.client.streamable_http import streamable_http_client

    from nutshell_mcp import server

    monkeypatch.setenv("NUTSHELL_QUOTA_ANON", "2")
    port = _free_port()
    app = quota.ClientIdentity(server.mcp.streamable_http_app(host="127.0.0.1"))
    srv = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=srv.run, daemon=True)
    thread.start()
    while not srv.started:
        time.sleep(0.05)
    try:
        texts = []
        url = f"http://127.0.0.1:{port}/mcp"
        async with streamable_http_client(url) as streams, ClientSession(*streams) as session:
            await session.initialize()
            for _ in range(3):
                res = await session.call_tool("list_zones", {"level": "NUTS9"})
                texts.append(res.content[0].text)
        assert not texts[0].startswith("Erreur : quota")
        assert texts[2].startswith("Erreur : quota journalier")
    finally:
        srv.should_exit = True
        thread.join(5)
