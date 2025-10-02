import axios from "axios";

const API_URL = "http://localhost:5000"; // твой сервер

export default {
  async getAssets() {
    const token = localStorage.getItem("access_token");
    if (!token) throw new Error("Нет токена");

    const res = await axios.get(`${API_URL}/assets/get_all`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    return res.data.assets || []; // ожидаем { assets: [...] } с сервера
  },
};
