import axios from 'axios';

const API_URL = 'http://localhost:5000/auth';

export const authService = {
    async register(email, password) {
        return axios.post(`${API_URL}/register`, { email, password });
    },

    async login(email, password) {
        return axios.post(`${API_URL}/login`, { email, password });
    },

    async checkToken() {
        console.log("Привет, это debug");
        const token = localStorage.getItem('access_token');
        if (!token) return null;

        try {
            const res = await axios.get(`${API_URL}/check-token`, {
            headers: { Authorization: `Bearer ${token}` },
            });
            console.log("Токен успешный");
            return res.data; // если всё ок, возвращаем пользователя
        } catch (err) {
            console.log("Токен не успешный");
            console.error("Token check error:", err.response ? err.response.data : err.message);
            // можно удалить недействительный токен
            localStorage.removeItem('access_token');
            return null; // возвращаем null, чтобы фронт знал, что токен недействителен
        }
    },

    logout() {
        localStorage.removeItem('access_token');
    },
};
