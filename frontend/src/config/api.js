/**
 * Конфигурация API endpoints
 * Централизованное управление URL для всех сервисов
 */
export const API_ENDPOINTS = {
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    CHECK_TOKEN: '/auth/check-token',
    UPDATE_PROFILE: '/auth/profile',
  },
  DASHBOARD: {
    BASE: '/dashboard/',
  },
  PORTFOLIO: {
    BASE: '/portfolios/',
    LIST: '/portfolios/',  // Исправлено: на backend это GET /portfolios/ (со слешем!)
    ADD: '/portfolios/',  // Исправлено: на backend это POST /portfolios/ (со слешем!)
    DELETE: (id) => `/portfolios/${id}`,  // Исправлено: на backend это DELETE /portfolios/{id}
    CLEAR: (id) => `/portfolios/${id}/clear`,
    DESCRIPTION: (id) => `/portfolios/${id}/description`,
    ASSETS: (id) => `/portfolios/${id}/assets`,
    HISTORY: (id) => `/portfolios/${id}/history`,
    IMPORT_BROKER: '/portfolios/import-broker',  // Исправлено: на backend это /portfolios/import-broker
  },
  ASSETS: {
    BASE: '/assets/',
    ADD: '/assets/',  // Исправлено: на backend это POST /assets/ (со слешем!)
    DELETE: (id) => `/assets/${id}`,
    ADD_PRICE: '/assets/price',  // Исправлено: на backend это POST /assets/price
    MOVE: (portfolio_asset_id) => `/assets/portfolio/${portfolio_asset_id}/move`,
    GET_INFO: (id) => `/assets/${id}`,
    GET_PRICES: (id) => `/assets/${id}/prices`,
    GET_PORTFOLIO_ASSET_INFO: (portfolio_asset_id) => `/assets/portfolio/${portfolio_asset_id}`,
  },
  TRANSACTIONS: {
    BASE: '/transactions/',
  },
  OPERATIONS: {
    BASE: '/operations/',
  },
  ANALYTICS: {
    BASE: '/analytics',
    PORTFOLIOS: '/analytics/portfolios',
  },
  TASKS: {
    BASE: '/tasks',
    GET: (id) => `/tasks/${id}`,
    STATUS: (id) => `/tasks/${id}/status`,
    USER: '/tasks/user/list',  // Исправлено: на backend это GET /tasks/user/list
    CANCEL: (id) => `/tasks/${id}/cancel`,
  },
};






