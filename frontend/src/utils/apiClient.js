/**
 * Единый API клиент для всех запросов к backend
 * Устраняет дублирование authHeaders и базового URL
 */
import axios from 'axios';

// В режиме разработки используем прокси из Vite, в продакшене - полный URL
const API_BASE_URL = import.meta.env.PROD 
  ? (import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api/v1')
  : '/api/v1';

// Создаем экземпляр axios с базовой конфигурацией
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // 30 секунд таймаут
});

// Interceptor для добавления токена авторизации к каждому запросу
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers = config.headers || {};
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Interceptor для обработки ошибок авторизации и сетевых ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Обработка сетевых ошибок
    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      console.error('Network Error: Backend server may be down or unreachable');
      console.error('Attempted URL:', error.config?.baseURL + error.config?.url);
      // Не перенаправляем на логин при сетевой ошибке, просто пробрасываем ошибку
      return Promise.reject(error);
    }
    
    // Обработка ошибок авторизации
    if (error.response?.status === 401) {
      const isAuthRoute = error.config?.url?.includes('/auth/login') || 
                         error.config?.url?.includes('/auth/register');
      
      if (!isAuthRoute) {
        localStorage.removeItem('access_token');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

