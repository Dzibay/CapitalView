import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async getAnalytics() {
    const res = await apiClient.get(API_ENDPOINTS.ANALYTICS.PORTFOLIOS);
    return res.data;
  },
};