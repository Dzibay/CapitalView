import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export const supportService = {
  async sendMessage(message) {
    const res = await apiClient.post(API_ENDPOINTS.SUPPORT.MESSAGE, { message });
    return res.data;
  },
};
