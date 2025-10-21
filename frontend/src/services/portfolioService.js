import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/portfolio'

export default {
  async addPortfolio(data) {
    console.log('добавление портфеля')
    const res = await axios.post(`${API_URL}/add`, data, { headers: authHeaders() })
    console.log(res)
    return res.data
  },

  // Импорт портфеля из Tinkoff
  async importPortfolio(broker_id, token, portfolio_id, portfolio_name) {
      const payload = { broker_id, token, portfolio_id, portfolio_name }
      const res = await axios.post(`${API_URL}/import_broker`, payload, { headers: authHeaders() })
      return res.data
  },

  async deletePortfolio(portfolio_id) {
    const res = await axios.delete(`${API_URL}/${portfolio_id}/delete`, { headers: authHeaders() })
    return res.data
  },

  async clearPortfolio(portfolio_id) {
    const res = await axios.post(`${API_URL}/${portfolio_id}/clear`, {}, { headers: authHeaders() })
    return res.data
  },

  async updatePortfolioGoal(portfolioId, { title, targetAmount }) {
    const payload = {
      text: title,
      capital_target_name: title,
      capital_target_value: targetAmount
    };

    const response = await axios.post(`${API_URL}/${portfolioId}/description`, payload, { headers: authHeaders() });
    if (response.data.success) {
      return response.data.description;
    } else {
      throw new Error(response.data.error || 'Ошибка при обновлении цели');
    }
  }
}
