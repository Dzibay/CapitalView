"""
Фикстуры для работы с базой данных в тестах.
"""
import pytest
from typing import List, Dict, Any
from unittest.mock import Mock, patch


@pytest.fixture
def mock_db_query_result():
    """
    Мок результата запроса к БД.
    Возвращает список словарей.
    """
    def _create_result(data: List[Dict[str, Any]]):
        return data
    return _create_result


@pytest.fixture
def empty_db_result():
    """Пустой результат запроса к БД."""
    return []


@pytest.fixture
def mock_single_row_result():
    """Мок результата с одной строкой."""
    return [{"id": 1, "name": "Test"}]


@pytest.fixture
def mock_multiple_rows_result():
    """Мок результата с несколькими строками."""
    return [
        {"id": 1, "name": "Test 1"},
        {"id": 2, "name": "Test 2"},
        {"id": 3, "name": "Test 3"}
    ]
