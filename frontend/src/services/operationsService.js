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
    // success_response(data={ operations }) даёт { success, operations } на верхнем уровне
    const raw = res.data?.data?.operations ?? res.data?.operations;
    return Array.isArray(raw) ? raw : [];
  },

  async addOperation(operationData) {
    // Унифицированно: все создание операций делаем через /operations/apply
    const res = await apiClient.post(API_ENDPOINTS.OPERATIONS.APPLY, { operations: [operationData] });
    return res.data;
  },
  
  async applyOperations(operations) {
    const res = await apiClient.post(API_ENDPOINTS.OPERATIONS.APPLY, { operations });
    return res.data;
  },

  async deleteOperations(operation_ids) {
    const res = await apiClient.delete(API_ENDPOINTS.OPERATIONS.BASE, {
      data: { ids: operation_ids }
    });
    return res.data;
  },

  async updateOperation(operation_id, { operation_date, amount, quantity, price }) {
    return this.updateOperationsBatch([
      { operation_id, operation_date, amount, quantity, price },
    ])
  },
  async updateOperationsBatch(updates) {
    const res = await apiClient.patch(API_ENDPOINTS.OPERATIONS.APPLY_UPDATES, {
      updates,
    });
    return res.data;
  },
};
