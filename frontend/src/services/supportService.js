import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export const supportService = {
  async fetchMessages() {
    const res = await apiClient.get(API_ENDPOINTS.SUPPORT.MESSAGES);
    const raw = res.data?.messages;
    return Array.isArray(raw) ? raw : [];
  },

  async sendMessage(message) {
    const res = await apiClient.post(API_ENDPOINTS.SUPPORT.MESSAGE, { message });
    return res.data;
  },
};
