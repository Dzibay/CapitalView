"""
Скрипт обновления справочных данных: MOEX активы, дивиденды, купоны, криптоактивы.

Запуск:
  python -m scripts.run_reference_updates

Или через env при старте backend:
  RUN_REFERENCE_UPDATES=1
"""
import os
import sys

# Добавляем корень backend в path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.logging import init_logging, get_logger

init_logging()
logger = get_logger(__name__)


async def run_all_updates():
    """Последовательно выполняет все обновления справочников."""
    logger.info("=" * 50)
    logger.info("Запуск обновления справочных данных")
    logger.info("=" * 50)

    # 1. MOEX активы (акции, облигации, фонды)
    try:
        from app.infrastructure.external.moex.update_moex_assets import import_moex_assets_async
        logger.info("--- update_moex_assets ---")
        await import_moex_assets_async()
    except Exception as e:
        logger.error(f"Ошибка update_moex_assets: {e}", exc_info=True)

    # 2. Дивиденды
    try:
        from app.infrastructure.external.moex.update_dividends import update_forecasts
        logger.info("--- update_dividends ---")
        await update_forecasts()
    except Exception as e:
        logger.error(f"Ошибка update_dividends: {e}", exc_info=True)

    # 3. Купоны облигаций
    try:
        from app.infrastructure.external.moex.update_coupons import update_all_coupons
        logger.info("--- update_coupons ---")
        await update_all_coupons()
    except Exception as e:
        logger.error(f"Ошибка update_coupons: {e}", exc_info=True)

    # 4. Криптоактивы
    try:
        from app.infrastructure.external.crypto.update_crypto_assets import import_crypto_assets_async
        logger.info("--- update_crypto_assets ---")
        await import_crypto_assets_async()
    except Exception as e:
        logger.error(f"Ошибка update_crypto_assets: {e}", exc_info=True)

    logger.info("=" * 50)
    logger.info("Обновление справочных данных завершено")
    logger.info("=" * 50)


if __name__ == "__main__":
    from app.config import Config
    from app.utils.async_runner import run_async
    Config.validate()
    run_async(run_all_updates())
