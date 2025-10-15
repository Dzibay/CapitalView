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
      return res.data
    },

  // Импорт портфеля из Tinkoff
  async importPortfolio(token, portfolio_id, portfolio_name) {
      const payload = { token, portfolio_id, portfolio_name }
      const res = await axios.post(`${API_URL}/import_tinkoff`, payload, { headers: authHeaders() })
      return res.data
  },

  async clearPortfolio(portfolio_id) {
    const res = await axios.post(`${API_URL}/${portfolio_id}/clear`, {}, { headers: authHeaders() })
    return res.data
  }
}
