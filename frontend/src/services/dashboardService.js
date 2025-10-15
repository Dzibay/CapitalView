import axios from "axios";

function authHeaders() {
  const token = localStorage.getItem('access_token')
  return { Authorization: `Bearer ${token}` }
}
const API_URL = 'http://localhost:5000/api/dashboard';

/* === Основная функция === */
export async function fetchDashboardData(user) {
  try {
    const res = await axios.get(`${API_URL}/`, { headers: authHeaders() });
    return res;
  } catch (error) {
    console.error(error);
    return { totalCapital: 0 };
  }
}
