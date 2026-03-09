import { defineStore } from 'pinia'
import transactionsService from '../services/transactionsService'
import operationsService from '../services/operationsService'
import analyticsService from '../services/analyticsService'
import { useDashboardStore } from './dashboard.store'
import { useUIStore } from './ui.store'

// Вспомогательная функция для поиска portfolio_id
function findPortfolioId(portfolios, portfolioId, portfolioAssetId) {
  // Если portfolio_id уже есть, возвращаем его
  if (portfolioId) {
    return portfolioId
  }
  
  // Ищем через portfolio_asset_id
  if (portfolioAssetId) {
    const portfolio = portfolios.find(p => 
      p.assets?.some(a => a.portfolio_asset_id === portfolioAssetId)
    )
    return portfolio?.id
  }
  
  return null
}

export const useTransactionsStore = defineStore('transactions', {
  actions: {
    async addTransaction({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date, transaction_date, create_deposit_operation = false }) {
      const dashboardStore = useDashboardStore()
      
      try {
        // Используем transaction_date если есть, иначе date
        const txDate = transaction_date || date
        await transactionsService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, txDate, create_deposit_operation)
        
        // Обновляем dashboard_data в фоне без показа загрузочного экрана
        // reloadDashboard уже загружает транзакции, поэтому отдельный запрос getTransactions не нужен
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
        
        // Обновляем список операций в store только если они уже загружены
        // Если операции не загружены, они будут загружены при следующем открытии страницы операций
        if (!skipReload && dashboardStore.operationsLoaded) {
          try {
            // Получаем portfolio_id используя вспомогательную функцию
            const portfolioId = findPortfolioId(
              dashboardStore.portfolios,
              operationData.portfolio_id,
              operationData.portfolio_asset_id
            )
            
            // Загружаем операции с фильтром по портфелю (если есть)
            // Если portfolio_id нет, загружаем все операции
            const operationsResponse = await operationsService.getOperations({ 
              portfolio_id: portfolioId || undefined,
              limit: 1000 
            })
            
            const operations = Array.isArray(operationsResponse) 
              ? operationsResponse 
              : (operationsResponse?.data?.operations || operationsResponse?.operations || [])
            
            if (operations.length > 0) {
              // addOperations автоматически избегает дубликатов и устанавливает operationsLoaded = true
              dashboardStore.addOperations(operations)
            }
          } catch (err) {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления списка операций в store:', err)
            }
            // Продолжаем выполнение, даже если обновление store не удалось
          }
        }
        
        // Обновляем dashboard_data в фоне без показа загрузочного экрана
        // Это обновит транзакции, если операция создала транзакцию (Buy/Sell)
        if (!skipReload) {
          dashboardStore.reloadDashboard(false).catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления dashboard после добавления операции:', err)
            }
          })
        }
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
          // Обновляем dashboard_data в фоне без показа загрузочного экрана
          dashboardStore.reloadDashboard(false).catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка обновления dashboard после добавления операций:', err)
            }
          })
        }
        return result // Возвращаем результат с датами созданных операций
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка массового добавления операций:', err)
        }
        throw err
      }
    },

    async editTransaction(updated_transaction) {
      const dashboardStore = useDashboardStore()
      
      try {
        await transactionsService.editTransaction(updated_transaction)
        // Обновляем dashboard_data в фоне без показа загрузочного экрана
        dashboardStore.reloadDashboard(false).catch(err => {
          if (import.meta.env.VITE_APP_DEV) {
            console.error('Ошибка обновления dashboard после редактирования транзакции:', err)
          }
        })
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

