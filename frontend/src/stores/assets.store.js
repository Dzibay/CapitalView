import { defineStore } from 'pinia'
import assetsService from '../services/assetsService'
import { useDashboardStore } from './dashboard.store'
import { useUIStore } from './ui.store'

export const useAssetsStore = defineStore('assets', {
  actions: {
    async addAsset(assetData) {
      try {
        const res = await assetsService.addAsset(assetData)
        if (res.success && res.asset) {
          const dashboardStore = useDashboardStore()
          
          // Оптимистичное обновление
          dashboardStore.addAssetOptimistic(res.asset, assetData.portfolio_id)
          
          // Фоновая перезагрузка для синхронизации
          dashboardStore.reloadDashboard().catch(err => {
            if (import.meta.env.VITE_APP_DEV) {
              console.error('Ошибка фоновой перезагрузки:', err)
            }
          })
        }
        return res
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления актива:', err)
        }
        throw err
      }
    },

    async removeAsset(portfolioAssetId) {
      if (!confirm("Удалить актив?")) return
      
      try {
        const res = await assetsService.deleteAsset(portfolioAssetId)
        if (!res.success) throw new Error(res.error || 'Ошибка удаления актива')

        const dashboardStore = useDashboardStore()
        
        // Оптимистичное удаление
        dashboardStore.removeAsset(portfolioAssetId)
        
        // Фоновая перезагрузка
        await dashboardStore.reloadDashboard()
        
        return res
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка удаления актива:', err)
        }
        throw err
      }
    },

    async moveAsset({ portfolio_asset_id, target_portfolio_id }) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        uiStore.setLoading(true)
        const res = await assetsService.moveAsset(portfolio_asset_id, target_portfolio_id)
        if (!res.success) throw new Error(res.error || 'Ошибка перемещения актива')
        
        // Полная перезагрузка после перемещения (так как изменяется структура портфелей)
        await dashboardStore.reloadDashboard()
        
        return res
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка перемещения актива:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    },

    async addPrice({ asset_id, price, date }) {
      const uiStore = useUIStore()
      const dashboardStore = useDashboardStore()
      
      try {
        await assetsService.addPrice(asset_id, price, date)
        uiStore.setLoading(true)
        await dashboardStore.reloadDashboard()
      } catch (err) {
        if (import.meta.env.VITE_APP_DEV) {
          console.error('Ошибка добавления цены:', err)
        }
        throw err
      } finally {
        uiStore.setLoading(false)
      }
    }
  }
})

