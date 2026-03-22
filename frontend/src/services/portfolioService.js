import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export default {
  async addPortfolio(data) {
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.ADD, data);
    return res.data;
  },

  async getBrokers() {
    const res = await apiClient.get(API_ENDPOINTS.PORTFOLIO.BROKERS);
    // Структура ответа: { success: true, brokers: [...] } (data объединяется с корнем)
    if (res.data && res.data.success && res.data.brokers) {
      return res.data.brokers;
    }
    return [];
  },

  async importPortfolio(broker_id, token, portfolio_id, portfolio_name) {
    const payload = { broker_id, token, portfolio_id, portfolio_name };
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.IMPORT_BROKER, payload);
    return res.data;
    // Теперь возвращает { success: true, task_id: 123, status: 'pending' }
  },

  async deletePortfolio(portfolio_id) {
    const res = await apiClient.delete(API_ENDPOINTS.PORTFOLIO.DELETE(portfolio_id));
    return res.data;
  },

  async clearPortfolio(portfolio_id) {
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.CLEAR(portfolio_id), {});
    return res.data;
  },

  async refreshPortfolio(portfolio_id) {
    const res = await apiClient.post(API_ENDPOINTS.PORTFOLIO.REFRESH(portfolio_id), {});
    return res.data;
  },

  async getBrokerCredentials(portfolio_id) {
    const res = await apiClient.get(API_ENDPOINTS.PORTFOLIO.BROKER_CREDENTIALS(portfolio_id));
    return { broker_id: res.data.broker_id, api_key: res.data.api_key };
  },

  async getPayoutPositions(portfolio_id) {
    const res = await apiClient.get(API_ENDPOINTS.PORTFOLIO.PAYOUT_POSITIONS(portfolio_id));
    return res.data.positions || [];
  },

  async updatePortfolioGoal(portfolioId, { title, targetAmount, monthlyContribution, annualReturn, useInflation, inflationRate }) {
    const payload = {
      text: title || '',
      capital_target_name: title || '',
      capital_target_value: targetAmount,
      monthly_contribution: monthlyContribution,
      annual_return: annualReturn,
      use_inflation: useInflation || false,
      inflation_rate: inflationRate || 7.5
    };

    const response = await apiClient.post(API_ENDPOINTS.PORTFOLIO.DESCRIPTION(portfolioId), payload);
    
    if (response.data.success) {
      return response.data.description;
    } else {
      throw new Error(response.data.error || 'Ошибка при обновлении цели');
    }
  }
};
