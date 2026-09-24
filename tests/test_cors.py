"""CORS optionnel du transport HTTP (playground de la landing page)."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from nutshell_mcp import server


def _app():
    async def ok(request):
        return PlainTextResponse("ok", headers={"mcp-session-id": "abc"})
    return Starlette(routes=[Route("/mcp", ok, methods=["POST"])])


def test_origins_parsed(monkeypatch):
    monkeypatch.setenv("NUTSHELL_CORS_ORIGINS", " https://a.example/ , http://localhost:8000,")
    assert server._cors_origins() == ["https://a.example", "http://localhost:8000"]
    monkeypatch.delenv("NUTSHELL_CORS_ORIGINS")
    assert server._cors_origins() == []


def test_preflight_and_session_header_exposed():
    client = TestClient(server._wrap_cors(_app(), ["https://a.example"]))
    pre = client.options("/mcp", headers={
        "origin": "https://a.example", "access-control-request-method": "POST",
        "access-control-request-headers": "content-type, mcp-session-id"})
    assert pre.status_code == 200
    assert pre.headers["access-control-allow-origin"] == "https://a.example"
    r = client.post("/mcp", headers={"origin": "https://a.example"})
    assert "mcp-session-id" in r.headers["access-control-expose-headers"].lower()


def test_unknown_origin_refused():
    client = TestClient(server._wrap_cors(_app(), ["https://a.example"]))
    pre = client.options("/mcp", headers={
        "origin": "https://evil.example", "access-control-request-method": "POST"})
    assert pre.status_code == 400
