import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async getOperations({ portfolio_id, start_date, end_date, limit } = {}) {
    const params = {};

    if (portfolio_id) params.portfolio_id = portfolio_id;
    if (start_date) params.start_date = start_date;
    if (end_date) params.end_date = end_date;
    if (limit) params.limit = limit;

    const res = await apiClient.get(API_ENDPOINTS.OPERATIONS.BASE, { params });
    return res.data;
  }
};
