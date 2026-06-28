"""Config routes: GET /api/config, PUT /api/config, POST /api/config/preset/{name}."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import Config, ConfigUpdate
from ..store import store

router = APIRouter(prefix="/api/config", tags=["config"])

_PRESETS: dict[str, Config] = {
    "vulnerable": Config(
        strip_credentials=False,
        block_egress=False,
        resolve_symlinks=False,
        disable_extensibility=False,
    ),
    "hardened": Config(
        strip_credentials=True,
        block_egress=True,
        resolve_symlinks=True,
        disable_extensibility=True,
    ),
}


@router.get("", response_model=Config)
async def get_config() -> Config:
    return await store.get_config()


@router.put("", response_model=Config)
async def put_config(body: ConfigUpdate) -> Config:
    current = await store.get_config()
    updated = current.model_copy(
        update={k: v for k, v in body.model_dump().items() if v is not None}
    )
    return await store.set_config(updated)


@router.post("/preset/{name}", response_model=Config)
async def apply_preset(name: str) -> Config:
    preset = _PRESETS.get(name)
    if preset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown preset {name!r}. Valid: vulnerable, hardened",
        )
    return await store.set_config(preset)
