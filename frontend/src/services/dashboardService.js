import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export async function fetchDashboardData() {
  try {
    const res = await apiClient.get(API_ENDPOINTS.DASHBOARD.BASE);
    return res;
  } catch (error) {
    // Более детальная обработка ошибок
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      const errorMessage = 'Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:5000';
      console.error('Network Error:', errorMessage);
      console.error('Request URL:', error.config?.baseURL + error.config?.url);
      throw new Error(errorMessage);
    }
    console.error('Error fetching dashboard data:', error);
    throw error;
  }
}
