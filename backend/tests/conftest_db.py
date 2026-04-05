"""
Конфигурация для работы с тестовой базой данных.

Автоматически создает тестовую БД при первом запуске тестов.
"""
import pytest
import os
import subprocess
import asyncio
from app.config import Config

TEST_DB_NAME = os.getenv("TEST_DB_NAME", f"{Config.DB_NAME}_test")


def create_test_database():
    """Создает тестовую БД и копирует структуру из основной БД."""
    try:
        import asyncpg
    except ImportError:
        print("⚠️  asyncpg не установлен. Установите: pip install asyncpg")
        return False

    db_config = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
    }

    async def _create():
        conn = await asyncpg.connect(database='postgres', **db_config)
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
            )
            if exists:
                print(f"✅ Тестовая БД {TEST_DB_NAME} уже существует.")
                return True

            print(f"🔧 Создание тестовой БД {TEST_DB_NAME}...")
            await conn.execute(f'CREATE DATABASE {TEST_DB_NAME}')
        finally:
            await conn.close()

        print(f"📋 Копирование структуры из {Config.DB_NAME}...")
        pg_dump_cmd = [
            'pg_dump',
            '-h', Config.DB_HOST,
            '-p', str(Config.DB_PORT),
            '-U', Config.DB_USER,
            '-d', Config.DB_NAME,
            '--schema-only',
            '--no-owner',
            '--no-acl',
        ]
        psql_cmd = [
            'psql',
            '-h', Config.DB_HOST,
            '-p', str(Config.DB_PORT),
            '-U', Config.DB_USER,
            '-d', TEST_DB_NAME,
            '-q',
        ]
        env = os.environ.copy()
        env['PGPASSWORD'] = Config.DB_PASSWORD

        try:
            dump_process = subprocess.Popen(
                pg_dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
            )
            psql_process = subprocess.Popen(
                psql_cmd, stdin=dump_process.stdout, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, env=env,
            )
            dump_process.stdout.close()
            stdout, stderr = psql_process.communicate()

            if psql_process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                if 'does not exist' not in error_msg.lower():
                    print(f"⚠️  Предупреждение при копировании структуры: {error_msg[:200]}")

            print(f"✅ Тестовая БД {TEST_DB_NAME} создана и настроена.")
            return True
        except FileNotFoundError:
            print("⚠️  pg_dump не найден. Используется упрощенный метод создания БД.")
            print("💡 Для полного копирования структуры установите PostgreSQL client tools")
            return True

    try:
        return asyncio.get_event_loop().run_until_complete(_create())
    except RuntimeError:
        return asyncio.run(_create())
    except Exception as e:
        print(f"❌ Ошибка при создании тестовой БД: {e}")
        return False


@pytest.fixture(scope="session")
def test_db_config():
    """Возвращает конфигурацию для подключения к тестовой БД."""
    return {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'database': TEST_DB_NAME,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
    }


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(test_db_config):
    """
    Автоматически создает и настраивает тестовую БД перед запуском тестов.
    """
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg не установлен. Установите: pip install asyncpg")
        return

    async def _check():
        conn = await asyncpg.connect(
            host=test_db_config['host'],
            port=test_db_config['port'],
            database='postgres',
            user=test_db_config['user'],
            password=test_db_config['password'],
        )
        try:
            return await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME
            )
        finally:
            await conn.close()

    try:
        try:
            exists = asyncio.get_event_loop().run_until_complete(_check())
        except RuntimeError:
            exists = asyncio.run(_check())

        if not exists:
            if not create_test_database():
                pytest.skip(f"Не удалось создать тестовую БД {TEST_DB_NAME}")

    except Exception as e:
        print(f"⚠️  Не удалось проверить/создать тестовую БД: {e}")
        print(f"💡 Тесты, требующие БД, будут пропущены.")

    yield


@pytest.fixture(scope="function")
def clean_test_db(test_db_config):
    """
    Очищает тестовую БД перед каждым тестом (опционально).
    Используйте только для критичных тестов, требующих чистого состояния.
    """
    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg не установлен")
        return

    async def _clean():
        conn = await asyncpg.connect(**test_db_config)
        try:
            await conn.execute("SET session_replication_role = 'replica';")
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'pg_%'
            """)
            for row in tables:
                try:
                    await conn.execute(f"TRUNCATE TABLE {row['tablename']} CASCADE;")
                except Exception as e:
                    print(f"Warning: Could not truncate {row['tablename']}: {e}")
            await conn.execute("SET session_replication_role = 'origin';")
        finally:
            await conn.close()

    try:
        asyncio.get_event_loop().run_until_complete(_clean())
    except RuntimeError:
        asyncio.run(_clean())

    yield
