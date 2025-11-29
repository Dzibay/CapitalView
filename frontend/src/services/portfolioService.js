import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async addPortfolio(data) {
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.ADD, data);
    return res.data;
  },

  async importPortfolio(broker_id, token, portfolio_id, portfolio_name) {
    const payload = { broker_id, token, portfolio_id, portfolio_name };
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.IMPORT_BROKER, payload);
    return res.data;
  },

  async deletePortfolio(portfolio_id) {
    const res = await apiClient.delete(API_ENDPOINTS.PORTFOLIO.DELETE(portfolio_id));
    return res.data;
  },

  async clearPortfolio(portfolio_id) {
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.CLEAR(portfolio_id), {});
    return res.data;
  },

  async updatePortfolioGoal(portfolioId, { title, targetAmount }) {
    const payload = {
      text: title,
      capital_target_name: title,
      capital_target_value: targetAmount
    };

    const response = await apiClient.post(API_ENDPOINTS.PORTFOLIO.DESCRIPTION(portfolioId), payload);
    if (response.data.success) {
      return response.data.description;
    } else {
      throw new Error(response.data.error || 'Ошибка при обновлении цели');
    }
  }
};
