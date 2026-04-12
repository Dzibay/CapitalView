// composables/usePortfolioAnalytics.js
import { computed, ref, watch, toValue, isRef } from 'vue'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { expandPortfolioHistoryForCharts } from '../utils/portfolioHistory'

/**
 * @typedef {object} PortfolioAnalyticsOverrides
 * @property {import('vue').MaybeRefOrGetter<Array>} [portfolios] — список портфелей вместо dashboard store
 * @property {import('vue').MaybeRefOrGetter<Array>} [analytics] — массив аналитики как в store (portfolio_id, …)
 * @property {import('vue').Ref<*>} [selectedPortfolioId] — выбранный id вместо ui store (не трогаем глобальный выбор)
 */

/**
 * Composable для работы с аналитикой портфеля
 * Используется на страницах Dashboard и Analytics
 *
 * @param {PortfolioAnalyticsOverrides | null} [overrides]
 */
export function usePortfolioAnalytics(overrides = null) {
  const dashboardStore = useDashboardStore()
  const uiStore = useUIStore()

  const externalSelection = isRef(overrides?.selectedPortfolioId)

  const portfolios = computed(() => {
    if (overrides?.portfolios != null) {
      const v = toValue(overrides.portfolios)
      return Array.isArray(v) ? v : []
    }
    return dashboardStore.portfolios ?? []
  })

  const analyticsList = computed(() => {
    if (overrides?.analytics != null) {
      const v = toValue(overrides.analytics)
      return Array.isArray(v) ? v : []
    }
    return dashboardStore.analytics ?? []
  })

  const effectiveSelectedPortfolioId = computed(() => {
    if (overrides?.selectedPortfolioId != null) {
      return toValue(overrides.selectedPortfolioId)
    }
    return uiStore.selectedPortfolioId
  })

  const selectedPortfolioAnalytics = ref(null)
  const isLoadingAnalytics = ref(false)

  // Получаем выбранный портфель
  const selectedPortfolio = computed(() => {
    const id = effectiveSelectedPortfolioId.value
    return portfolios.value.find(p => p.id === id) || null
  })

  // Функция для сбора всех id выбранного портфеля и его дочерних
  function collectPortfolioIds(portfolio, allPortfolios) {
    let ids = [portfolio.id]
    const children = allPortfolios.filter(p => p.parent_portfolio_id === portfolio.id)

    for (const child of children) {
      ids = ids.concat(collectPortfolioIds(child, allPortfolios))
    }

    return ids
  }

  // Обновление выбранной аналитики
  async function updateSelectedAnalytics() {
    const allAnalytics = analyticsList.value
    const currentId = effectiveSelectedPortfolioId.value
    const portfoliosList = portfolios.value
    const portfolioExists =
      currentId != null && portfoliosList.some((p) => p.id === currentId)

    selectedPortfolioAnalytics.value =
      allAnalytics.find((a) => a.portfolio_id === currentId) || null

    // Fallback и смена выбранного портфеля — только если id битый / портфеля нет в списке.
    // Пустой портфель (без активов) в analytics не попадает (см. dashboard.store) — выбор не трогаем.
    // При внешнем selectedPortfolioId родитель сам выставляет корень / валидный id (админка).
    if (
      !externalSelection &&
      !selectedPortfolioAnalytics.value &&
      allAnalytics.length > 0 &&
      !portfolioExists
    ) {
      selectedPortfolioAnalytics.value = allAnalytics[0]
      if (currentId !== selectedPortfolioAnalytics.value.portfolio_id) {
        uiStore.setSelectedPortfolioId(selectedPortfolioAnalytics.value.portfolio_id)
      }
    }

    if (!selectedPortfolioAnalytics.value && currentId != null && !portfolioExists) {
      console.warn('⚠️ Аналитика не найдена для портфеля', currentId)
    }
  }

  // Безопасная загрузка аналитики
  async function safeLoadAnalytics() {
    if (isLoadingAnalytics.value) return
    try {
      isLoadingAnalytics.value = true
      // Аналитика уже загружена вместе с dashboard, просто обновляем выбранную
      await updateSelectedAnalytics()
    } catch (err) {
      console.error('❌ Ошибка при обработке аналитики:', err)
    } finally {
      isLoadingAnalytics.value = false
    }
  }

  // Автозагрузка аналитики при изменении портфелей
  watch(
    portfolios,
    async (list) => {
      if (list?.length) {
        await safeLoadAnalytics()
      }
    },
    { immediate: true }
  )

  // Перерисовка при смене портфеля
  watch(
    effectiveSelectedPortfolioId,
    async () => {
      await updateSelectedAnalytics()
    }
  )

  // Получение баланса портфеля
  const balance = computed(() => {
    return selectedPortfolio.value?.balance || 
           selectedPortfolio.value?.analytics?.totals?.balance || 
           selectedPortfolioAnalytics.value?.totals?.balance || 
           0
  })

  // Данные для TotalCapitalWidget: капитал = total_value; строка внизу = total_invested + balance; пилюля = нереализ. % к этой базе (total_value − база = unrealized_pl)
  const totalCapitalWidgetData = computed(() => {
    const p = selectedPortfolio.value
    const t =
      selectedPortfolioAnalytics.value?.totals ||
      p?.analytics?.totals ||
      null

    const totalValue =
      t?.total_value != null
        ? Number(t.total_value) || 0
        : Number(p?.total_value) || 0

    const investedInPositions =
      t?.total_invested != null
        ? Number(t.total_invested) || 0
        : Number(p?.total_invested) || 0

    const bal =
      t?.balance != null && Number.isFinite(Number(t.balance))
        ? Number(t.balance)
        : Number(balance.value) || 0

    const investedWithBalance = investedInPositions + bal

    let unrealizedPl = 0
    if (t != null && t.unrealized_pl != null && Number.isFinite(Number(t.unrealized_pl))) {
      unrealizedPl = Number(t.unrealized_pl)
    } else {
      unrealizedPl = totalValue - investedWithBalance
    }

    const unrealizedPercent =
      investedWithBalance > 0 ? (unrealizedPl / investedWithBalance) * 100 : 0

    if (p || t) {
      return {
        totalAmount: totalValue,
        investedAmount: investedWithBalance,
        unrealizedPl,
        unrealizedPercent,
      }
    }

    return {
      totalAmount: 0,
      investedAmount: 0,
      unrealizedPl: 0,
      unrealizedPercent: 0,
    }
  })

  // Данные для PortfolioProfitWidget
  const profitWidgetData = computed(() => {
    if (!selectedPortfolio.value) {
      return {
        totalAmount: 0,
        totalProfit: 0,
        monthlyChange: 0,
        investedAmount: 0,
        analytics: {}
      }
    }

    // Та же база, что у строки «Инвестировано в активы» в TotalCapitalWidget (total_invested + balance)
    const investedForProfitPercent = totalCapitalWidgetData.value.investedAmount

    return {
      totalAmount: selectedPortfolio.value.total_value || 0,
      totalProfit: selectedPortfolio.value.analytics?.totals?.total_profit || 
                   selectedPortfolio.value.analytics?.total_profit || 
                   selectedPortfolioAnalytics.value?.totals?.total_profit || 
                   0,
      monthlyChange: selectedPortfolio.value.monthly_change || 0,
      investedAmount: investedForProfitPercent,
      analytics: selectedPortfolioAnalytics.value || selectedPortfolio.value.analytics || {}
    }
  })

  // Расчет годовых дивидендов: процент доходности * сумма портфеля
  const calculatedAnnualDividends = computed(() => {
    // Используем данные из аналитики, если доступны
    if (selectedPortfolioAnalytics.value?.totals) {
      const returnPercent = selectedPortfolioAnalytics.value.totals.return_percent || 0
      const totalValue = selectedPortfolioAnalytics.value.totals.total_value || 0
      return (returnPercent / 100) * totalValue
    }
    // Иначе используем данные из selectedPortfolio.analytics
    if (selectedPortfolio.value?.analytics) {
      const returnPercent = selectedPortfolio.value.analytics.return_percent || 0
      const totalValue = selectedPortfolio.value.analytics.total_value || selectedPortfolio.value.total_value || 0
      return (returnPercent / 100) * totalValue
    }
    return 0
  })

  // Данные для ReturnWidget
  const returnData = computed(() => {
    // Используем данные из аналитики, если доступны
    if (selectedPortfolioAnalytics.value?.totals) {
      const t = selectedPortfolioAnalytics.value.totals
      const bal = t.balance != null ? t.balance : balance.value
      return {
        returnPercent: t.return_percent || 0,
        returnPercentOnInvested: t.return_percent_on_invested || 0,
        totalValue: t.total_value || 0,
        totalInvested: (t.total_invested || 0) + bal
      }
    }
    // Иначе используем данные из selectedPortfolio.analytics
    if (selectedPortfolio.value?.analytics) {
      return {
        returnPercent: selectedPortfolio.value.analytics.return_percent || 0,
        returnPercentOnInvested: selectedPortfolio.value.analytics.return_percent_on_invested || 0,
        totalValue: selectedPortfolio.value.analytics.total_value || selectedPortfolio.value.total_value || 0,
        totalInvested: selectedPortfolio.value.analytics.total_invested || selectedPortfolio.value.total_invested || 0
      }
    }
    return {
      returnPercent: 0,
      returnPercentOnInvested: 0,
      totalValue: totalCapitalWidgetData.value.totalAmount,
      totalInvested: totalCapitalWidgetData.value.investedAmount
    }
  })

  // Данные для графика динамики капитала (в формате для PortfolioChartWidget)
  const portfolioChartData = computed(() => {
    const sid = effectiveSelectedPortfolioId.value
    if (sid == null) {
      return { labels: [], data_value: [], data_invested: [], data_balance: [] }
    }

    const portfolio = portfolios.value.find(p => p.id === sid)
    const ex = expandPortfolioHistoryForCharts(portfolio?.history)
    return {
      labels: ex.labels,
      data_value: ex.data_value,
      data_invested: ex.data_invested,
      data_balance: ex.data_balance
    }
  })

  // Данные для PortfolioProfitChartWidget
  const profitChartData = computed(() => {
    const ex = expandPortfolioHistoryForCharts(selectedPortfolio.value?.history)
    return {
      labels: ex.labels,
      data_pnl: ex.data_pnl
    }
  })

  return {
    portfolios,
    selectedPortfolio,
    selectedPortfolioAnalytics,
    isLoadingAnalytics,
    balance,
    totalCapitalWidgetData,
    profitWidgetData,
    calculatedAnnualDividends,
    returnData,
    portfolioChartData,
    profitChartData,
    collectPortfolioIds,
    safeLoadAnalytics,
    updateSelectedAnalytics
  }
}
