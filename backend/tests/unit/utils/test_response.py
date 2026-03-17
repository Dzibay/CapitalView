"""
Unit тесты для response утилит.
"""
import pytest
from app.utils.response import success_response, error_response
from app.constants import HTTPStatus


@pytest.mark.unit
@pytest.mark.utils
class TestSuccessResponse:
    """Тесты для success_response."""
    
    def test_success_response_with_data(self):
        """Тест успешного ответа с данными."""
        data = {"id": 1, "name": "Test"}
        response = success_response(data=data)
        
        assert response["success"] is True
        assert "id" in response
        assert response["id"] == 1
        assert response["name"] == "Test"
    
    def test_success_response_with_message(self):
        """Тест успешного ответа с сообщением."""
        message = "Operation successful"
        response = success_response(message=message)
        
        assert response["success"] is True
        assert response["message"] == message
    
    def test_success_response_with_list(self):
        """Тест успешного ответа со списком."""
        data = [1, 2, 3]
        response = success_response(data=data)
        
        assert response["success"] is True
        assert response["data"] == data
    
    def test_success_response_empty(self):
        """Тест успешного ответа без данных."""
        response = success_response()
        
        assert response["success"] is True
        assert "data" not in response or response.get("data") is None


@pytest.mark.unit
@pytest.mark.utils
class TestErrorResponse:
    """Тесты для error_response."""
    
    def test_error_response_basic(self):
        """Тест базового ответа с ошибкой."""
        error = "Something went wrong"
        response = error_response(error=error)
        
        assert response["success"] is False
        assert response["error"] == error
    
    def test_error_response_with_details(self):
        """Тест ответа с ошибкой и деталями."""
        error = "Validation failed"
        details = {"field": "email", "message": "Invalid format"}
        response = error_response(error=error, details=details)
        
        assert response["success"] is False
        assert response["error"] == error
        assert response["details"] == details
    
    def test_error_response_with_status_code(self):
        """Тест ответа с ошибкой и статус кодом."""
        error = "Not found"
        response = error_response(error=error, status_code=HTTPStatus.NOT_FOUND)
        
        assert response["success"] is False
        assert response["error"] == error
        # status_code не включается в response, но проверяем что функция принимает его
        assert "status_code" not in response
