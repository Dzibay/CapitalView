/**
 * Конфигурация API endpoints
 * Централизованное управление URL для всех сервисов
 */
export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    CHECK_TOKEN: '/auth/check-token',
  },
  DASHBOARD: {
    BASE: '/dashboard/',
  },
  PORTFOLIO: {
    BASE: '/portfolio',
    LIST: '/portfolio/list',
    ADD: '/portfolio/add',
    DELETE: (id) => `/portfolio/${id}/delete`,
    CLEAR: (id) => `/portfolio/${id}/clear`,
    DESCRIPTION: (id) => `/portfolio/${id}/description`,
    ASSETS: (id) => `/portfolio/${id}/assets`,
    HISTORY: (id) => `/portfolio/${id}/history`,
    IMPORT_BROKER: '/portfolio/import_broker',
  },
  ASSETS: {
    BASE: '/assets',
    ADD: '/assets/add',
    DELETE: (id) => `/assets/${id}`,
    ADD_PRICE: '/assets/add_price',
  },
  TRANSACTIONS: {
    BASE: '/transactions/',
  },
  ANALYTICS: {
    BASE: '/analitics',
    PORTFOLIOS: '/analitics/portfolios',
  },
};

