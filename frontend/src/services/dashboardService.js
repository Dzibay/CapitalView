import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

/* === Основная функция === */
export async function fetchDashboardData() {
    try {
      const res = await apiClient.get(API_ENDPOINTS.DASHBOARD.BASE, {});
      return res.data;
    } catch (error) {
      console.error(error);
      return { totalCapital: 0 };
    }
  }
