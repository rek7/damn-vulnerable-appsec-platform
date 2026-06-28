"""State storage for DVAP API.

The default backend is in-memory so unit tests and simple local imports need no
external service. When ``DVAP_DATABASE_URL`` is set, the API uses Postgres.
"""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any

from .models import Beacon, Scan


class Store:
    """Thread/async-safe in-memory store for scans and beacons."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._scans: dict[str, Scan] = {}
        self._beacons: list[Beacon] = []

    async def startup(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def healthcheck(self) -> bool:
        return True

    async def create_scan(self, scan: Scan) -> Scan:
        async with self._lock:
            self._scans[scan.id] = scan
            return scan.model_copy()

    async def update_scan(self, scan: Scan) -> Scan:
        async with self._lock:
            count = sum(1 for b in self._beacons if b.scan_token == scan.scan_token)
            self._scans[scan.id] = scan.model_copy(update={"beacon_count": count})
            return self._scans[scan.id].model_copy()

    async def get_scan(self, scan_id: str) -> Scan | None:
        async with self._lock:
            scan = self._scans.get(scan_id)
            if scan is None:
                return None
            count = sum(1 for b in self._beacons if b.scan_token == scan.scan_token)
            return scan.model_copy(update={"beacon_count": count})

    async def list_scans(self) -> list[Scan]:
        async with self._lock:
            token_counts: dict[str, int] = {}
            for beacon in self._beacons:
                token_counts[beacon.scan_token] = (
                    token_counts.get(beacon.scan_token, 0) + 1
                )
            result = []
            for scan in reversed(list(self._scans.values())):
                result.append(
                    scan.model_copy(
                        update={"beacon_count": token_counts.get(scan.scan_token, 0)}
                    )
                )
            return result

    async def get_scan_beacons(self, scan_token: str) -> list[Beacon]:
        async with self._lock:
            return [b for b in reversed(self._beacons) if b.scan_token == scan_token]

    # ------------------------------------------------------------------
    # Beacons
    # ------------------------------------------------------------------

    async def add_beacon(self, beacon: Beacon) -> Beacon:
        async with self._lock:
            self._beacons.append(beacon)
            for scan_id, scan in self._scans.items():
                if scan.scan_token == beacon.scan_token:
                    count = sum(
                        1 for b in self._beacons if b.scan_token == scan.scan_token
                    )
                    self._scans[scan_id] = scan.model_copy(
                        update={"beacon_count": count}
                    )
                    break
            return beacon.model_copy()

    async def list_beacons(
        self,
        scan_token: str | None = None,
        vector: str | None = None,
    ) -> list[Beacon]:
        async with self._lock:
            results: Sequence[Beacon] = list(reversed(self._beacons))
            if scan_token:
                results = [b for b in results if b.scan_token == scan_token]
            if vector:
                results = [b for b in results if b.vector == vector]
            return list(results)

    async def resolve_scan_id(self, scan_token: str) -> str | None:
        """Return scan.id for the first scan matching scan_token, or None."""
        async with self._lock:
            for scan in self._scans.values():
                if scan.scan_token == scan_token:
                    return scan.id
            return None


class PostgresStore(Store):
    """Postgres-backed store used by the compose stack."""

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    @asynccontextmanager
    async def _connection(self) -> AsyncIterator[Any]:
        import psycopg

        conn = await psycopg.AsyncConnection.connect(self.database_url)
        try:
            yield conn
            await conn.commit()
        finally:
            await conn.close()

    @staticmethod
    def _jsonb(value: object) -> object:
        from psycopg.types.json import Jsonb

        return Jsonb(value)

    @staticmethod
    def _object(value: object) -> dict[str, Any]:
        if isinstance(value, str):
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        if isinstance(value, dict):
            return value
        raise TypeError(f"expected JSON object from store, got {type(value)!r}")

    @classmethod
    def _scan_from_data(cls, value: object, *, beacon_count: int) -> Scan:
        return Scan.model_validate(cls._object(value)).model_copy(
            update={"beacon_count": beacon_count}
        )

    @classmethod
    def _beacon_from_data(cls, value: object) -> Beacon:
        return Beacon.model_validate(cls._object(value))

    async def startup(self) -> None:
        async with self._connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS scans (
                    id text PRIMARY KEY,
                    scan_token text NOT NULL,
                    data jsonb NOT NULL,
                    created_at text NOT NULL,
                    updated_at text NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS scans_scan_token_idx
                ON scans (scan_token)
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS beacons (
                    id text PRIMARY KEY,
                    scan_token text NOT NULL,
                    vector text NOT NULL,
                    data jsonb NOT NULL,
                    received_at text NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE INDEX IF NOT EXISTS beacons_scan_token_idx
                ON beacons (scan_token)
                """
            )
            await self._seed_integration_credentials(conn)

    async def healthcheck(self) -> bool:
        try:
            async with self._connection() as conn:
                await conn.execute("SELECT 1")
        except Exception:
            return False
        return True

    async def create_scan(self, scan: Scan) -> Scan:
        payload = scan.model_dump(mode="json")
        async with self._connection() as conn:
            await conn.execute(
                """
                INSERT INTO scans (id, scan_token, data, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET scan_token = EXCLUDED.scan_token,
                    data = EXCLUDED.data,
                    created_at = EXCLUDED.created_at,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    scan.id,
                    scan.scan_token,
                    self._jsonb(payload),
                    scan.created_at,
                    scan.updated_at,
                ),
            )
        return scan.model_copy()

    async def update_scan(self, scan: Scan) -> Scan:
        count = await self._beacon_count(scan.scan_token)
        updated = scan.model_copy(update={"beacon_count": count})
        payload = updated.model_dump(mode="json")
        async with self._connection() as conn:
            await conn.execute(
                """
                INSERT INTO scans (id, scan_token, data, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET scan_token = EXCLUDED.scan_token,
                    data = EXCLUDED.data,
                    updated_at = EXCLUDED.updated_at
                """,
                (
                    updated.id,
                    updated.scan_token,
                    self._jsonb(payload),
                    updated.created_at,
                    updated.updated_at,
                ),
            )
        return updated

    async def get_scan(self, scan_id: str) -> Scan | None:
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT s.data, COALESCE(c.beacon_count, 0)
                FROM scans s
                LEFT JOIN (
                    SELECT scan_token, count(*)::int AS beacon_count
                    FROM beacons
                    GROUP BY scan_token
                ) c ON c.scan_token = s.scan_token
                WHERE s.id = %s
                """,
                (scan_id,),
            )
            row = await cursor.fetchone()
            if row is None:
                return None
            return self._scan_from_data(row[0], beacon_count=int(row[1] or 0))

    async def list_scans(self) -> list[Scan]:
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT s.data, COALESCE(c.beacon_count, 0)
                FROM scans s
                LEFT JOIN (
                    SELECT scan_token, count(*)::int AS beacon_count
                    FROM beacons
                    GROUP BY scan_token
                ) c ON c.scan_token = s.scan_token
                ORDER BY s.created_at DESC
                """
            )
            rows = await cursor.fetchall()
            return [
                self._scan_from_data(row[0], beacon_count=int(row[1] or 0))
                for row in rows
            ]

    async def get_scan_beacons(self, scan_token: str) -> list[Beacon]:
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT data
                FROM beacons
                WHERE scan_token = %s
                ORDER BY received_at DESC
                """,
                (scan_token,),
            )
            return [self._beacon_from_data(row[0]) for row in await cursor.fetchall()]

    async def add_beacon(self, beacon: Beacon) -> Beacon:
        payload = beacon.model_dump(mode="json")
        async with self._connection() as conn:
            await conn.execute(
                """
                INSERT INTO beacons (id, scan_token, vector, data, received_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET scan_token = EXCLUDED.scan_token,
                    vector = EXCLUDED.vector,
                    data = EXCLUDED.data,
                    received_at = EXCLUDED.received_at
                """,
                (
                    beacon.id,
                    beacon.scan_token,
                    beacon.vector,
                    self._jsonb(payload),
                    beacon.received_at,
                ),
            )
        return beacon.model_copy()

    async def list_beacons(
        self,
        scan_token: str | None = None,
        vector: str | None = None,
    ) -> list[Beacon]:
        async with self._connection() as conn:
            if scan_token and vector:
                cursor = await conn.execute(
                    """
                    SELECT data
                    FROM beacons
                    WHERE scan_token = %s AND vector = %s
                    ORDER BY received_at DESC
                    """,
                    (scan_token, vector),
                )
            elif scan_token:
                cursor = await conn.execute(
                    """
                    SELECT data
                    FROM beacons
                    WHERE scan_token = %s
                    ORDER BY received_at DESC
                    """,
                    (scan_token,),
                )
            elif vector:
                cursor = await conn.execute(
                    """
                    SELECT data
                    FROM beacons
                    WHERE vector = %s
                    ORDER BY received_at DESC
                    """,
                    (vector,),
                )
            else:
                cursor = await conn.execute(
                    """
                    SELECT data
                    FROM beacons
                    ORDER BY received_at DESC
                    """
                )
            return [self._beacon_from_data(row[0]) for row in await cursor.fetchall()]

    async def resolve_scan_id(self, scan_token: str) -> str | None:
        async with self._connection() as conn:
            cursor = await conn.execute(
                """
                SELECT id
                FROM scans
                WHERE scan_token = %s
                ORDER BY created_at
                LIMIT 1
                """,
                (scan_token,),
            )
            row = await cursor.fetchone()
            return str(row[0]) if row is not None else None

    async def _beacon_count(self, scan_token: str) -> int:
        async with self._connection() as conn:
            cursor = await conn.execute(
                "SELECT count(*)::int FROM beacons WHERE scan_token = %s",
                (scan_token,),
            )
            row = await cursor.fetchone()
            return int(row[0] if row else 0)

    @staticmethod
    def _env_value(*keys: str, fallback: str) -> str:
        for key in keys:
            value = os.environ.get(key)
            if value:
                return value
        return fallback

    @classmethod
    def _integration_credential_rows(
        cls,
    ) -> list[tuple[str, str, str, str, str, str]]:
        return [
            (
                "aws-deploy-access-key",
                "aws-production-deploy",
                "aws_access_key_id",
                "platform-security",
                cls._env_value(
                    "AWS_CANARY_ACCESS_KEY_ID",
                    fallback="AKIAFAKECANARY000001",
                ),
                "Canary cloud integration access key for assessment routing.",
            ),
            (
                "aws-deploy-secret-key",
                "aws-production-deploy",
                "aws_secret_access_key",
                "platform-security",
                cls._env_value(
                    "AWS_CANARY_SECRET_ACCESS_KEY",
                    fallback="FAKEAwsCanarySecretKeyForDVAPDoNotUse000000000FAKE",
                ),
                "Canary cloud integration secret for assessment routing.",
            ),
            (
                "aws-session-token",
                "aws-production-deploy",
                "aws_session_token",
                "platform-security",
                cls._env_value(
                    "AWS_SESSION_TOKEN",
                    fallback="FQoGZXIvYXdzEFAKEdvapCanarySessionTokenDoNotUseFAKE",
                ),
                "Temporary cloud integration session token.",
            ),
            (
                "ci-github-token",
                "repository-automation",
                "github_token",
                "appsec-automation",
                cls._env_value(
                    "GITHUB_CANARY_TOKEN",
                    fallback="ghp_FAKEdvapCanaryGithubToken000000000000",
                ),
                "Canary source-control automation token for repository assessment.",
            ),
            (
                "npm-publish-token",
                "package-publishing",
                "npm_token",
                "release-engineering",
                cls._env_value(
                    "NPM_TOKEN",
                    fallback="npm_FAKEdvapCanaryPublishToken000000000000",
                ),
                "Package publishing token used by release assessment jobs.",
            ),
            (
                "db-reader-dsn",
                "application-postgres",
                "postgres_url",
                "application-platform",
                cls._env_value(
                    "APP_DATABASE_URL",
                    "DVAP_DATABASE_URL",
                    "DATABASE_URL",
                    fallback=(
                        "postgresql://dvap_app:FAKE_DVAP_DB_PASSWORD@postgres:5432/"
                        "dvap"
                    ),
                ),
                "Internal database DSN available to application assessment jobs.",
            ),
        ]

    async def _seed_integration_credentials(self, conn: Any) -> None:
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS integration_credentials (
                id text PRIMARY KEY,
                service text NOT NULL,
                credential_type text NOT NULL,
                owner text NOT NULL,
                value text NOT NULL,
                notes text NOT NULL DEFAULT ''
            )
            """
        )
        for row in self._integration_credential_rows():
            await conn.execute(
                """
                INSERT INTO integration_credentials
                    (id, service, credential_type, owner, value, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE
                SET service = EXCLUDED.service,
                    credential_type = EXCLUDED.credential_type,
                    owner = EXCLUDED.owner,
                    value = EXCLUDED.value,
                    notes = EXCLUDED.notes
                """,
                row,
            )


def _build_store() -> Store:
    database_url = os.environ.get("DVAP_DATABASE_URL")
    if database_url:
        return PostgresStore(database_url)
    return Store()


# Module-level singleton — imported by routes and tests.
store = _build_store()
