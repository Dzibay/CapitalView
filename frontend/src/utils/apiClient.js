import axios from 'axios';

/**
 * Оптимизированное получение базового URL.
 * Если API на том же домене, лучше использовать относительный путь.
 */
function getApiBaseUrl() {
  if (import.meta.env.DEV) {
    // В разработке (Vite) обычно используем прокси или полный URL
    return import.meta.env.VITE_API_BASE_URL || '/api/v1';
  }
  // В продакшене используем относительный путь. 
  // Браузер сам подставит текущий протокол (https) и домен.
  return '/api/v1'; 
}

const apiClient = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: parseInt(import.meta.env.VITE_API_TIMEOUT || '30000', 10),
});

apiClient.interceptors.request.use(
  (config) => {
    // Исправление Mixed Content: 
    // Если мы на HTTPS, убеждаемся, что URL запроса не начинается с http://
    if (typeof window !== 'undefined' && window.location.protocol === 'https:') {
      if (config.url?.startsWith('http://')) {
        config.url = config.url.replace('http://', 'https://');
      }
      // Если baseURL был задан как http, исправляем его
      if (config.baseURL?.startsWith('http://')) {
        config.baseURL = config.baseURL.replace('http://', 'https://');
      }
    }

    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    // Обработка 401 (Unauthorized)
    if (error.response?.status === 401) {
      const isAuthRoute = error.config?.url?.includes('/auth/');
      
      if (!isAuthRoute) {
        localStorage.removeItem('access_token');
        // Используем router.push, если есть доступ к роутеру, 
        // но window.location тоже рабочий вариант для жесткого ресета состояния
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;