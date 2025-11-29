import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, transaction_date) {
    const payload = {
      asset_id,
      portfolio_asset_id,
      transaction_type,
      quantity,
      price,
      transaction_date
    };

    const res = await apiClient.post(API_ENDPOINTS.TRANSACTIONS.BASE, payload);
    return res.data;
  },

  async getTransactions({ asset_name, portfolio_id, start_date, end_date, limit } = {}) {
    const params = {};

    if (asset_name) params.asset_name = asset_name;
    if (portfolio_id) params.portfolio_id = portfolio_id;
    if (start_date) params.start_date = start_date;
    if (end_date) params.end_date = end_date;
    if (limit) params.limit = limit;

    const res = await apiClient.get(API_ENDPOINTS.TRANSACTIONS.BASE, { params });
    return res.data;
  },

  async editTransaction(updated_transaction) {
    const res = await apiClient.put(API_ENDPOINTS.TRANSACTIONS.BASE, updated_transaction);
    return res.data;
  },

  async deleteTransactions(transaction_ids) {
    const res = await apiClient.delete(API_ENDPOINTS.TRANSACTIONS.BASE, {
      data: { ids: transaction_ids }
    });
    return res.data;
  }
};