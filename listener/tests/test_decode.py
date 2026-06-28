"""Tests for the dotted-hex decode helper (CONTRACTS.md §6a)."""

from __future__ import annotations

import pytest

from app.decode import decode_dotted_hex


class TestDecodeDottedHex:
    def test_valid_plain_hex(self) -> None:
        # "hello" in hex = 68656c6c6f
        assert decode_dotted_hex("68656c6c6f") == "hello"

    def test_valid_dotted_chunked(self) -> None:
        # "hello world" chunked as DNS labels would be
        text = "hello world"
        full_hex = text.encode("utf-8").hex()
        # Split into 10-char chunks joined by '.'
        chunks = [full_hex[i : i + 10] for i in range(0, len(full_hex), 10)]
        dotted = ".".join(chunks)
        assert decode_dotted_hex(dotted) == text

    def test_empty_string(self) -> None:
        assert decode_dotted_hex("") == ""

    def test_only_dots(self) -> None:
        assert decode_dotted_hex("...") == ""

    def test_malformed_odd_length(self) -> None:
        # Odd number of hex chars → invalid → graceful empty string
        assert decode_dotted_hex("abc") == ""

    def test_malformed_non_hex_chars(self) -> None:
        # Contains 'z', not valid hex
        assert decode_dotted_hex("zzzzzz") == ""

    def test_utf8_multibyte(self) -> None:
        text = "Ünïcödé"
        assert decode_dotted_hex(text.encode("utf-8").hex()) == text

    def test_replacement_on_invalid_utf8(self) -> None:
        # 0xff is not valid standalone UTF-8; should not raise, uses replacement char
        result = decode_dotted_hex("ff")
        assert "�" in result

    def test_real_exfil_shape(self) -> None:
        # Simulate the exfil format: newline-joined KEY=VALUE pairs, chunked ~60 chars
        exfil = "AWS_ACCESS_KEY_ID=AKIA_FAKE_DVSEXAMPLE000\nGITHUB_TOKEN=ghp_FAKE0000"
        full_hex = exfil.encode("utf-8").hex()
        chunks = [full_hex[i : i + 60] for i in range(0, len(full_hex), 60)]
        dotted = ".".join(chunks)
        assert decode_dotted_hex(dotted) == exfil

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "00",
            "deadbeef",
            "de.ad.be.ef",
        ],
    )
    def test_never_raises(self, raw: str) -> None:
        # Must not raise regardless of input
        try:
            decode_dotted_hex(raw)
        except Exception as exc:  # noqa: BLE001
            pytest.fail(f"decode_dotted_hex raised unexpectedly: {exc}")
