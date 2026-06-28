"""Tests for GET /api/config, PUT /api/config, POST /api/config/preset/{name}."""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Config
from app.store import store


@pytest.fixture(autouse=True)
def reset_config() -> None:
    """Reset config to VULNERABLE defaults before each test."""
    asyncio.run(store.set_config(Config()))


client = TestClient(app)


def test_get_config_defaults() -> None:
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data == {
        "strip_credentials": False,
        "block_egress": False,
        "resolve_symlinks": False,
        "disable_extensibility": False,
    }


def test_put_config_full() -> None:
    resp = client.put(
        "/api/config",
        json={
            "strip_credentials": True,
            "block_egress": True,
            "resolve_symlinks": True,
            "disable_extensibility": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["strip_credentials"] is True
    assert data["disable_extensibility"] is True


def test_put_config_partial() -> None:
    """PUT with a partial body should only update provided keys."""
    # First set all True
    client.put(
        "/api/config",
        json={
            "strip_credentials": True,
            "block_egress": True,
            "resolve_symlinks": True,
            "disable_extensibility": True,
        },
    )
    # Partial update: only set strip_credentials back to False
    resp = client.put("/api/config", json={"strip_credentials": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["strip_credentials"] is False
    # Others should remain True
    assert data["block_egress"] is True
    assert data["resolve_symlinks"] is True
    assert data["disable_extensibility"] is True


_ALL_KEYS = [
    "strip_credentials",
    "block_egress",
    "resolve_symlinks",
    "disable_extensibility",
]


def test_preset_hardened() -> None:
    resp = client.post("/api/config/preset/hardened")
    assert resp.status_code == 200
    data = resp.json()
    assert all(data[k] is True for k in _ALL_KEYS)


def test_preset_vulnerable() -> None:
    # First harden
    client.post("/api/config/preset/hardened")
    # Then reset to vulnerable
    resp = client.post("/api/config/preset/vulnerable")
    assert resp.status_code == 200
    data = resp.json()
    assert all(data[k] is False for k in _ALL_KEYS)


def test_preset_unknown() -> None:
    resp = client.post("/api/config/preset/unknown_preset")
    assert resp.status_code == 404
