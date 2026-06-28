"""Synthetic-seed loading, watermark enforcement, and per-scan env setup (§7).

The watermark check is the load-bearing containment control: if any seed value
is missing the ``FAKE`` watermark, the worker refuses to boot. That guarantees a
compromise can only ever exfiltrate clearly-synthetic credentials.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from . import config


class WatermarkError(RuntimeError):
    """Raised when a seed value (or the k8s token) is missing the watermark."""


_CANARYTOKENS_ALLOWED_KEYS = frozenset(
    {"AWS_CANARY_ACCESS_KEY_ID", "AWS_CANARY_SECRET_ACCESS_KEY"}
)
_AWS_ACCESS_KEY_ID_RE = re.compile(r"^(?:AKIA|ASIA)[A-Z0-9]{16}$")
_AWS_SECRET_ACCESS_KEY_RE = re.compile(r"^[A-Za-z0-9/+=]{40}$")
_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _parse_env_file(text: str) -> dict[str, str]:
    """Parse a minimal KEY=VALUE .env file (ignores blanks and ``#`` comments)."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        out[key.strip()] = value.strip()
    return out


def _first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def _load_extra_seed_overlay() -> dict[str, str]:
    chosen = _first_existing(config.extra_seeds_file_candidates())
    if chosen is None:
        return {}
    values = _parse_env_file(chosen.read_text(encoding="utf-8"))
    return {
        key: value for key, value in values.items() if key in config.SECRET_ENV_KEYS
    }


def load_seeds(seeds_path: Path | None = None) -> dict[str, str]:
    """Load the synthetic seeds file, searching the configured candidates.

    Raises FileNotFoundError if no candidate exists.
    """
    if seeds_path is not None:
        chosen: Path | None = seeds_path if seeds_path.is_file() else None
    else:
        chosen = _first_existing(config.seeds_file_candidates())
    if chosen is None:
        raise FileNotFoundError("synthetic seeds file not found")
    loaded = _parse_env_file(chosen.read_text(encoding="utf-8"))
    loaded.update(_load_extra_seed_overlay())
    return loaded


def load_k8s_token(token_path: Path | None = None) -> str:
    """Load the fake k8s SA token contents, or '' if absent."""
    if token_path is not None:
        chosen: Path | None = token_path if token_path.is_file() else None
    else:
        chosen = _first_existing(config.k8s_token_src_candidates())
    if chosen is None:
        return ""
    return chosen.read_text(encoding="utf-8").strip()


def has_watermark(value: str) -> bool:
    """True if ``value`` contains the case-insensitive ``FAKE`` watermark."""
    return config.WATERMARK.lower() in value.lower()


def _external_canarytokens_enabled() -> bool:
    return os.environ.get("DVAP_ALLOW_EXTERNAL_CANARYTOKENS", "").lower() in _TRUTHY


def _is_allowed_external_canarytoken(key: str, value: str) -> bool:
    if not _external_canarytokens_enabled() or key not in _CANARYTOKENS_ALLOWED_KEYS:
        return False
    if key == "AWS_CANARY_ACCESS_KEY_ID":
        return bool(_AWS_ACCESS_KEY_ID_RE.fullmatch(value))
    if key == "AWS_CANARY_SECRET_ACCESS_KEY":
        return bool(_AWS_SECRET_ACCESS_KEY_RE.fullmatch(value))
    return False


def verify_watermark(seeds: dict[str, str], k8s_token: str) -> None:
    """Raise WatermarkError unless every seed value and the token are watermarked.

    The k8s token is only required to carry the watermark when it is present; an
    empty token (none bundled) is acceptable and simply means no token leak.
    """
    for key, value in seeds.items():
        if not has_watermark(value) and not _is_allowed_external_canarytoken(
            key, value
        ):
            raise WatermarkError(
                f"seed {key!r} is missing the {config.WATERMARK} watermark"
            )
    if k8s_token and not has_watermark(k8s_token):
        raise WatermarkError("k8s SA token is missing the watermark")


def startup_watermark_check() -> tuple[dict[str, str], str]:
    """Load seeds + token and enforce the watermark; used at process startup (§7).

    Returns ``(seeds, k8s_token)`` on success. Raises on any failure so the
    caller can ``sys.exit(1)`` and refuse to serve.
    """
    seeds = load_seeds()
    token = load_k8s_token()
    verify_watermark(seeds, token)
    return seeds, token


def build_subprocess_env(seeds: dict[str, str]) -> dict[str, str]:
    """Build the analyzer subprocess env from os.environ plus synthetic seeds."""
    env = dict(os.environ)
    env.update(seeds)
    return env


def write_k8s_token(token: str, dest: Path | None = None) -> Path | None:
    """Write the k8s SA token to its destination, creating parent dirs (§7).

    Returns the path written, or None if there is no token to write.
    """
    if not token:
        return None
    target = dest if dest is not None else config.k8s_token_dest()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token, encoding="utf-8")
    return target


def remove_k8s_token(dest: Path | None = None) -> None:
    """Remove the k8s SA token file."""
    target = dest if dest is not None else config.k8s_token_dest()
    try:
        target.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
