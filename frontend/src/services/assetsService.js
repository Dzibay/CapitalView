import axios from "axios";

const API_URL = "http://localhost:5000/api/assets"; // твой сервер

// автоматически добавляем токен
function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

export default {
  async getReferenceData() {
    const res = await axios.get(`${API_URL}/references`, { headers: authHeaders() })
    return res.data
  },

  async addAsset(assetData) {
    const res = await axios.post(`${API_URL}/add`, assetData, { headers: authHeaders() })
    return res.data
  },

  async getAssets() {
    const res = await axios.get(`${API_URL}/get_all`, { headers: authHeaders() })
    console.log(res.data.portfolios)
    return res.data.portfolios
  },

  async deleteAsset(id) {
    const res = await axios.delete(`${API_URL}/delete/${id}`, { headers: authHeaders() })
    return res.data
  },
}
