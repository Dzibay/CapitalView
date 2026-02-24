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
        if (import.meta.env.VITE_APP_DEV) {
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
        const uiStore = useUIStore()
        
        // Собираем все ID портфелей, которые будут удалены (родитель + дочерние)
        const idsToRemove = new Set([portfolioId])
        const findChildren = (parentId) => {
          dashboardStore.portfolios.forEach(p => {
            if (p.parent_portfolio_id === parentId && !idsToRemove.has(p.id)) {
              idsToRemove.add(p.id)
              findChildren(p.id)
            }
          })
        }
        findChildren(portfolioId)
        
        // Оптимистичное удаление (рекурсивно удаляет все дочерние)
        dashboardStore.removePortfolio(portfolioId)
        
        // Обновляем выбранный портфель, если он был удален или был дочерним удаленного
        if (idsToRemove.has(uiStore.selectedPortfolioId)) {
          const portfolios = dashboardStore.portfolios
          // Ищем корневой портфель (без parent_portfolio_id)
          const rootPortfolio = portfolios.find(p => !p.parent_portfolio_id)
          if (rootPortfolio) {
            uiStore.setSelectedPortfolioId(rootPortfolio.id)
          } else if (portfolios.length > 0) {
            uiStore.setSelectedPortfolioId(portfolios[0].id)
          } else {
            uiStore.setSelectedPortfolioId(null)
          }
        }
        
        return res
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
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
        if (import.meta.env.VITE_APP_DEV) {
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
        
        // Возвращаем результат с task_id для отслеживания статуса
        // Теперь импорт выполняется асинхронно через систему задач
        return res
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка импорта портфеля:', err)
        }
        throw err
      }
    },

    async updatePortfolioGoal({ portfolioId, title, targetAmount, monthlyContribution, annualReturn, useInflation, inflationRate }) {
      try {
        const res = await portfolioService.updatePortfolioGoal(portfolioId, { 
          title, 
          targetAmount, 
          monthlyContribution, 
          annualReturn,
          useInflation,
          inflationRate
        })
        
        if (!res) throw new Error('Ошибка при обновлении цели')

        const updated = res[0]
        const dashboardStore = useDashboardStore()
        
        // Оптимистичное обновление
        // Обновляем description с учетом инфляции
        const updatedDescription = {
          ...updated.description,
          use_inflation: updated.use_inflation !== undefined ? updated.use_inflation : (updated.description?.use_inflation || false),
          inflation_rate: updated.inflation_rate !== undefined ? updated.inflation_rate : (updated.description?.inflation_rate || 7.5)
        }
        
        const updateData = {
          description: updatedDescription,
          capital_target_name: updated.capital_target_name,
          capital_target_value: updated.capital_target_value,
          capital_target_currency: updated.capital_target_currency
        }
        
        dashboardStore.updatePortfolio(portfolioId, updateData)
        
        return updated
      } catch (err) {
        console.error('[PortfoliosStore] Ошибка обновления цели портфеля:', err)
        throw err
      }
    }
  }
})

