import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/assets'

export default {
  // Добавить новый актив / транзакцию
  async addAsset(assetData) {
    console.log('Добавляем')
    const res = await axios.post(`${API_URL}/add`, assetData, { headers: authHeaders() })
    return res.data
  },

  // Удалить актив
  async deleteAsset(assetId) {
    const res = await axios.delete(`${API_URL}/${assetId}`, { headers: authHeaders() })
    return res.data
  },

  async addPrice(asset_id, price, date) {
    const payload = {
      asset_id,
      price,
      date
    }
    const res = await axios.post(`${API_URL}/add_price`, payload, {headers: authHeaders() })
    return res.data
  }
}
