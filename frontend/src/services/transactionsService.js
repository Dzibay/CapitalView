import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/transactions'

export default {
  async addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, transaction_date) {
    // формируем объект данных
    const payload = {
      asset_id,
      portfolio_asset_id,
      transaction_type,
      quantity,
      price,
      transaction_date
    };

    console.log("📤 Отправляем транзакцию:", payload);

    // отправляем POST-запрос
    const res = await axios.post(`${API_URL}/`, payload, {
      headers: authHeaders(),
    });

    return res.data;
  },

  // 🔹 Получить транзакции с фильтрацией
  async getTransactions({ asset_name, portfolio_id, start_date, end_date }) {
    const params = {}

    if (asset_name) params.asset_name = asset_name
    if (portfolio_id) params.portfolio_id = portfolio_id
    if (start_date) params.start_date = start_date
    if (end_date) params.end_date = end_date

    const res = await axios.get(`${API_URL}/`, {
      headers: authHeaders(),
      params
    })
    console.log('Транзакции загружены')

    return res.data
  },
};