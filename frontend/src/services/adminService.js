import apiClient from '../utils/apiClient'
import { API_ENDPOINTS } from '../config/api'

export const adminService = {
  async fetchAdminData() {
    const res = await apiClient.get(API_ENDPOINTS.ADMIN.DATA)
    const d = res.data
    return {
      overview: d?.overview ?? null,
      users_registration_series: Array.isArray(d?.users_registration_series)
        ? d.users_registration_series
        : [],
      users: Array.isArray(d?.users) ? d.users : [],
    }
  },

  /** Дашборд выбранного пользователя (как GET /dashboard/ у него). Только admin. */
  async fetchUserDashboard(userId) {
    const res = await apiClient.get(API_ENDPOINTS.ADMIN.USER_DASHBOARD(userId))
    return res.data?.dashboard ?? null
  },

  async adminRefreshUserPortfolio(userId, portfolioId) {
    const res = await apiClient.post(
      API_ENDPOINTS.ADMIN.USER_PORTFOLIO_REFRESH(userId, portfolioId),
    )
    return res.data
  },

  async adminClearUserPortfolio(userId, portfolioId) {
    const res = await apiClient.post(
      API_ENDPOINTS.ADMIN.USER_PORTFOLIO_CLEAR(userId, portfolioId),
    )
    return res.data
  },

  async adminDeleteUserPortfolio(userId, portfolioId) {
    const res = await apiClient.delete(
      API_ENDPOINTS.ADMIN.USER_PORTFOLIO_DELETE(userId, portfolioId),
    )
    return res.data
  },

  /** Очередь импорта по всем портфелям пользователя с сохранённым ключом брокера. */
  async adminBrokerSyncUserPortfolios(userId) {
    const res = await apiClient.post(API_ENDPOINTS.ADMIN.USER_BROKER_SYNC(userId))
    return res.data
  },

  async fetchSupportMessages() {
    const res = await apiClient.get(API_ENDPOINTS.ADMIN.SUPPORT_MESSAGES)
    const raw = res.data?.support_messages
    return Array.isArray(raw) ? raw : []
  },

  async replySupportMessage(userId, message) {
    const res = await apiClient.post(API_ENDPOINTS.ADMIN.SUPPORT_REPLY, {
      user_id: userId,
      message,
    })
    return res.data?.chat_message ?? null
  },
}
