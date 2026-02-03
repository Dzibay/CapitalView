import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  /**
   * Получает статус задачи импорта
   */
  async getTaskStatus(taskId) {
    const res = await apiClient.get(API_ENDPOINTS.TASKS.STATUS(taskId));
    return res.data;
  },

  /**
   * Получает информацию о задаче
   */
  async getTask(taskId) {
    const res = await apiClient.get(API_ENDPOINTS.TASKS.GET(taskId));
    return res.data;
  },

  /**
   * Получает список задач пользователя
   */
  async getUserTasks(limit = 50) {
    const res = await apiClient.get(API_ENDPOINTS.TASKS.USER, {
      params: { limit }
    });
    return res.data;
  },

  /**
   * Отменяет задачу
   */
  async cancelTask(taskId) {
    const res = await apiClient.post(API_ENDPOINTS.TASKS.CANCEL(taskId));
    return res.data;
  }
};
