import apiClient from '../utils/apiClient'
import { API_ENDPOINTS } from '../config/api'

export const adminService = {
  async fetchStatsOverview() {
    const res = await apiClient.get(API_ENDPOINTS.ADMIN.STATS_OVERVIEW)
    return res.data?.overview ?? null
  },
}
