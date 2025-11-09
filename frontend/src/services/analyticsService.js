import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/analitics'

export default {
  // Добавить новый актив / транзакцию
  async getAnalytics() {
    const res = await axios.get(`${API_URL}/portfolios`, { headers: authHeaders() })
    return res.data
  },
}