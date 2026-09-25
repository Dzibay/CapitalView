"""Idempotent database bootstrap and one-time reference-data seed."""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import asyncpg

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config
from app.core.logging import get_logger, init_logging
from app.infrastructure.database.postgres_async import close_connection_pool
from scripts.init_db import init_db

init_logging()
logger = get_logger(__name__)

_BOOTSTRAP_LOCK = 824601337
_SEED_STATE_KEY = "reference_seed"
_UPDATE_STATE_KEY = "reference_updates"


def _db_config() -> dict:
    return {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "database": Config.DB_NAME,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
    }


async def _connect_with_retry() -> asyncpg.Connection:
    attempts = max(1, int(os.getenv("DB_CONNECT_RETRIES", "30")))
    delay = max(1, int(os.getenv("DB_CONNECT_RETRY_SECONDS", "2")))
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            conn = await asyncpg.connect(**_db_config())
            logger.info("bootstrap_db_connected attempt=%s", attempt)
            return conn
        except Exception as exc:
            last_error = exc
            logger.warning("bootstrap_db_wait attempt=%s/%s error=%s", attempt, attempts, exc)
            if attempt < attempts:
                await asyncio.sleep(delay)
    raise RuntimeError(f"PostgreSQL не доступен после {attempts} попыток: {last_error}")


async def _ensure_state_table(conn: asyncpg.Connection) -> None:
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS service_state (
            state_key text PRIMARY KEY,
            state_value jsonb NOT NULL DEFAULT '{}'::jsonb,
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )


async def _get_state(conn: asyncpg.Connection, key: str) -> dict:
    row = await conn.fetchrow(
        "SELECT state_value FROM service_state WHERE state_key = $1", key
    )
    if not row or not row["state_value"]:
        return {}
    value = row["state_value"]
    return value if isinstance(value, dict) else json.loads(value)


async def _set_state(conn: asyncpg.Connection, key: str, value: dict) -> None:
    await conn.execute(
        """
        INSERT INTO service_state (state_key, state_value, updated_at)
        VALUES ($1, $2::jsonb, now())
        ON CONFLICT (state_key) DO UPDATE SET
            state_value = EXCLUDED.state_value,
            updated_at = now()
        """,
        key,
        json.dumps(value, ensure_ascii=False, default=str),
    )


async def bootstrap() -> None:
    Config.validate()
    logger.info("bootstrap_start")
    conn = await _connect_with_retry()
    locked = False
    try:
        await conn.execute("SELECT pg_advisory_lock($1)", _BOOTSTRAP_LOCK)
        locked = True
        logger.info("bootstrap_lock_acquired")

        logger.info("bootstrap_schema_start")
        try:
            await init_db()
        finally:
            await close_connection_pool()
        logger.info("bootstrap_schema_done")

        await _ensure_state_table(conn)
        seed_version = os.getenv("REFERENCE_SEED_VERSION", "1").strip() or "1"
        seed_enabled = os.getenv("REFERENCE_SEED_ENABLED", "true").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        seed_state = await _get_state(conn, _SEED_STATE_KEY)
        already_seeded = (
            seed_state.get("status") == "success"
            and str(seed_state.get("version")) == seed_version
        )

        if already_seeded:
            logger.info("reference_seed_skipped version=%s", seed_version)
            return
        if not seed_enabled:
            logger.warning("reference_seed_disabled")
            return

        logger.info("reference_seed_start version=%s", seed_version)
        from scripts.run_reference_updates import run_all_updates

        failed_phases = await run_all_updates()
        if failed_phases:
            raise RuntimeError(
                "Первичная загрузка справочников завершилась с ошибками: "
                + ", ".join(failed_phases)
            )

        completed_at = datetime.now(timezone.utc).isoformat()
        await _set_state(
            conn,
            _SEED_STATE_KEY,
            {"status": "success", "version": seed_version, "completed_at": completed_at},
        )
        await _set_state(
            conn,
            _UPDATE_STATE_KEY,
            {"status": "success", "source": "bootstrap", "completed_at": completed_at},
        )
        logger.info("reference_seed_done version=%s", seed_version)
    finally:
        if locked:
            await conn.execute("SELECT pg_advisory_unlock($1)", _BOOTSTRAP_LOCK)
            logger.info("bootstrap_lock_released")
        await conn.close()


if __name__ == "__main__":
    asyncio.run(bootstrap())
