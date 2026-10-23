import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

const TERMINAL_STATUSES = ['completed', 'failed', 'cancelled'];

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
  },

  /**
   * Ждёт завершения задачи (completed / failed / cancelled) и возвращает её последний статус.
   * Сетевые сбои не прерывают ожидание; через timeoutMs возвращает последний известный статус.
   */
  async waitForTask(taskId, { interval = 2500, timeoutMs = 15 * 60 * 1000, onUpdate } = {}) {
    const deadline = Date.now() + timeoutMs;
    let last = null;
    while (Date.now() < deadline) {
      try {
        last = await this.getTaskStatus(taskId);
        if (onUpdate) onUpdate(last);
        if (TERMINAL_STATUSES.includes(last?.status)) return last;
      } catch (error) {
        if (error.response?.status === 404) return { status: 'failed', error_message: 'Задача не найдена' };
      }
      await new Promise((resolve) => setTimeout(resolve, interval));
    }
    return last;
  }
};
