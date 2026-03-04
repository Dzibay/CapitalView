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
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления транзакции:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async addOperation(operationData, skipReload = false) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await operationsService.addOperation(operationData)
        if (!skipReload) {
          uiStore.setLoading(true)
          await dashboardStore.reloadDashboard()
        }
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления операции:', err)
        }
        throw err
      } finally {
        if (!skipReload) {
          uiStore.setLoading(false)
        }
      }
    },

    async addOperationsBatch(batchData, skipReload = false) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        const result = await operationsService.addOperationsBatch(batchData)
        if (!skipReload) {
          uiStore.setLoading(true)
          await dashboardStore.reloadDashboard()
        }
        return result // Возвращаем результат с датами созданных операций
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка массового добавления операций:', err)
        }
        throw err
      } finally {
        if (!skipReload) {
          uiStore.setLoading(false)
        }
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
        if (import.meta.env.VITE_APP_DEV) {
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
        // Используем batch удаление для оптимизации
        await transactionsService.deleteTransactions(transaction_ids)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка удаления транзакций:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async deleteOperations(operation_ids) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await operationsService.deleteOperations(operation_ids)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка удаления операций:', err)
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

