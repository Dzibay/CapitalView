import { defineStore } from 'pinia'
import transactionsService from '../services/transactionsService'
import operationsService from '../services/operationsService'
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

    async addOperation(operationData) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await operationsService.addOperation(operationData)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка добавления операции:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async addOperationsBatch(batchData) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await operationsService.addOperationsBatch(batchData)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка массового добавления операций:', err)
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
      // Транзакции теперь загружаются вместе с dashboard
      // Эта функция оставлена для обратной совместимости, но не делает ничего
      const dashboardStore = useDashboardStore()
      if (dashboardStore.transactionsLoaded) return
      // Если транзакции еще не загружены, они будут загружены при следующем fetchDashboard
    },

    async loadAnalytics() {
      // Аналитика теперь загружается вместе с dashboard
      // Эта функция оставлена для обратной совместимости, но не делает ничего
      const dashboardStore = useDashboardStore()
      if (dashboardStore.analyticsLoaded) return
      // Если аналитика еще не загружена, она будет загружена при следующем fetchDashboard
    }
  }
})

