// src/services/assetsService.js
import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/'

export default {
  // Получить все портфели с активами
  async getAll() {
    const res = await axios.get(`${API_URL}/get_all`, { headers: authHeaders() })
    return res.data
  },

  // Добавить новый актив / транзакцию
  async addAsset(assetData) {
    const res = await axios.post(`${API_URL}/add`, assetData, { headers: authHeaders() })
    return res.data
  },

  // Продать актив
  async sellAsset(portfolio_asset_id, quantity, price, date) {
    const payload = { portfolio_asset_id, quantity, price, date }
    const res = await axios.post(`${API_URL}/sell`, payload, { headers: authHeaders() })
    return res.data
  },

  // Удалить актив
  async deleteAsset(assetId) {
    const res = await axios.delete(`${API_URL}/delete/${assetId}`, { headers: authHeaders() })
    return res.data
  },

  // Получить справочные данные для формы (типы активов, валюты, существующие активы)
  async getReferences() {
    const res = await axios.get(`${API_URL}/references`, { headers: authHeaders() })
    return res.data
  },

  // Импорт портфеля из Tinkoff
  async importPortfolio(token, portfolioId, portfolio_name) {
    const payload = { token, portfolioId, portfolio_name }
    const res = await axios.post(`${API_URL}/import_tinkoff_portfolio`, payload, { headers: authHeaders() })
    return res.data
  }
}
