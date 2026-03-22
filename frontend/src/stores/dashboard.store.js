import { defineStore } from 'pinia'
import { fetchDashboardData } from '../services/dashboardService'
import { fetchReferenceData } from '../services/referenceService'
import operationsService from '../services/operationsService'
import transactionsService from '../services/transactionsService'
import { useUIStore } from './ui.store'

/** Один общий Promise на параллельные fetchDashboard (Strict Mode / двойной mount). */
let dashboardFetchInFlight = null

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    portfolios: [],
    recentTransactions: [], // Последние 5 транзакций из dashboard (для виджета)
    transactions: [],       // Полный список транзакций (загружается лениво)
    operations: [],          // Полный список операций (загружается лениво)
    referenceData: {},
    analytics: [],
    missedPayoutsCount: 0,
    lastFetch: null,
    cacheTimeout: parseInt(import.meta.env.VITE_DASHBOARD_CACHE_TIMEOUT || '60000', 10),
    fullListsLoaded: false,  // Полные списки транзакций и операций загружены
    analyticsLoaded: false
  }),

  getters: {
    rootPortfolio: (state) => 
      state.portfolios.find(p => !p.parent_portfolio_id),
    
    portfolioById: (state) => (id) =>
      state.portfolios.find(p => p.id === id),
    
    hasData: (state) => state.portfolios.length > 0,
    
    data: (state) => ({
      portfolios: state.portfolios,
      recent_transactions: state.recentTransactions,
      referenceData: state.referenceData,
      analytics: state.analytics
    })
  },

  actions: {
    async fetchDashboard(force = false, showLoading = true) {
      const uiStore = useUIStore()

      if (!force && this.lastFetch &&
          Date.now() - this.lastFetch < this.cacheTimeout) {
        return
      }

      if (dashboardFetchInFlight) {
        return dashboardFetchInFlight
      }

      dashboardFetchInFlight = (async () => {
        if (showLoading) {
          uiStore.setLoading(true)
        }
        try {
          const [dashBody, refBody] = await Promise.all([
            fetchDashboardData(),
            fetchReferenceData({ bypassCache: force }).catch(() => null)
          ])

          if (import.meta.env.DEV && import.meta.env.VITE_DEBUG_DASHBOARD_DATA) {
            console.log('📊 Dashboard:', JSON.parse(JSON.stringify(dashBody)))
          }

          if (dashBody?.dashboard) {
            const d = dashBody.dashboard
            this.portfolios = d.portfolios || []
            this.recentTransactions = d.recent_transactions || []
            if (!this.fullListsLoaded) {
              this.transactions = this.recentTransactions
            }
            this.missedPayoutsCount = d.missed_payouts_count || 0

            this.analytics = (d.portfolios || [])
              .filter(p => p.analytics && Object.keys(p.analytics).length > 0)
              .map(p => ({
                portfolio_id: p.id,
                portfolio_name: p.name,
                ...p.analytics
              }))
            this.analyticsLoaded = true
          }

          if (refBody?.reference) {
            this.referenceData = refBody.reference
          }

          this.lastFetch = Date.now()
        } catch (err) {
          if (import.meta.env.VITE_APP_DEV && (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error'))) {
            console.error('Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:5000')
          }
          throw err
        } finally {
          if (showLoading) {
            uiStore.setLoading(false)
          }
          dashboardFetchInFlight = null
        }
      })()

      return dashboardFetchInFlight
    },

    async reloadDashboard(showLoading = true) {
      await this.fetchDashboard(true, showLoading)
      // После мутаций всегда обновляем полные списки, если они были загружены
      if (this.fullListsLoaded) {
        this.fetchTransactionsAndOperationsInBackground()
      }
    },

    /**
     * Загружает полные списки транзакций и операций в фоне (не блокирует UI).
     * Списки всегда заменяются актуальными данными с сервера (избегаем дубликатов после редактирования).
     * @returns {Promise<void>} — можно await для ожидания завершения загрузки
     */
    fetchTransactionsAndOperationsInBackground() {
      return Promise.all([
        transactionsService.getTransactions({ limit: 2000 }).catch(err => {
          if (import.meta.env.VITE_APP_DEV) console.error('Фоновая загрузка транзакций:', err)
          return null
        }),
        operationsService.getOperations({ limit: 2000 }).catch(err => {
          if (import.meta.env.VITE_APP_DEV) console.error('Фоновая загрузка операций:', err)
          return null
        })
      ]).then(([txResponse, opResponse]) => {
        if (txResponse != null) {
          const list = txResponse?.transactions || txResponse || []
          const normalized = list.map(tx => ({
            ...tx,
            id: tx.id || tx.transaction_id,
            transaction_id: tx.transaction_id || tx.id,
            transaction_type: tx.transaction_type || tx.transaction_type_name
          }))
          this.addTransactions(normalized, true)
        }
        if (opResponse != null) {
          const list = opResponse?.operations || opResponse || []
          this.addOperations(list, true)
        }
        this.fullListsLoaded = true
      })
    },

    // Оптимистичное обновление: добавляем актив локально без перезагрузки
    addAssetOptimistic(asset, portfolioId) {
      const portfolio = this.portfolios.find(p => p.id === portfolioId)
      if (portfolio) {
        if (!portfolio.assets) portfolio.assets = []
        
        const existingAsset = portfolio.assets.find(
          a => a.portfolio_asset_id === asset.portfolio_asset_id
        )
        
        if (existingAsset) {
          Object.assign(existingAsset, {
            quantity: asset.quantity,
            average_price: asset.average_price,
            last_price: asset.last_price,
            total_value: Math.round(asset.quantity * asset.last_price * 100) / 100
          })
        } else {
          portfolio.assets.push({
            ...asset,
            total_value: Math.round(asset.quantity * asset.last_price * 100) / 100
          })
        }
      }
    },

    // Обновление портфеля после изменений
    updatePortfolio(portfolioId, updates) {
      const portfolio = this.portfolios.find(p => p.id === portfolioId)
      if (portfolio) {
        // Если обновляется description, нужно правильно его слить
        if (updates.description) {
          portfolio.description = {
            ...(portfolio.description || {}),
            ...updates.description
          }
        }
        
        // Обновляем остальные поля
        Object.keys(updates).forEach(key => {
          if (key !== 'description') {
            portfolio[key] = updates[key]
          }
        })
      }
    },

    // Удаление портфеля и всех его дочерних портфелей
    removePortfolio(portfolioId) {
      // Собираем все ID портфелей для удаления (сам портфель + все дочерние)
      const idsToRemove = new Set([portfolioId])
      
      // Рекурсивно находим все дочерние портфели
      const findChildren = (parentId) => {
        this.portfolios.forEach(p => {
          if (p.parent_portfolio_id === parentId && !idsToRemove.has(p.id)) {
            idsToRemove.add(p.id)
            findChildren(p.id) // Рекурсивно ищем детей детей
          }
        })
      }
      
      findChildren(portfolioId)
      
      // Удаляем все найденные портфели
      this.portfolios = this.portfolios.filter(p => !idsToRemove.has(p.id))
    },

    // Удаление актива из всех портфелей
    removeAsset(portfolioAssetId) {
      this.portfolios.forEach(portfolio => {
        if (portfolio.assets) {
          portfolio.assets = portfolio.assets.filter(
            asset => asset.portfolio_asset_id !== portfolioAssetId
          )
        }
      })
    },

    // Добавление аналитики
    addAnalytics(analyticsArray) {
      if (Array.isArray(analyticsArray)) {
        this.analytics = [
          ...(this.analytics || []),
          ...analyticsArray
        ]
        this.analyticsLoaded = true
      }
    },

    // Замена полного списка транзакций
    addTransactions(transactionsArray, replace = false) {
      if (!Array.isArray(transactionsArray)) return
      if (replace || this.transactions.length === 0) {
        this.transactions = transactionsArray
      } else {
        const existingIds = new Set(this.transactions.map(t => t.id || t.transaction_id))
        const newTransactions = transactionsArray.filter(t => !existingIds.has(t.id || t.transaction_id))
        if (newTransactions.length > 0) {
          this.transactions = [...this.transactions, ...newTransactions]
        }
      }
    },

    // Замена полного списка операций
    addOperations(operationsArray, replace = false) {
      if (!Array.isArray(operationsArray)) return
      const sorted = [...operationsArray].sort((a, b) => {
        const dateA = new Date(a.operation_date || a.date || 0).getTime()
        const dateB = new Date(b.operation_date || b.date || 0).getTime()
        return dateB - dateA
      })
      if (replace || this.operations.length === 0) {
        this.operations = sorted
      } else {
        const existingIds = new Set(this.operations.map(op => op.id || op.cash_operation_id || op.operation_id))
        const newOperations = sorted.filter(op => !existingIds.has(op.id || op.cash_operation_id || op.operation_id))
        if (newOperations.length > 0) {
          this.operations = [...this.operations, ...newOperations].sort((a, b) => {
            const dateA = new Date(a.operation_date || a.date || 0).getTime()
            const dateB = new Date(b.operation_date || b.date || 0).getTime()
            return dateB - dateA
          })
        }
      }
    },

    // Удаление транзакций из кэша
    removeTransactions(transactionIds) {
      if (Array.isArray(transactionIds)) {
        this.transactions = this.transactions.filter(
          tx => !transactionIds.includes(tx.id || tx.transaction_id)
        )
      }
    },

    // Удаление операций из кэша
    removeOperations(operationIds) {
      if (Array.isArray(operationIds)) {
        this.operations = this.operations.filter(
          op => !operationIds.includes(op.id || op.cash_operation_id)
        )
      }
    }
  }
})

