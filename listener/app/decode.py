"""Hex-decode helpers for the DVAP beacon exfil format (CONTRACTS.md §6a).

Exfil encoding: UTF-8 bytes hex-encoded, split into ~60-char chunks joined
by '.' (DNS-label style).  Strip the dots, then bytes.fromhex, then decode.
"""

from __future__ import annotations


def decode_dotted_hex(raw: str) -> str:
    """Return the UTF-8 string encoded in *raw* (dotted hex).

    Rules:
    - Strip all '.' characters.
    - Convert the result with bytes.fromhex().
    - Decode the bytes as UTF-8 with errors="replace".
    - Malformed hex (odd length, non-hex chars) → return "" rather than raise.
    - Empty / absent input → return "".
    """
    if not raw:
        return ""

    stripped = raw.replace(".", "")
    if not stripped:
        return ""

    try:
        raw_bytes = bytes.fromhex(stripped)
    except ValueError:
        # Odd-length hex or non-hex characters; best-effort = empty string.
        return ""

    return raw_bytes.decode("utf-8", errors="replace")
