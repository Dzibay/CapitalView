import { defineStore } from 'pinia'
import { adminService } from '../services/adminService'
import { useUIStore } from './ui.store'

let adminDataFetchInFlight = null
let supportMessagesFetchInFlight = null

export const useAdminStore = defineStore('admin', {
  state: () => ({
    overview: null,
    usersSeries: [],
    adminUsers: [],
    adminDataLastFetch: null,
    adminDataError: '',

    supportMessages: [],
    supportMessagesLastFetch: null,
    supportMessagesError: '',

    cacheTimeout: parseInt(import.meta.env.VITE_ADMIN_CACHE_TIMEOUT || '60000', 10),
  }),

  getters: {
    hasFreshAdminData(state) {
      return (
        state.adminDataLastFetch != null &&
        Date.now() - state.adminDataLastFetch < state.cacheTimeout
      )
    },
    hasFreshSupportMessages(state) {
      return (
        state.supportMessagesLastFetch != null &&
        Date.now() - state.supportMessagesLastFetch < state.cacheTimeout
      )
    },
  },

  actions: {
    async fetchAdminData(force = false, showLoading = false) {
      const uiStore = useUIStore()

      if (!force && this.hasFreshAdminData) {
        return
      }

      if (adminDataFetchInFlight) {
        return adminDataFetchInFlight
      }

      adminDataFetchInFlight = (async () => {
        if (showLoading) {
          uiStore.setLoading(true)
        }
        this.adminDataError = ''
        try {
          const { overview, users_registration_series: series, users } =
            await adminService.fetchAdminData()
          this.overview = overview
          this.usersSeries = series
          this.adminUsers = users
          this.adminDataLastFetch = Date.now()
        } catch (e) {
          this.adminDataError =
            e.response?.data?.error || e.message || 'Не удалось загрузить статистику'
          throw e
        } finally {
          if (showLoading) {
            uiStore.setLoading(false)
          }
          adminDataFetchInFlight = null
        }
      })()

      return adminDataFetchInFlight
    },

    async fetchSupportMessages(force = false, showLoading = false) {
      const uiStore = useUIStore()

      if (!force && this.hasFreshSupportMessages) {
        return
      }

      if (supportMessagesFetchInFlight) {
        return supportMessagesFetchInFlight
      }

      supportMessagesFetchInFlight = (async () => {
        if (showLoading) {
          uiStore.setLoading(true)
        }
        this.supportMessagesError = ''
        try {
          const list = await adminService.fetchSupportMessages()
          this.supportMessages = list
          this.supportMessagesLastFetch = Date.now()
        } catch (e) {
          this.supportMessagesError =
            e.response?.data?.error || e.message || 'Не удалось загрузить сообщения'
          throw e
        } finally {
          if (showLoading) {
            uiStore.setLoading(false)
          }
          supportMessagesFetchInFlight = null
        }
      })()

      return supportMessagesFetchInFlight
    },
  },
})
