"""
Инициализация БД: таблицы, справочники, функции, индексы.

Скрипты migrate_*.sql сюда не входят — их выполняют вручную на существующей БД
в нужном порядке (см. database/).

Запуск с сервера (БД без внешнего IP, доступна только из приватной сети):
  docker compose run --rm backend python -m scripts.init_db

Или локально при доступе к БД:
  cd backend && python -m scripts.init_db

После init.sql выполняется migrate_payout_types.sql (справочник payout_types и перенос
asset_payouts.type → type_id на уже существующих базах).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Config
from app.core.logging import init_logging, get_logger
from app.infrastructure.database.postgres_async import get_connection_pool

init_logging()
logger = get_logger(__name__)

# database/ — project_root/database или /app/database в Docker
_script_dir = Path(__file__).resolve().parent
DB_DIR = _script_dir.parent.parent / "database"
if not DB_DIR.exists():
    DB_DIR = Path("/app/database")  # Docker: context=., database копируется в /app/database
INIT_SQL = DB_DIR / "init.sql"
MIGRATE_PAYOUT_TYPES_SQL = DB_DIR / "migrate_payout_types.sql"
FIX_DUPLICATES_SQL = DB_DIR / "fix_duplicate_payouts.sql"
INDEXES_SQL = DB_DIR / "create_indexes.sql"

# Файлы функций: get_user_portfolios_analytics до get_dashboard_data_complete (зависимость)
_EXCLUDED = ("init.sql", "bd.sql", "create_indexes.sql")
_ALL_FUNCTIONS = sorted(
    f
    for f in DB_DIR.glob("*.sql")
    if f.name not in _EXCLUDED
    and not f.name.startswith("migrate_")
)
_PRIORITY = ["get_user_portfolios_analytics.sql"]  # должен быть до get_dashboard_data_complete
FUNCTION_FILES = [f for f in _ALL_FUNCTIONS if f.name in _PRIORITY] + [
    f for f in _ALL_FUNCTIONS if f.name not in _PRIORITY
]


async def run_sql_file(conn, path: Path) -> None:
    """Выполняет SQL-файл."""
    sql = path.read_text(encoding="utf-8")
    await conn.execute(sql)
    logger.info(f"Выполнен: {path.name}")


async def init_db():
    """Инициализирует БД."""
    Config.validate()
    logger.info("Инициализация БД...")

    pool = await get_connection_pool()
    async with pool.acquire() as conn:
        # 1. Таблицы и справочники
        await run_sql_file(conn, INIT_SQL)

        # 1b. Типы выплат (payout_types) + перенос asset_payouts.type → type_id на старых БД
        if MIGRATE_PAYOUT_TYPES_SQL.exists():
            try:
                await run_sql_file(conn, MIGRATE_PAYOUT_TYPES_SQL)
            except Exception as e:
                logger.warning("migrate_payout_types.sql: %s", e)

        # 2. Функции
        for f in FUNCTION_FILES:
            try:
                await run_sql_file(conn, f)
            except Exception as e:
                logger.warning(f"Ошибка {f.name}: {e}")

        # 3. Удаление дубликатов купонов (если есть) перед созданием уникального индекса
        if FIX_DUPLICATES_SQL.exists():
            try:
                await run_sql_file(conn, FIX_DUPLICATES_SQL)
            except Exception as e:
                logger.warning(f"fix_duplicate_payouts: {e}")

        # 4. Индексы
        await run_sql_file(conn, INDEXES_SQL)

    logger.info("Инициализация БД завершена.")


if __name__ == "__main__":
    from app.utils.async_runner import run_async
    run_async(init_db())
