import apiClient from '../utils/apiClient'
import { API_ENDPOINTS } from '../config/api'

export const billingService = {
  async fetchPublic() {
    const res = await apiClient.get(API_ENDPOINTS.BILLING.PUBLIC)
    return {
      trial_days: Number(res.data?.trial_days ?? 14),
      tariffs: Array.isArray(res.data?.tariffs) ? res.data.tariffs : [],
    }
  },

  async fetchMe() {
    const res = await apiClient.get(API_ENDPOINTS.BILLING.ME)
    return {
      subscription: res.data?.subscription ?? null,
      tariffs: Array.isArray(res.data?.tariffs) ? res.data.tariffs : [],
      trial_days: Number(res.data?.trial_days ?? 14),
      timeline: res.data?.timeline ?? null,
      registered_at: res.data?.registered_at ?? null,
    }
  },

  async createPayment(tariffId, returnUrl) {
    const res = await apiClient.post(API_ENDPOINTS.BILLING.PAYMENTS, {
      tariff_id: tariffId,
      return_url: returnUrl,
    })
    return res.data?.payment ?? null
  },
}
