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

    console.log('[PortfolioService] updatePortfolioGoal payload:', payload);

    const response = await apiClient.post(API_ENDPOINTS.PORTFOLIO.DESCRIPTION(portfolioId), payload);
    
    console.log('[PortfolioService] updatePortfolioGoal response:', response.data);
    
    if (response.data.success) {
      const result = response.data.description;
      console.log('[PortfolioService] updatePortfolioGoal result:', result);
      return result;
    } else {
      throw new Error(response.data.error || 'Ошибка при обновлении цели');
    }
  }
};
