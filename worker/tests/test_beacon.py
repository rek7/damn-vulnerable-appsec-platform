"""Beacon encoding (§6a) + worker-side beacon host refusal (§13)."""

from __future__ import annotations

from app import beacon
from tests.conftest import GOOD_SEEDS, GOOD_TOKEN


def test_dotted_hex_roundtrip() -> None:
    payload = "AWS_ACCESS_KEY_ID=AKIA_FAKE_DVSEXAMPLE000\nGITHUB_TOKEN=ghp_FAKE"
    dotted = beacon.encode_dotted_hex(payload)
    assert beacon.decode_dotted_hex(dotted) == payload


def test_dotted_hex_chunking_is_about_60_chars() -> None:
    # A payload long enough to need multiple chunks.
    payload = "K=" + ("FAKE" * 100)
    dotted = beacon.encode_dotted_hex(payload)
    chunks = dotted.split(".")
    assert len(chunks) > 1
    # Every chunk except possibly the last is exactly CHUNK_SIZE chars.
    for chunk in chunks[:-1]:
        assert len(chunk) == beacon.CHUNK_SIZE
    assert 1 <= len(chunks[-1]) <= beacon.CHUNK_SIZE
    # Chunks are hex only.
    for chunk in chunks:
        int(chunk, 16)  # raises if not hex


def test_empty_payload_encodes_empty() -> None:
    assert beacon.encode_dotted_hex("") == ""
    assert beacon.decode_dotted_hex("") == ""


def test_build_exfil_joins_secrets_and_token() -> None:
    exfil = beacon.build_exfil(GOOD_SEEDS, GOOD_TOKEN)
    for key, value in GOOD_SEEDS.items():
        assert f"{key}={value}" in exfil
    assert f"K8S_SA_TOKEN={GOOD_TOKEN}" in exfil
    # Roundtrips cleanly through the dotted-hex codec.
    assert beacon.decode_dotted_hex(beacon.encode_dotted_hex(exfil)) == exfil


def test_build_exfil_empty_when_credentials_stripped() -> None:
    # Empty seed inputs produce empty exfil.
    assert beacon.build_exfil({}, "") == ""


def test_build_beacon_url_shape() -> None:
    url = beacon.build_beacon_url("listener", 9000, "ab12cd34ef56", "v", "aa.bb")
    assert url == "http://listener:9000/b/ab12cd34ef56/v?d=aa.bb"
    # No `d` when exfil empty.
    url2 = beacon.build_beacon_url("listener", 9000, "tok", "v", "")
    assert url2 == "http://listener:9000/b/tok/v"


def test_send_beacon_refuses_blocked_host() -> None:
    # Loopback / metadata / non-listener hosts are refused before any socket opens.
    assert beacon.send_beacon("127.0.0.1", 9000, "tok", "v", "aa") is False
    assert beacon.send_beacon("169.254.169.254", 80, "tok", "v", "aa") is False
    assert beacon.send_beacon("example.com", 9000, "tok", "v", "aa") is False
