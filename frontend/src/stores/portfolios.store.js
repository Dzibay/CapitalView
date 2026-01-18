import { defineStore } from 'pinia'
import portfolioService from '../services/portfolioService'
import { useDashboardStore } from './dashboard.store'
import { useUIStore } from './ui.store'

export const usePortfoliosStore = defineStore('portfolios', {
  actions: {
    async addPortfolio(portfolioData) {
      try {
        const res = await portfolioService.addPortfolio(portfolioData)
        if (res.success) {
          const dashboardStore = useDashboardStore()
          // Оптимистичное добавление
          dashboardStore.portfolios.push(res.portfolio)
        }
        return res
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка создания портфеля:', err)
        }
        throw err
      }
    },

    async deletePortfolio(portfolioId) {
      try {
        const res = await portfolioService.deletePortfolio(portfolioId)
        if (!res.success) throw new Error(res.error || 'Ошибка удаления портфеля')
        
        const dashboardStore = useDashboardStore()
        // Оптимистичное удаление
        dashboardStore.removePortfolio(portfolioId)
        
        // Обновляем выбранный портфель, если он был удален
        const uiStore = useUIStore()
        if (uiStore.selectedPortfolioId === portfolioId) {
          const portfolios = dashboardStore.portfolios
          if (portfolios.length > 0) {
            uiStore.setSelectedPortfolioId(portfolios[0].id)
          } else {
            uiStore.setSelectedPortfolioId(null)
          }
        }
        
        return res
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка удаления портфеля:', err)
        }
        throw err
      }
    },

    async clearPortfolio(portfolioId) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        uiStore.setLoading(true)
        const res = await portfolioService.clearPortfolio(portfolioId)
        if (!res.success) throw new Error(res.error || 'Ошибка очистки портфеля')
        
        await dashboardStore.reloadDashboard()
        return res
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка очистки портфеля:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async importPortfolio({ broker_id, token, portfolioId, portfolio_name }) {
      try {
        const res = await portfolioService.importPortfolio(broker_id, token, portfolioId, portfolio_name)
        if (!res.success) throw new Error(res.error || 'Ошибка импорта портфеля')
        return res
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка импорта портфеля:', err)
        }
        throw err
      }
    },

    async updatePortfolioGoal({ portfolioId, title, targetAmount }) {
      try {
        const res = await portfolioService.updatePortfolioGoal(portfolioId, { title, targetAmount })
        if (!res) throw new Error('Ошибка при обновлении цели')

        const updated = res[0]
        const dashboardStore = useDashboardStore()
        
        // Оптимистичное обновление
        dashboardStore.updatePortfolio(portfolioId, {
          description: updated.description,
          capital_target_name: updated.capital_target_name,
          capital_target_value: updated.capital_target_value,
          capital_target_currency: updated.capital_target_currency
        })
        
        return updated
      } catch (err) {
        if (import.meta.env.DEV) {
          console.error('Ошибка обновления цели портфеля:', err)
        }
        throw err
      }
    }
  }
})

