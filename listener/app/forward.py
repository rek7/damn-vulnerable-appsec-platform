"""Forward a parsed beacon to the DVAP api (CONTRACTS.md §6b).

The api may be temporarily unavailable (e.g. during startup); log and
continue rather than raising — the beacon caller always gets a 200.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Default matches the compose service hostname; override with DVAP_API_URL.
_API_URL: str = os.environ.get("DVAP_API_URL", "http://api:8000")


async def forward_beacon(payload: dict[str, Any]) -> None:
    """POST *payload* to {DVAP_API_URL}/api/beacons.

    Logs success/failure; never raises — caller must return 200 regardless.
    """
    url = f"{_API_URL}/api/beacons"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload)
            if resp.is_success:
                logger.info("forwarded beacon to api: status=%d", resp.status_code)
            else:
                logger.warning(
                    "api rejected beacon: status=%d body=%.200s",
                    resp.status_code,
                    resp.text,
                )
    except Exception as exc:  # noqa: BLE001
        # api is down or unreachable; log and move on.
        logger.warning("could not reach api (%s): %s", url, exc)
