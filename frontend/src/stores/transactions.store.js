import { defineStore } from 'pinia'
import transactionsService from '../services/transactionsService'
import operationsService from '../services/operationsService'
import { useDashboardStore } from './dashboard.store'

export const useTransactionsStore = defineStore('transactions', {
  state: () => ({
    /** Показать шкалу дат на странице транзакций (сохраняется в localStorage) */
    showPeriodTrack: false,
    viewMode: 'transactions',
    selectedAsset: '',
    assetSearch: '',
    recentAssets: [],
    /** Пустой массив = все портфели (по имени, как в данных транзакций) */
    selectedPortfolio: [],
    /** Пустой массив = все типы */
    selectedType: [],
    selectedCurrency: 'RUB',
    periodPreset: 'all',
    startDate: '',
    endDate: '',
    globalSearch: '',
  }),

  persist: ['showPeriodTrack'],

  actions: {
    resetFilters() {
      this.selectedAsset = ''
      this.assetSearch = ''
      this.selectedPortfolio = []
      this.selectedType = []
      this.globalSearch = ''
      this.periodPreset = 'all'
      this.startDate = ''
      this.endDate = ''
    },
    async addTransaction({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date, transaction_date, create_deposit_operation = false, skipReload = false }) {
      const dashboardStore = useDashboardStore()
      
      try {
        // Используем transaction_date если есть, иначе date
        const txDate = transaction_date || date
        await transactionsService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, txDate, create_deposit_operation)
        if (!skipReload) {
          dashboardStore.reloadDashboard(false).catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления dashboard после добавления транзакции:', err)
            }
          })
        }
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

