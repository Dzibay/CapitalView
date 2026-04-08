/**
 * Конфигурация API endpoints
 * Централизованное управление URL для всех сервисов
 */
export const API_ENDPOINTS = {
  ADMIN: {
    STATS_OVERVIEW: '/admin/stats/overview',
  },
  AUTH: {
    REGISTER: '/auth/register',
    LOGIN: '/auth/login',
    CHECK_TOKEN: '/auth/check-token',
    UPDATE_PROFILE: '/auth/profile',
    CHANGE_PASSWORD: '/auth/change-password',
    RESEND_VERIFICATION: '/auth/resend-verification',
  },
  DASHBOARD: {
    BASE: '/dashboard/',
  },
  REFERENCE: {
    BASE: '/reference/',
    VERSION: '/reference/version',
    SEARCH_ASSETS: '/reference/assets/search',
    ASSET_META: (id) => `/reference/assets/${id}`,
  },
  PORTFOLIO: {
    BASE: '/portfolios/',
    LIST: '/portfolios/',  // Исправлено: на backend это GET /portfolios/ (со слешем!)
    ADD: '/portfolios/',  // Исправлено: на backend это POST /portfolios/ (со слешем!)
    DELETE: (id) => `/portfolios/${id}`,  // Исправлено: на backend это DELETE /portfolios/{id}
    CLEAR: (id) => `/portfolios/${id}/clear`,
    REFRESH: (id) => `/portfolios/${id}/refresh`,
    DESCRIPTION: (id) => `/portfolios/${id}/description`,
    ASSETS: (id) => `/portfolios/${id}/assets`,
    HISTORY: (id) => `/portfolios/${id}/history`,
    IMPORT_BROKER: '/portfolios/import-broker',  // Исправлено: на backend это /portfolios/import-broker
    BROKERS: '/portfolios/brokers',  // Получение списка брокеров
    BROKER_CREDENTIALS: (id) => `/portfolios/${id}/broker-credentials`,
    PAYOUT_POSITIONS: (id) => `/portfolios/${id}/payout-positions`,
  },
  ASSETS: {
    BASE: '/assets/',
    ADD: '/assets/',  // Исправлено: на backend это POST /assets/ (со слешем!)
    DELETE: (id) => `/assets/${id}`,
    ADD_PRICE: '/assets/price',  // Исправлено: на backend это POST /assets/price
    ADD_PRICES_BATCH: '/assets/prices/batch',  // Массовое добавление цен
    MOVE: (portfolio_asset_id) => `/assets/portfolio/${portfolio_asset_id}/move`,
    GET_INFO: (id) => `/assets/${id}`,
    GET_PRICES: (id) => `/assets/${id}/prices`,
    GET_PORTFOLIO_ASSET_INFO: (portfolio_asset_id) => `/assets/portfolio/${portfolio_asset_id}`,
    GET_DAILY_VALUES: (portfolio_asset_id) => `/assets/portfolio/${portfolio_asset_id}/daily-values`,
  },
  TRANSACTIONS: {
    BASE: '/transactions/',
  },
  OPERATIONS: {
    BASE: '/operations/',
    APPLY: '/operations/apply',
    APPLY_UPDATES: '/operations/apply-updates',
    UPDATE: (id) => `/operations/${id}`,  // PATCH — обновление операции (дата/сумма)
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
  MISSED_PAYOUTS: {
    BASE: '/missed-payouts',
  },
  SUPPORT: {
    MESSAGE: '/support/message',
  },
};






