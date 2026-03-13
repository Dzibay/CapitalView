import { defineStore } from 'pinia'
import transactionsService from '../services/transactionsService'
import operationsService from '../services/operationsService'
import { useDashboardStore } from './dashboard.store'

export const useTransactionsStore = defineStore('transactions', {
  actions: {
    async addTransaction({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date, transaction_date, create_deposit_operation = false }) {
      const dashboardStore = useDashboardStore()
      
      try {
        // Используем transaction_date если есть, иначе date
        const txDate = transaction_date || date
        await transactionsService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, txDate, create_deposit_operation)
        dashboardStore.reloadDashboard(false).catch(err => {
          if (import.meta.env.VITE_APP_DEV) {
            console.error('Ошибка обновления dashboard после добавления транзакции:', err)
          }
        })
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления транзакции:', err)
        }
        throw err
      }
    },

    async addOperation(operationData, skipReload = false) {
      const dashboardStore = useDashboardStore()
      
      try {
        const result = await operationsService.addOperation(operationData)
        if (!skipReload) {
          dashboardStore.reloadDashboard(false).catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления dashboard после добавления операции:', err)
            }
          })
        }
        return result
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления операции:', err)
        }
        throw err
      }
    },

    async addOperationsBatch(batchData, skipReload = false) {
      const dashboardStore = useDashboardStore()
      
      try {
        const result = await operationsService.addOperationsBatch(batchData)
        if (!skipReload) {
          dashboardStore.reloadDashboard(false).catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления dashboard после добавления операций:', err)
            }
          })
        }
        return result
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка массового добавления операций:', err)
        }
        throw err
      }
    },

    async editTransaction(updated_transaction) {
      try {
        await transactionsService.editTransaction(updated_transaction)
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка редактирования транзакции:', err)
        }
        throw err
      }
    },

    async deleteTransactions(transaction_ids) {
      const dashboardStore = useDashboardStore()
      
      try {
        // Используем batch удаление для оптимизации
        await transactionsService.deleteTransactions(transaction_ids)
        // Удаляем транзакции из кэша
        dashboardStore.removeTransactions(transaction_ids)
        // Обновляем dashboard_data в фоне без показа загрузочного экрана
        dashboardStore.reloadDashboard(false).catch(err => {
          if (import.meta.env.VITE_APP_DEV) {
            console.error('Ошибка обновления dashboard после удаления транзакций:', err)
          }
        })
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка удаления транзакций:', err)
        }
        throw err
      }
    },

    async deleteOperations(operation_ids) {
      const dashboardStore = useDashboardStore()
      
      try {
        await operationsService.deleteOperations(operation_ids)
        // Удаляем операции из кэша
        dashboardStore.removeOperations(operation_ids)
        // Обновляем dashboard_data в фоне без показа загрузочного экрана
        dashboardStore.reloadDashboard(false).catch(err => {
          if (import.meta.env.VITE_APP_DEV) {
            console.error('Ошибка обновления dashboard после удаления операций:', err)
          }
        })
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка удаления операций:', err)
        }
        throw err
      }
    },

  }
})

