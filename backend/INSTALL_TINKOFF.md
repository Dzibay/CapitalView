# Установка библиотеки Tinkoff Investments

Библиотека `t-tech-investments` устанавливается из приватного репозитория Т-Банка.

## Способ 1: Использование скрипта (рекомендуется)

```bash
cd backend
python install_tinkoff.py
```

## Способ 2: Прямая установка через pip

```bash
pip install t-tech-investments --index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

## Способ 3: Через requirements файл

```bash
pip install -r requirements-tinkoff.txt --index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
```

## Важно

- Убедитесь, что вы находитесь в активированном виртуальном окружении (venv)
- Python версии 3.8.1 или выше (но менее 4.0)
- Старые пакеты `tinkoff` и `tinkoff-investments` были удалены из requirements.txt

## Проверка установки

После установки проверьте, что импорт работает:

```python
from tinkoff.invest import Client, InstrumentIdType
```

Если импорт проходит без ошибок, установка выполнена успешно.
