"""
Скрипт обновления справочных данных: MOEX активы, дивиденды, купоны, криптоактивы.

Запуск:
  python -m scripts.run_reference_updates

Или через env при старте backend:
  RUN_REFERENCE_UPDATES=1

Логи: app.reference.* в stdout (см. app.core.logging и app.core.reference_logging).
"""
import os
import sys
import time

# Добавляем корень backend в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import init_logging
from app.core.reference_logging import boost_reference_loggers_to_info, get_reference_logger

init_logging()
boost_reference_loggers_to_info()
logger = get_reference_logger("runner")


async def run_all_updates():
    """Последовательно выполняет все обновления справочников."""
    started = time.perf_counter()
    logger.info("reference_updates_start")
    phases_failed = []

    async def _phase(name: str, coro_factory):
        t0 = time.perf_counter()
        logger.info("reference_phase_start phase=%s", name)
        try:
            await coro_factory()
            logger.info(
                "reference_phase_done phase=%s duration_sec=%.2f",
                name,
                time.perf_counter() - t0,
            )
        except Exception:
            phases_failed.append(name)
            logger.exception("reference_phase_failed phase=%s", name)

    from app.infrastructure.external.moex.update_moex_assets import import_moex_assets_async
    from app.infrastructure.external.moex.update_dividends import update_forecasts
    from app.infrastructure.external.moex.update_coupons import update_all_coupons
    from app.infrastructure.external.crypto.update_crypto_assets import import_crypto_assets_async
    from app.core.reference_logging import reference_progress_enabled

    show_progress = reference_progress_enabled()

    await _phase("moex_assets", import_moex_assets_async)
    await _phase("dividends", lambda: update_forecasts(show_progress=show_progress))
    await _phase("coupons", lambda: update_all_coupons(show_progress=show_progress))
    await _phase("crypto_assets", import_crypto_assets_async)

    logger.info(
        "reference_updates_finish total_duration_sec=%.2f failed_phases=%s",
        time.perf_counter() - started,
        ",".join(phases_failed) if phases_failed else "none",
    )


if __name__ == "__main__":
    from app.config import Config
    from app.utils.async_runner import run_async
    Config.validate()
    run_async(run_all_updates())
