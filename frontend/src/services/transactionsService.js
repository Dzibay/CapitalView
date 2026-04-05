import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';
import operationsService from './operationsService';

export default {
  async addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, transaction_date, create_deposit_operation = false) {
    // transaction_type: 1=Buy, 2=Sell, 3=Amortization (UI-level)
    // SQL operations_type ids: 1=Buy, 2=Sell, 9=Amortization
    const operation_type_map = {
      1: 1,
      2: 2,
      3: 9,
    };

    const mappedOperationType = operation_type_map[transaction_type];
    if (!mappedOperationType) {
      throw new Error(`Некорректный transaction_type=${transaction_type}`);
    }

    return operationsService.applyOperations([
      {
        operation_type: mappedOperationType,
        operation_date: transaction_date,
        asset_id,
        portfolio_asset_id,
        quantity,
        price,
        create_deposit_operation: !!create_deposit_operation,
      },
    ]);
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

  async deleteTransactions(transaction_ids) {
    const res = await apiClient.delete(API_ENDPOINTS.TRANSACTIONS.BASE, {
      data: { ids: transaction_ids }
    });
    return res.data;
  }
};