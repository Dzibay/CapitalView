import apiClient from '../utils/apiClient';
import { API_ENDPOINTS } from '../config/api';

export const authService = {
    async register(email, password) {
        return apiClient.post(API_ENDPOINTS.AUTH.REGISTER, { email, password });
    },

    async login(email, password) {
        try {
            const res = await apiClient.post(API_ENDPOINTS.AUTH.LOGIN, { email, password });
            // Сохраняем токен после успешного логина
            if (res.data && res.data.access_token) {
                localStorage.setItem('access_token', res.data.access_token);
                // Проверяем, что токен действительно сохранился
                const savedToken = localStorage.getItem('access_token');
                if (!savedToken) {
                    throw new Error('Не удалось сохранить токен');
                }
            } else {
                throw new Error('Токен не получен от сервера');
            }
            return res;
        } catch (error) {
            // Убеждаемся, что токен не сохраняется при ошибке
            localStorage.removeItem('access_token');
            throw error;
        }
    },

    async checkToken() {
        const token = localStorage.getItem('access_token');
        if (!token) return null;

        try {
            const res = await apiClient.get(API_ENDPOINTS.AUTH.CHECK_TOKEN);
            return res.data;
        } catch (err) {
            // Токен недействителен, очищаем
            localStorage.removeItem('access_token');
            return null;
        }
    },

    async updateProfile(name, email) {
        const data = {};
        if (name !== undefined && name !== null) {
            data.name = name;
        }
        if (email !== undefined && email !== null) {
            data.email = email;
        }
        
        const res = await apiClient.put(API_ENDPOINTS.AUTH.UPDATE_PROFILE, data);
        return res.data;
    },

    logout() {
        localStorage.removeItem('access_token');
    },
};
