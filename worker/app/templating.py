"""Placeholder substitution for bundled sample repositories."""

from __future__ import annotations

import os
from pathlib import Path

from . import config

# Files we never rewrite (binary-ish / metadata). Substitution is text-only.
_SKIP_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".gz"})


def build_substitutions(
    *,
    scan_token: str,
    vector: str,
    listener_host: str,
    listener_port: int,
) -> dict[str, str]:
    """Compute the placeholder -> value map for a scan."""
    return {
        config.PLACEHOLDER_SCAN_TOKEN: scan_token,
        config.PLACEHOLDER_VECTOR: vector,
        config.PLACEHOLDER_LISTENER_HOST: listener_host,
        config.PLACEHOLDER_LISTENER_PORT: str(listener_port),
    }


def substitute_text(text: str, subs: dict[str, str]) -> str:
    """Apply every placeholder substitution to a string."""
    for placeholder, value in subs.items():
        text = text.replace(placeholder, value)
    return text


def _is_symlink(path: Path) -> bool:
    return path.is_symlink()


def apply_to_tree(root: Path, subs: dict[str, str]) -> None:
    """Rewrite every regular text file under ``root`` in place with ``subs``.

    Symlinks are never followed or rewritten (the secrets/symlink repo's ``leak``
    must stay pointing at its target). Files that are not valid UTF-8 are left
    untouched.
    """
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if _is_symlink(path):
                continue
            if path.suffix.lower() in _SKIP_SUFFIXES:
                continue
            try:
                original = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            replaced = substitute_text(original, subs)
            if replaced != original:
                path.write_text(replaced, encoding="utf-8")
