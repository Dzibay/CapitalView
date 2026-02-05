"""
Скрипт для установки пакета t-tech-investments из репозитория Т-Банка
"""
import subprocess
import sys

def install_tinkoff():
    """Устанавливает t-tech-investments из репозитория Т-Банка"""
    index_url = "https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple"
    package = "t-tech-investments"
    
    print(f"Установка {package} из репозитория Т-Банка...")
    print(f"Index URL: {index_url}")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            package,
            "--index-url", index_url
        ])
        print(f"✅ {package} успешно установлен!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при установке {package}: {e}")
        return False

if __name__ == "__main__":
    success = install_tinkoff()
    sys.exit(0 if success else 1)
