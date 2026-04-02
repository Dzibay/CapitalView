// composables/usePortfolioAnalytics.js
import { computed, ref, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { expandPortfolioHistoryForCharts } from '../utils/portfolioHistory'

/**
 * Composable для работы с аналитикой портфеля
 * Используется на страницах Dashboard и Analytics
 */
export function usePortfolioAnalytics() {
  const dashboardStore = useDashboardStore()
  const uiStore = useUIStore()

  const portfolios = computed(() => dashboardStore.portfolios ?? [])
  const selectedPortfolioAnalytics = ref(null)
  const isLoadingAnalytics = ref(false)

  // Получаем выбранный портфель
  const selectedPortfolio = computed(() => {
    return portfolios.value.find(p => p.id === uiStore.selectedPortfolioId) || null
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
    const allAnalytics = dashboardStore.analytics ?? []
    const currentId = uiStore.selectedPortfolioId
    const portfoliosList = dashboardStore.portfolios ?? []
    const portfolioExists =
      currentId != null && portfoliosList.some((p) => p.id === currentId)

    selectedPortfolioAnalytics.value =
      allAnalytics.find((a) => a.portfolio_id === currentId) || null

    // Fallback и смена выбранного портфеля — только если id битый / портфеля нет в списке.
    // Пустой портфель (без активов) в analytics не попадает (см. dashboard.store) — выбор не трогаем.
    if (!selectedPortfolioAnalytics.value && allAnalytics.length > 0 && !portfolioExists) {
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
    () => dashboardStore.portfolios,
    async (portfolios) => {
      if (portfolios?.length) {
        await safeLoadAnalytics()
      }
    },
    { immediate: true }
  )

  // Перерисовка при смене портфеля
  watch(
    () => uiStore.selectedPortfolioId,
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

  // Данные для TotalCapitalWidget
  const totalCapitalWidgetData = computed(() => {
    // Приоритет: selectedPortfolioAnalytics > selectedPortfolio
    if (selectedPortfolioAnalytics.value?.totals) {
      const totalInvested = selectedPortfolioAnalytics.value.totals.total_invested || 0
      return {
        totalAmount: selectedPortfolioAnalytics.value.totals.total_value || 0,
        investedAmount: totalInvested + balance.value
      }
    }
    
    if (selectedPortfolio.value) {
      const totalInvested = selectedPortfolio.value.total_invested || 0
      return {
        totalAmount: selectedPortfolio.value.total_value || 0,
        investedAmount: totalInvested + balance.value
      }
    }

    return {
      totalAmount: 0,
      investedAmount: 0
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

    return {
      totalAmount: selectedPortfolio.value.total_value || 0,
      totalProfit: selectedPortfolio.value.analytics?.totals?.total_profit || 
                   selectedPortfolio.value.analytics?.total_profit || 
                   selectedPortfolioAnalytics.value?.totals?.total_profit || 
                   0,
      monthlyChange: selectedPortfolio.value.monthly_change || 0,
      investedAmount: (selectedPortfolio.value.total_invested || 0) + balance.value,
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
      return {
        returnPercent: selectedPortfolioAnalytics.value.totals.return_percent || 0,
        returnPercentOnInvested: selectedPortfolioAnalytics.value.totals.return_percent_on_invested || 0,
        totalValue: selectedPortfolioAnalytics.value.totals.total_value || 0,
        totalInvested: selectedPortfolioAnalytics.value.totals.total_invested || 0
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
    if (!uiStore.selectedPortfolioId) {
      return { labels: [], data_value: [], data_invested: [], data_balance: [] }
    }

    const portfolio = portfolios.value.find(p => p.id === uiStore.selectedPortfolioId)
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
