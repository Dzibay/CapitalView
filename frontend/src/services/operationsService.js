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
    // API возвращает { success: true, data: { operations: [...] } }
    return res.data?.data?.operations || res.data?.operations || res.data || [];
  },

  async addOperation(operationData) {
    const res = await apiClient.post(API_ENDPOINTS.OPERATIONS.BASE, operationData);
    return res.data;
  },

  async addOperationsBatch(batchData) {
    const res = await apiClient.post(API_ENDPOINTS.OPERATIONS.BATCH, batchData);
    return res.data;
  },

  async deleteOperations(operation_ids) {
    const res = await apiClient.delete(API_ENDPOINTS.OPERATIONS.BASE, {
      data: { ids: operation_ids }
    });
    return res.data;
  },

  async updateOperation(operation_id, { operation_date, amount }) {
    const payload = {};
    if (operation_date != null) payload.operation_date = operation_date;
    if (amount != null) payload.amount = amount;
    const res = await apiClient.patch(API_ENDPOINTS.OPERATIONS.UPDATE(operation_id), payload);
    return res.data;
  }
};
