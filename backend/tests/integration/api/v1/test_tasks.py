"""
Интеграционные тесты для API endpoints задач.
"""
import pytest
from unittest.mock import patch
from tests.helpers.client import assert_success_response, assert_error_response, get_response_data
@pytest.mark.integration
@pytest.mark.api
class TestTasksGet:
    """Тесты для получения задач."""
    
    def test_get_task_success(self, authenticated_client, mock_user):
        """Тест успешного получения задачи."""
        test_task = {
            "id": 1,
            "portfolio_id": 10,
            "status": "pending",
            "type": "import"
        }
        
        with patch('app.api.v1.tasks.get_task', return_value=test_task):
            with patch('app.api.v1.tasks.import_task_belongs_to_user', return_value=True):
                response = authenticated_client.get("/api/v1/tasks/1")
                data = get_response_data(response)
                assert "task" in data
                assert data["task"]["id"] == 1
    
    def test_get_task_not_found(self, authenticated_client):
        """Тест получения несуществующей задачи."""
        with patch('app.api.v1.tasks.get_task', return_value=None):
            response = authenticated_client.get("/api/v1/tasks/99999")
            assert_error_response(response, expected_status=404)
    
    def test_get_task_unauthorized(self, authenticated_client, mock_user):
        """Тест получения задачи другого пользователя."""
        test_task = {
            "id": 1,
            "portfolio_id": 10,
            "status": "pending"
        }
        
        with patch('app.api.v1.tasks.get_task', return_value=test_task):
            with patch('app.api.v1.tasks.import_task_belongs_to_user', return_value=False):
                response = authenticated_client.get("/api/v1/tasks/1")
                assert_error_response(response, expected_status=403)
    
    def test_get_user_tasks_success(self, authenticated_client, mock_user):
        """Тест успешного получения списка задач пользователя."""
        test_tasks = [
            {"id": 1, "portfolio_id": 1, "status": "pending"},
            {"id": 2, "portfolio_id": 2, "status": "completed"}
        ]
        
        with patch('app.api.v1.tasks.get_user_tasks', return_value=test_tasks):
            response = authenticated_client.get("/api/v1/tasks/user/list")
            data = get_response_data(response)
            assert "tasks" in data
            assert len(data["tasks"]) == 2


@pytest.mark.integration
@pytest.mark.api
class TestTasksStatus:
    """Тесты для работы со статусом задач."""
    
    def test_get_task_status_success(self, authenticated_client, mock_user):
        """Тест успешного получения статуса задачи."""
        test_task = {
            "id": 1,
            "portfolio_id": 1,
            "status": "in_progress"
        }
        
        with patch('app.api.v1.tasks.get_task', return_value=test_task):
            with patch('app.api.v1.tasks.import_task_belongs_to_user', return_value=True):
                response = authenticated_client.get("/api/v1/tasks/1/status")
                data = get_response_data(response)
                assert "status" in data
                assert data["status"] == "in_progress"
    
    def test_cancel_task_success(self, authenticated_client, mock_user):
        """Тест успешной отмены задачи."""
        test_task = {
            "id": 1,
            "portfolio_id": 1,
            "status": "pending"
        }
        
        with patch('app.api.v1.tasks.get_task', return_value=test_task):
            with patch('app.api.v1.tasks.cancel_task', return_value=True):
                response = authenticated_client.post("/api/v1/tasks/1/cancel")
                assert_success_response(response)
