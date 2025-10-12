import axios from 'axios';

const API_URL = "http://localhost:5000/api/statistics";

export async function fetchPortfolioHistory() {
  try {
    const response = await axios.get(`${API_URL}/portfolio_value`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem('access_token')}`
      }
    });
    console.log('Получем данные о портфелях')
    console.log(response.data)
    return response.data || {};

  } catch (error) {
    console.error('Ошибка при получении статистики портфеля:', error);
    return {};
  }
}
