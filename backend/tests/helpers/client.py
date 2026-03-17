"""
Вспомогательные функции для работы с тестовым клиентом.
"""
from typing import Optional, Dict, Any
from fastapi.testclient import TestClient
from httpx import AsyncClient


def make_auth_headers(token: str) -> Dict[str, str]:
    """
    Создает заголовки авторизации.
    
    Args:
        token: JWT токен
        
    Returns:
        Словарь с заголовками
    """
    return {"Authorization": f"Bearer {token}"}


def assert_success_response(response, expected_data: Optional[Dict[str, Any]] = None):
    """
    Проверяет, что ответ успешный.
    
    Args:
        response: Ответ от API
        expected_data: Ожидаемые данные (опционально)
    """
    assert response.status_code in [200, 201], f"Expected success status, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("success") is True, f"Expected success=True, got {data}"
    
    if expected_data:
        for key, value in expected_data.items():
            assert key in data, f"Expected key '{key}' in response"
            assert data[key] == value, f"Expected {key}={value}, got {data[key]}"


def assert_error_response(response, expected_status: int = 400, expected_message: Optional[str] = None):
    """
    Проверяет, что ответ содержит ошибку.
    
    Args:
        response: Ответ от API
        expected_status: Ожидаемый статус код
        expected_message: Ожидаемое сообщение об ошибке (опционально)
    """
    assert response.status_code == expected_status, f"Expected status {expected_status}, got {response.status_code}"
    data = response.json()
    
    if expected_message:
        assert expected_message in str(data.get("detail", "")), f"Expected message '{expected_message}' in response"


def get_response_data(response) -> Dict[str, Any]:
    """
    Извлекает данные из успешного ответа.
    
    Args:
        response: Ответ от API
        
    Returns:
        Словарь с данными
    """
    assert_success_response(response)
    return response.json()


async def async_assert_success_response(response, expected_data: Optional[Dict[str, Any]] = None):
    """
    Асинхронная версия assert_success_response.
    
    Args:
        response: Ответ от AsyncClient
        expected_data: Ожидаемые данные (опционально)
    """
    assert response.status_code in [200, 201], f"Expected success status, got {response.status_code}: {response.text}"
    data = response.json()
    assert data.get("success") is True, f"Expected success=True, got {data}"
    
    if expected_data:
        for key, value in expected_data.items():
            assert key in data, f"Expected key '{key}' in response"
            assert data[key] == value, f"Expected {key}={value}, got {data[key]}"


async def async_get_response_data(response) -> Dict[str, Any]:
    """
    Асинхронная версия get_response_data.
    
    Args:
        response: Ответ от AsyncClient
        
    Returns:
        Словарь с данными
    """
    await async_assert_success_response(response)
    return response.json()
