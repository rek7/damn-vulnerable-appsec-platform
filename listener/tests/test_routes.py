"""Integration-style tests for listener routes using TestClient.

Covers:
- /healthz
- GET /b/{scan_token}/{vector} — token/vector path parsing, exfil decode
- POST /b/{scan_token}/{vector} — form param d
- Forwarding shape sent to the api (httpx mocked via monkeypatch)
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# /healthz
# ---------------------------------------------------------------------------


def test_healthz() -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET beacon — path parsing
# ---------------------------------------------------------------------------


def test_get_beacon_returns_200() -> None:
    with patch("app.main.forward_beacon", new_callable=AsyncMock):
        resp = client.get("/b/ab12cd34ef56/checkov_external_checks")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_get_beacon_token_and_vector_parsed() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        client.get("/b/aabbccddeeff/symlink_traversal?d=68656c6c6f")

    assert len(captured) == 1
    assert captured[0]["scan_token"] == "aabbccddeeff"
    assert captured[0]["vector"] == "symlink_traversal"


# ---------------------------------------------------------------------------
# GET beacon — hex decode
# ---------------------------------------------------------------------------


def test_get_beacon_decodes_exfil() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    # "secret" in hex
    hex_val = b"secret".hex()  # 736563726574

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        client.get(f"/b/ab12cd34ef56/setup_py_exec?d={hex_val}")

    assert captured[0]["decoded"] == "secret"
    assert captured[0]["raw"] == hex_val


def test_get_beacon_dotted_hex_decode() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    text = "AWS_ACCESS_KEY_ID=AKIA_FAKE"
    full_hex = text.encode("utf-8").hex()
    chunks = [full_hex[i : i + 60] for i in range(0, len(full_hex), 60)]
    dotted = ".".join(chunks)

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        client.get(f"/b/ab12cd34ef56/setup_py_exec?d={dotted}")

    assert captured[0]["decoded"] == text


def test_get_beacon_empty_d() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        client.get("/b/ab12cd34ef56/npm_lifecycle")

    assert captured[0]["raw"] == ""
    assert captured[0]["decoded"] == ""


def test_get_beacon_malformed_hex_no_500() -> None:
    with patch("app.main.forward_beacon", new_callable=AsyncMock):
        resp = client.get("/b/ab12cd34ef56/gemspec_eval?d=zzznotvalidhex")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# POST beacon — form param
# ---------------------------------------------------------------------------


def test_post_beacon_form_param() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    hex_val = b"POST_data".hex()

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        resp = client.post(
            "/b/ab12cd34ef56/eslintrc_js_exec",
            data={"d": hex_val},
        )

    assert resp.status_code == 200
    assert captured[0]["decoded"] == "POST_data"
    assert captured[0]["method"] == "POST"


def test_post_beacon_empty_form() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        resp = client.post("/b/ab12cd34ef56/rubocop_require")

    assert resp.status_code == 200
    assert captured[0]["raw"] == ""
    assert captured[0]["decoded"] == ""


# ---------------------------------------------------------------------------
# Forward payload shape (CONTRACTS §6b)
# ---------------------------------------------------------------------------


def test_forward_payload_shape() -> None:
    captured: list[dict[str, Any]] = []

    async def fake_forward(payload: dict[str, Any]) -> None:
        captured.append(payload)

    with patch("app.main.forward_beacon", side_effect=fake_forward):
        client.get("/b/ab12cd34ef56/checkov_external_checks?d=68656c6c6f")

    p = captured[0]
    # All required keys per CONTRACTS §6b must be present
    for key in ("scan_token", "vector", "raw", "decoded", "method", "path", "remote"):
        assert key in p, f"missing key: {key}"

    assert p["scan_token"] == "ab12cd34ef56"
    assert p["vector"] == "checkov_external_checks"
    assert p["raw"] == "68656c6c6f"
    assert p["decoded"] == "hello"
    assert p["method"] == "GET"
    assert "/b/ab12cd34ef56/checkov_external_checks" in p["path"]


# ---------------------------------------------------------------------------
# api unavailable — listener still returns 200
# ---------------------------------------------------------------------------


def test_api_unavailable_still_200(monkeypatch: Any) -> None:
    """Beacon caller gets 200 even when the api is unreachable.

    forward_beacon catches network errors internally (CONTRACTS §6b: 'tolerate api
    being temporarily unavailable').  Simulate this by patching httpx so the POST
    raises a ConnectError, then confirm the GET /b/… route still returns 200.
    """
    import httpx

    async def failing_forward(payload: dict[str, Any]) -> None:
        # Simulate forward_beacon catching a network error and returning normally.
        import logging

        logger = logging.getLogger("test")
        try:
            raise httpx.ConnectError("simulated: api is down")
        except Exception as exc:  # noqa: BLE001
            logger.warning("simulated api unreachable: %s", exc)
        # Must return normally — no re-raise.

    with patch("app.main.forward_beacon", side_effect=failing_forward):
        resp = client.get("/b/ab12cd34ef56/checkov_external_checks?d=68656c6c6f")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_forward_beacon_tolerates_httpx_error() -> None:
    """forward_beacon itself must not propagate network errors."""
    import asyncio

    import httpx

    from app.forward import forward_beacon

    async def run() -> None:
        # Patch httpx.AsyncClient to raise a connection error
        with patch("app.forward.httpx.AsyncClient") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_instance.post.side_effect = httpx.ConnectError("refused")
            # Must not raise
            await forward_beacon(
                {
                    "scan_token": "ab12cd34ef56",
                    "vector": "checkov_external_checks",
                    "raw": "",
                    "decoded": "",
                    "method": "GET",
                    "path": "/b/ab12cd34ef56/checkov_external_checks",
                    "remote": "127.0.0.1",
                }
            )

    asyncio.run(run())
