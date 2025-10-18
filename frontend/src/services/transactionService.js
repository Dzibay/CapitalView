import axios from 'axios'

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}

const API_URL = 'http://localhost:5000/api/portfolio'

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
    const res = await axios.post(`${API_URL}/add_transaction`, payload, {
      headers: authHeaders(),
    });

    return res.data;
  }
};