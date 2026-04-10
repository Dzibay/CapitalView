import { defineStore } from 'pinia'
import portfolioService from '../services/portfolioService'
import { useDashboardStore } from './dashboard.store'
import { getRootPortfolioIds } from '../utils/portfolioSubtree'

/** Одна общая загрузка при параллельных вызовах (Strict Mode / повторный mount). */
let fetchPayoutPositionsInFlight = null

export const useDividendsStore = defineStore('dividends', {
  state: () => ({
    /**
     * Все позиции с выплатами по дереву пользователя: один RPC на каждый корневой портфель
     * (SQL get_portfolio_payout_positions уже обходит поддерево от переданного id).
     * У каждой позиции есть portfolio_id — фильтр по выбранному портфелю на клиенте.
     */
    payoutPositionsFlat: [],
    payoutPositionsLoading: false,
  }),

  getters: {
    payoutPositionsCacheIsEmpty: (state) => state.payoutPositionsFlat.length === 0,
  },

  actions: {
    clearPayoutPositionsCache() {
      this.payoutPositionsFlat = []
    },

    /**
     * Загружает выплаты: по одному запросу на каждый корневой портфель (обычно один).
     * Не вызывает payout-positions отдельно для каждого подпортфеля.
     */
    async fetchPayoutPositionsForAllPortfolios() {
      if (fetchPayoutPositionsInFlight) {
        return fetchPayoutPositionsInFlight
      }

      const dashboardStore = useDashboardStore()
      const portfolios = dashboardStore.portfolios || []
      const rootIds = getRootPortfolioIds(portfolios)
      if (!rootIds.length) {
        this.payoutPositionsFlat = []
        return
      }

      fetchPayoutPositionsInFlight = (async () => {
        this.payoutPositionsLoading = true
        try {
          const results = await Promise.all(
            rootIds.map(async (id) => {
              try {
                const positions = await portfolioService.getPayoutPositions(id)
                return positions || []
              } catch (e) {
                if (import.meta.env.VITE_APP_DEV) console.error(e)
                return []
              }
            })
          )
          this.payoutPositionsFlat = results.flat()
        } finally {
          this.payoutPositionsLoading = false
          fetchPayoutPositionsInFlight = null
        }
      })()

      return fetchPayoutPositionsInFlight
    },
  },
})
