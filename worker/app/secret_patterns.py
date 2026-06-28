"""Synthetic-secret detection patterns + the symlink-aware file walker (§7, §13).

The patterns match the synthetic seed values (AKIA…, ghp_…, npm_…,
sk_live_…, ``postgres://`` / ``postgresql://``, webhook-shaped values, and AWS
secret/session tokens). The walker has two modes:

* vulnerable  -- ``open()`` follows symlinks without checking, so a symlink to
  ``/proc/self/environ`` leaks the worker env.
* resolved    -- ``os.path.realpath`` each candidate and SKIP any whose real path
  escapes the workdir root (the ``resolve_symlinks`` mitigation, §4).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Patterns for the synthetic seed shapes (§7). Names are for reporting only.
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key_id": re.compile(r"AKIA(?=[0-9A-Z_]*FAKE)[0-9A-Z_]{8,}"),
    "aws_secret_access_key": re.compile(r"FAKE[A-Za-z0-9]{20,}FAKE"),
    "aws_session_token": re.compile(r"FQoG[A-Za-z0-9_+=/-]*FAKE[A-Za-z0-9_+=/-]*"),
    "github_token": re.compile(r"ghp_[A-Za-z0-9_]*FAKE[A-Za-z0-9_]*"),
    "npm_token": re.compile(r"npm_[A-Za-z0-9_]*FAKE[A-Za-z0-9_]*"),
    "stripe_key": re.compile(r"sk_live_[A-Za-z0-9_]*FAKE[A-Za-z0-9_]*"),
    "postgres_url": re.compile(r"postgres(?:ql)?://[^\s\x00]*FAKE[^\s\x00]*"),
    "slack_webhook": re.compile(r"https://hooks\.slack\.[^\s\x00]*FAKE[^\s\x00]*"),
}

# Skip obviously-binary files when reading.
_MAX_READ_BYTES = 256 * 1024


def find_secrets_in_text(text: str) -> list[str]:
    """Return the names of every pattern that matches somewhere in ``text``."""
    return [name for name, pat in SECRET_PATTERNS.items() if pat.search(text)]


def _read_text(path: Path) -> str:
    """Read up to ``_MAX_READ_BYTES`` of a file as text (errors replaced).

    Uses a plain ``open`` which follows symlinks -- this is the vulnerable read.
    """
    with open(path, "rb") as fh:
        data = fh.read(_MAX_READ_BYTES)
    return data.decode("utf-8", errors="replace")


def _escapes_root(root: Path, path: Path) -> bool:
    """True if ``path``'s realpath escapes ``root`` (resolve_symlinks check)."""
    root_real = os.path.realpath(str(root))
    path_real = os.path.realpath(str(path))
    return not (path_real == root_real or path_real.startswith(root_real + os.sep))


def scan_workdir(workdir: Path, *, resolve_symlinks: bool) -> dict[str, list[str]]:
    """Walk ``workdir`` and return ``{relative_path: [secret_names...]}``.

    On the vulnerable path (``resolve_symlinks=False``) symlinks are followed and
    read. On the mitigated path each candidate's realpath is checked and any file
    whose real path escapes ``workdir`` is skipped (its symlink is never read).
    """
    findings: dict[str, list[str]] = {}
    root = workdir
    for dirpath, _dirnames, filenames in os.walk(workdir, followlinks=False):
        for name in filenames:
            path = Path(dirpath) / name
            # Mitigated: only read symlinks whose real target stays in-root.
            if resolve_symlinks and path.is_symlink() and _escapes_root(root, path):
                continue
            try:
                text = _read_text(path)
            except OSError:
                continue
            matches = find_secrets_in_text(text)
            if matches:
                rel = str(path.relative_to(workdir))
                findings[rel] = matches
    return findings
