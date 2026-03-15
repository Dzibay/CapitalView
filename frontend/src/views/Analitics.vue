<script setup>
import PortfolioSelector from '../components/PortfolioSelector.vue'
import LoadingState from '../components/base/LoadingState.vue'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'

// Виджеты
import { 
  TotalCapitalWidget, 
  PortfolioProfitWidget, 
  DividendsWidget, 
  ReturnWidget 
} from '../components/widgets/stats'
import { 
  PayoutsChartWidget,
  PayoutsByAssetChartWidget,
  PortfoliosDistributionChartWidget,
  AnalyticsAssetDistributionWidget,
  MonthlyFlowChartWidget,
  PortfolioChartWidget,
  AssetReturnsChartWidget,
  PortfolioProfitChartWidget
} from '../components/widgets/charts'
import { WidgetContainer } from '../components/widgets/base'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import { usePortfolioAnalytics } from '../composables/usePortfolioAnalytics'

// Используем stores
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

// Используем composable для аналитики портфеля
const {
  portfolios,
  selectedPortfolio,
  selectedPortfolioAnalytics,
  isLoadingAnalytics,
  totalCapitalWidgetData,
  profitWidgetData,
  calculatedAnnualDividends,
  returnData,
  portfolioChartData,
  profitChartData
} = usePortfolioAnalytics()
</script>

<template>
  <PageLayout v-if="!uiStore.loading">
    <PageHeader 
      title="Финансовая аналитика"
      subtitle="Сводные показатели"
    >
      <template #actions>
        <PortfolioSelector 
          :portfolios="portfolios"
          :modelValue="uiStore.selectedPortfolioId"
          @update:modelValue="uiStore.setSelectedPortfolioId"
        />
      </template>
    </PageHeader>

    <LoadingState v-if="isLoadingAnalytics" message="Загрузка аналитики..." />

    <div v-else-if="selectedPortfolioAnalytics" class="widgets-grid">
      <!-- 4 маленьких виджета вверху -->
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <TotalCapitalWidget 
          :total-amount="totalCapitalWidgetData.totalAmount"
          :invested-amount="totalCapitalWidgetData.investedAmount"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <PortfolioProfitWidget 
          :total-amount="profitWidgetData.totalAmount"
          :total-profit="profitWidgetData.totalProfit"
          :monthly-change="profitWidgetData.monthlyChange"
          :invested-amount="profitWidgetData.investedAmount"
          :analytics="profitWidgetData.analytics"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <DividendsWidget 
          :annual-dividends="calculatedAnnualDividends"
        />
      </WidgetContainer>
      <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
        <ReturnWidget 
          :return-percent="returnData.returnPercent"
          :return-percent-on-invested="returnData.returnPercentOnInvested"
          :total-value="returnData.totalValue"
          :total-invested="returnData.totalInvested"
        />
      </WidgetContainer>

      <!-- Виджет распределения активов и виджет динамики прибыли -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-xlarge)">
        <PortfolioChartWidget 
          :chart-data="portfolioChartData"
        />
      </WidgetContainer>
      
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-large)">
        <AnalyticsAssetDistributionWidget 
          :asset-distribution="selectedPortfolioAnalytics.asset_distribution || []"
          layout="horizontal"
        />
      </WidgetContainer>

      <!-- Виджет динамики прибыли -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-xlarge)">
        <PortfolioProfitChartWidget 
          :chartData="profitChartData"
        />
      </WidgetContainer>

      <!-- Остальные графики -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
        <AssetReturnsChartWidget 
          :asset-returns="selectedPortfolioAnalytics.asset_returns || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="Полученные выплаты по месяцам"
          :payouts="selectedPortfolioAnalytics.monthly_payouts || []"
          mode="past"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsChartWidget 
          title="График будущих выплат"
          :payouts="selectedPortfolioAnalytics.future_payouts || []"
          mode="future"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
        <MonthlyFlowChartWidget 
          :monthly-flow="selectedPortfolioAnalytics.monthly_flow || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PayoutsByAssetChartWidget 
          :payouts-by-asset="selectedPortfolioAnalytics.payouts_by_asset || []"
        />
      </WidgetContainer>

      <WidgetContainer :gridColumn="6" minHeight="var(--widget-height-medium)">
        <PortfoliosDistributionChartWidget 
          :portfolios="portfolios"
          :all-portfolios="dashboardStore.analytics || []"
          :selected-portfolio-id="uiStore.selectedPortfolioId"
        />
      </WidgetContainer>
    </div>

    <LoadingState v-else />
  </PageLayout>
</template>

<style scoped>
.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: min-content;
}

/* Адаптивность для планшетов */
@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

/* Адаптивность для мобильных */
@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
  }
}
</style>
