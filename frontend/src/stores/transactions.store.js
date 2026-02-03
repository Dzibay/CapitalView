import { defineStore } from 'pinia'
import transactionsService from '../services/transactionsService'
import analyticsService from '../services/analyticsService'
import { useDashboardStore } from './dashboard.store'
import { useUIStore } from './ui.store'

export const useTransactionsStore = defineStore('transactions', {
  actions: {
    async addTransaction({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date, transaction_date }) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        // Используем transaction_date если есть, иначе date
        const txDate = transaction_date || date
        await transactionsService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, txDate)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка добавления транзакции:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async editTransaction(updated_transaction) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await transactionsService.editTransaction(updated_transaction)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка редактирования транзакции:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async deleteTransactions(transaction_ids) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await transactionsService.deleteTransactions(transaction_ids)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка удаления транзакций:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async preloadTransactions() {
      const dashboardStore = useDashboardStore()
      
      if (dashboardStore.transactionsLoaded) return
      
      try {
        const response = await transactionsService.getTransactions({})
        // API возвращает объект с полем transactions
        const transactions = response?.transactions || response || []
        dashboardStore.addTransactions(transactions)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error("Ошибка фоновой загрузки транзакций:", err)
        }
      }
    },

    async loadAnalytics() {
      const dashboardStore = useDashboardStore()
      
      if (dashboardStore.analyticsLoaded) return

      try {
        const res = await analyticsService.getAnalytics()
        const analyticsArray = Array.isArray(res?.analytics) ? res.analytics : []
        dashboardStore.addAnalytics(analyticsArray)
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error("❌ Ошибка загрузки аналитики:", err)
        }
      }
    }
  }
})

