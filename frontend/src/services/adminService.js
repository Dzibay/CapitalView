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

  async fetchSupportMessages() {
    const res = await apiClient.get(API_ENDPOINTS.ADMIN.SUPPORT_MESSAGES)
    const raw = res.data?.support_messages
    return Array.isArray(raw) ? raw : []
  },
}
