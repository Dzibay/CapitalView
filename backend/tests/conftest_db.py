"""
Конфигурация для работы с тестовой базой данных.

Автоматически создает тестовую БД при первом запуске тестов.
"""
import pytest
import os
import subprocess
from app.config import Config

# Имя тестовой БД (можно переопределить через переменную окружения)
TEST_DB_NAME = os.getenv("TEST_DB_NAME", f"{Config.DB_NAME}_test")


def create_test_database():
    """Создает тестовую БД и копирует структуру из основной БД."""
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    except ImportError:
        print("⚠️  psycopg2 не установлен. Установите: pip install psycopg2-binary")
        return False
    
    # Параметры подключения
    db_config = {
        'host': Config.DB_HOST,
        'port': Config.DB_PORT,
        'user': Config.DB_USER,
        'password': Config.DB_PASSWORD,
    }
    
    try:
        # Подключаемся к postgres для создания тестовой БД
        conn = psycopg2.connect(database='postgres', **db_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Проверяем, существует ли тестовая БД
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB_NAME,)
        )
        exists = cursor.fetchone()
        
        if exists:
            print(f"✅ Тестовая БД {TEST_DB_NAME} уже существует.")
            cursor.close()
            conn.close()
            return True
        
        # Создаем тестовую БД
        print(f"🔧 Создание тестовой БД {TEST_DB_NAME}...")
        cursor.execute(f'CREATE DATABASE {TEST_DB_NAME}')
        cursor.close()
        conn.close()
        
        # Копируем структуру из основной БД через pg_dump
        print(f"📋 Копирование структуры из {Config.DB_NAME}...")
        
        # Формируем команду pg_dump
        pg_dump_cmd = [
            'pg_dump',
            '-h', Config.DB_HOST,
            '-p', str(Config.DB_PORT),
            '-U', Config.DB_USER,
            '-d', Config.DB_NAME,
            '--schema-only',
            '--no-owner',
            '--no-acl'
        ]
        
        # Формируем команду psql
        psql_cmd = [
            'psql',
            '-h', Config.DB_HOST,
            '-p', str(Config.DB_PORT),
            '-U', Config.DB_USER,
            '-d', TEST_DB_NAME,
            '-q'  # Тихий режим
        ]
        
        # Устанавливаем пароль через переменную окружения
        env = os.environ.copy()
        env['PGPASSWORD'] = Config.DB_PASSWORD
        
        try:
            # Запускаем pg_dump и передаем вывод в psql
            dump_process = subprocess.Popen(
                pg_dump_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            psql_process = subprocess.Popen(
                psql_cmd,
                stdin=dump_process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            
            dump_process.stdout.close()
            stdout, stderr = psql_process.communicate()
            
            if psql_process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                # Игнорируем ошибки о несуществующих объектах
                if 'does not exist' not in error_msg.lower():
                    print(f"⚠️  Предупреждение при копировании структуры: {error_msg[:200]}")
            
            print(f"✅ Тестовая БД {TEST_DB_NAME} создана и настроена.")
            return True
            
        except FileNotFoundError:
            # pg_dump/psql не найдены, используем упрощенный метод
            print("⚠️  pg_dump не найден. Используется упрощенный метод создания БД.")
            print("💡 Для полного копирования структуры установите PostgreSQL client tools")
            return True
            
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
    # Проверяем, нужно ли создавать БД
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 не установлен. Установите: pip install psycopg2-binary")
        return
    
    try:
        # Проверяем, существует ли тестовая БД
        conn = psycopg2.connect(
            host=test_db_config['host'],
            port=test_db_config['port'],
            database='postgres',
            user=test_db_config['user'],
            password=test_db_config['password'],
        )
        cursor = conn.cursor()
        cursor.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s",
            (TEST_DB_NAME,)
        )
        exists = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Если БД не существует, создаем её
        if not exists:
            if not create_test_database():
                pytest.skip(f"Не удалось создать тестовую БД {TEST_DB_NAME}")
        
    except Exception as e:
        # Если не удалось подключиться, пропускаем тесты, требующие БД
        print(f"⚠️  Не удалось проверить/создать тестовую БД: {e}")
        print(f"💡 Тесты, требующие БД, будут пропущены.")
        # Не используем pytest.skip здесь, чтобы не блокировать все тесты
    
    yield
    
    # Очистка после тестов (опционально)


@pytest.fixture(scope="function")
def clean_test_db(test_db_config):
    """
    Очищает тестовую БД перед каждым тестом (опционально).
    Используйте только для критичных тестов, требующих чистого состояния.
    """
    try:
        import psycopg2
    except ImportError:
        pytest.skip("psycopg2 не установлен")
        return
    
    conn = psycopg2.connect(**test_db_config)
    cursor = conn.cursor()
    
    # Отключаем внешние ключи временно
    cursor.execute("SET session_replication_role = 'replica';")
    
    # Получаем список таблиц
    cursor.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        AND tablename NOT LIKE 'pg_%'
    """)
    tables = [row[0] for row in cursor.fetchall()]
    
    # Очищаем все таблицы
    for table in tables:
        try:
            cursor.execute(f"TRUNCATE TABLE {table} CASCADE;")
        except Exception as e:
            print(f"Warning: Could not truncate {table}: {e}")
    
    # Включаем внешние ключи обратно
    cursor.execute("SET session_replication_role = 'origin';")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    yield
