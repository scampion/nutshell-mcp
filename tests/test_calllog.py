"""Journal des appels de tools : ligne par appel, arguments, statut."""

from __future__ import annotations

import logging

import pytest

from nutshell_mcp import calllog


@pytest.fixture
def records():
    got: list[str] = []

    class H(logging.Handler):
        def emit(self, record):
            got.append(record.getMessage())

    h = H()
    calllog.log.addHandler(h)
    yield got
    calllog.log.removeHandler(h)


async def test_logs_name_args_status(records):
    @calllog.logged
    async def demo(query: str, limit: int = 10) -> str:
        return "ok"

    assert await demo("chômage", limit=5) == "ok"
    assert 'tool=demo args={"query": "chômage", "limit": 5}' in records[0]
    assert "status=ok" in records[0]


async def test_logs_error_and_reraises(records):
    @calllog.logged
    async def boom(x: str) -> str:
        raise ValueError("non")

    with pytest.raises(ValueError):
        await boom("a")
    assert "status=error:ValueError" in records[0]


async def test_truncates_long_values(records):
    @calllog.logged
    async def demo(q: str) -> str:
        return "ok"

    await demo("x" * 1000)
    assert len(records[0]) < 500


def test_setup_writes_daily_file(tmp_path, monkeypatch):
    monkeypatch.setenv("NUTSHELL_DATA_DIR", str(tmp_path))
    before = list(calllog.log.handlers)
    calllog.setup()
    try:
        calllog.log.info("tool=x args={} ms=1 status=ok")
        for h in calllog.log.handlers:
            h.flush()
        assert "tool=x" in (tmp_path / "logs" / "nutshell.log").read_text()
    finally:
        for h in list(calllog.log.handlers):
            if h not in before:
                calllog.log.removeHandler(h)
                h.close()
