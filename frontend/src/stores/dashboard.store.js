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
    cacheTimeout: 60000, // 1 минута кеширования
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
        
        if (data?.data) {
          this.portfolios = data.data.portfolios || []
          this.transactions = data.data.transactions || []
          this.referenceData = data.data.referenceData || {}
        }
        
        this.lastFetch = Date.now()
        
        if (import.meta.env.DEV) {
          console.log('Dashboard data loaded:', data)
        }
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка получения данных Dashboard:', err)
          if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
            console.error('Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:5000')
          }
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
        Object.assign(portfolio, updates)
      }
    },

    // Удаление портфеля
    removePortfolio(portfolioId) {
      this.portfolios = this.portfolios.filter(p => p.id !== portfolioId)
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
        this.transactions = [
          ...(this.transactions || []),
          ...transactionsArray
        ]
        this.transactionsLoaded = true
      }
    }
  }
})

