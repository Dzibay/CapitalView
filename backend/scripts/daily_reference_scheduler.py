"""Persistent daily scheduler for external reference-data updates."""
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

init_logging()
logger = get_logger(__name__)

_SCHEDULER_LOCK = 824601338
_UPDATE_STATE_KEY = "reference_updates"


def _db_config() -> dict:
    return {
        "host": Config.DB_HOST,
        "port": Config.DB_PORT,
        "database": Config.DB_NAME,
        "user": Config.DB_USER,
        "password": Config.DB_PASSWORD,
    }


async def _get_connection() -> asyncpg.Connection:
    for attempt in range(1, 31):
        try:
            return await asyncpg.connect(**_db_config())
        except Exception as exc:
            logger.warning("scheduler_db_wait attempt=%s/30 error=%s", attempt, exc)
            await asyncio.sleep(2)
    raise RuntimeError("PostgreSQL недоступен для scheduler")


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


async def _get_state(conn: asyncpg.Connection) -> dict:
    row = await conn.fetchrow(
        "SELECT state_value FROM service_state WHERE state_key = $1", _UPDATE_STATE_KEY
    )
    if not row or not row["state_value"]:
        return {}
    value = row["state_value"]
    return value if isinstance(value, dict) else json.loads(value)


async def _set_state(conn: asyncpg.Connection, value: dict) -> None:
    await conn.execute(
        """
        INSERT INTO service_state (state_key, state_value, updated_at)
        VALUES ($1, $2::jsonb, now())
        ON CONFLICT (state_key) DO UPDATE SET
            state_value = EXCLUDED.state_value,
            updated_at = now()
        """,
        _UPDATE_STATE_KEY,
        json.dumps(value, ensure_ascii=False, default=str),
    )


async def _run_if_due() -> None:
    interval = max(3600, int(os.getenv("REFERENCE_UPDATE_INTERVAL_SECONDS", "86400")))
    conn = await _get_connection()
    locked = False
    try:
        await _ensure_state_table(conn)
        locked = bool(await conn.fetchval("SELECT pg_try_advisory_lock($1)", _SCHEDULER_LOCK))
        if not locked:
            logger.info("reference_scheduler_skip_locked")
            return

        state = await _get_state(conn)
        last_success_raw = state.get("completed_at")
        last_success = None
        if last_success_raw:
            try:
                last_success = datetime.fromisoformat(str(last_success_raw).replace("Z", "+00:00"))
            except ValueError:
                logger.warning("reference_scheduler_invalid_timestamp value=%s", last_success_raw)
        now = datetime.now(timezone.utc)
        if last_success and (now - last_success).total_seconds() < interval:
            remaining = interval - int((now - last_success).total_seconds())
            logger.info("reference_scheduler_not_due remaining_sec=%s", max(0, remaining))
            return

        logger.info("reference_scheduler_run_start")
        from scripts.run_reference_updates import run_all_updates

        failed_phases = await run_all_updates()
        from app.domain.services.reference_service import invalidate_reference_cache
        invalidate_reference_cache()
        if failed_phases:
            logger.error("reference_scheduler_run_failed phases=%s", ",".join(failed_phases))
            return

        completed_at = datetime.now(timezone.utc).isoformat()
        await _set_state({"status": "success", "source": "scheduler", "completed_at": completed_at})
        logger.info("reference_scheduler_run_done completed_at=%s", completed_at)
    finally:
        if locked:
            await conn.execute("SELECT pg_advisory_unlock($1)", _SCHEDULER_LOCK)
        await conn.close()


async def scheduler() -> None:
    Config.validate()
    poll_seconds = max(60, int(os.getenv("REFERENCE_SCHEDULER_POLL_SECONDS", "300")))
    logger.info("reference_scheduler_started interval_sec=%s poll_sec=%s", os.getenv("REFERENCE_UPDATE_INTERVAL_SECONDS", "86400"), poll_seconds)
    try:
        while True:
            try:
                await _run_if_due()
            except Exception:
                logger.exception("reference_scheduler_iteration_failed")
            await asyncio.sleep(poll_seconds)
    finally:
        await close_connection_pool()


if __name__ == "__main__":
    asyncio.run(scheduler())
