import { defineStore } from 'pinia'
import { fetchDashboardData } from '../services/dashboardService'
import { useUIStore } from './ui.store'

export const useDashboardStore = defineStore('dashboard', {
  state: () => ({
    portfolios: [],
    transactions: [],
    referenceData: {},
    analytics: [],
    lastFetch: null,
    cacheTimeout: parseInt(import.meta.env.VITE_DASHBOARD_CACHE_TIMEOUT || '60000', 10), // Время кеширования из env или 1 минута по умолчанию
    transactionsLoaded: false,
    analyticsLoaded: false
  }),

  getters: {
    rootPortfolio: (state) => 
      state.portfolios.find(p => !p.parent_portfolio_id),
    
    portfolioById: (state) => (id) =>
      state.portfolios.find(p => p.id === id),
    
    hasData: (state) => state.portfolios.length > 0,
    
    // Для обратной совместимости с текущим форматом dashboardData.value.data
    data: (state) => ({
      portfolios: state.portfolios,
      transactions: state.transactions,
      referenceData: state.referenceData,
      analytics: state.analytics
    })
  },

  actions: {
    async fetchDashboard(force = false) {
      const uiStore = useUIStore()
      
      // Кеширование: не загружаем, если данные свежие
      if (!force && this.lastFetch && 
          Date.now() - this.lastFetch < this.cacheTimeout) {
        return
      }

      uiStore.setLoading(true)
      try {
        const data = await fetchDashboardData()
        
        // Выводим dashboard data в консоль для отладки
        if (import.meta.env.VITE_DEBUG_DASHBOARD_DATA) {
          console.log('📊 Dashboard Data:', JSON.parse(JSON.stringify(data)))
          
        }
        
        if (data?.data) {
          this.portfolios = data.data.portfolios || []
          // Транзакции теперь приходят вместе с dashboard
          this.transactions = data.data.transactions || []
          this.transactionsLoaded = true
          this.referenceData = data.data.referenceData || {}
          
          // Аналитика теперь приходит в полном формате из get_user_portfolios_analytics
          // Она уже в правильном формате с totals, monthly_flow, monthly_payouts, asset_distribution, etc.
          // Извлекаем аналитику из портфелей
          this.analytics = (data.data.portfolios || [])
            .filter(p => p.analytics && Object.keys(p.analytics).length > 0)
            .map(p => ({
              portfolio_id: p.id,
              portfolio_name: p.name,
              ...p.analytics  // Распаковываем всю аналитику (totals, monthly_flow, monthly_payouts, etc.)
            }))
          this.analyticsLoaded = true
        }
        
        this.lastFetch = Date.now()
        
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV && (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error'))) {
            console.error('Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:5000')
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async reloadDashboard() {
      return this.fetchDashboard(true)
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

    // Добавление транзакций
    addTransactions(transactionsArray) {
      if (Array.isArray(transactionsArray)) {
        // Если транзакции еще не загружены, заменяем массив
        // Если уже загружены, добавляем к существующим (для обновления)
        if (this.transactionsLoaded && this.transactions.length > 0) {
          this.transactions = [
            ...this.transactions,
            ...transactionsArray
          ]
        } else {
          this.transactions = transactionsArray
        }
        this.transactionsLoaded = true
      }
    }
  }
})

