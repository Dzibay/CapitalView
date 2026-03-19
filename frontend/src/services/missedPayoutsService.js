import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async getMissedPayouts(portfolio_id = null) {
    const params = {};
    if (portfolio_id) params.portfolio_id = portfolio_id;
    
    // FastAPI-маршрут объявлен как GET "/" внутри prefix "/missed-payouts",
    // поэтому необходим trailing slash, иначе будет 307 redirect.
    const res = await apiClient.get(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/`, { params });
    return res.data?.data?.missed_payouts || res.data?.missed_payouts || [];
  },

  async deleteMissedPayout(missed_payout_id) {
    const res = await apiClient.delete(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/${missed_payout_id}`);
    return res.data;
  },

  async deleteMissedPayoutsBatch(missed_payout_ids) {
    // FastAPI Body(...) без embed=True ожидает массив напрямую
    const res = await apiClient.delete(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/batch`, {
      data: missed_payout_ids
    });
    return res.data;
  },

  async checkMissedPayouts(portfolio_asset_id) {
    const res = await apiClient.post(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/check/${portfolio_asset_id}`);
    return res.data;
  },

  async checkMissedPayoutsForPortfolio(portfolio_id) {
    const res = await apiClient.post(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/check-portfolio/${portfolio_id}`);
    return res.data;
  },

  async checkMissedPayoutsForUser() {
    const res = await apiClient.post(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/check-user`);
    return res.data;
  },

  async addOperationsFromMissedPayoutsBatch(missed_payout_ids) {
    // Создает операции выплат из списка неполученных выплат батчем
    // FastAPI Body(...) без embed=True ожидает массив напрямую
    const res = await apiClient.post(`${API_ENDPOINTS.MISSED_PAYOUTS.BASE}/add-operations-batch`, missed_payout_ids);
    return res.data;
  }
};
