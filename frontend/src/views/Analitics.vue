<script setup>
import { onMounted } from 'vue'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import LoadingState from '../components/base/LoadingState.vue'
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'

// Виджеты
import { 
  TotalCapitalWidget, 
  PortfolioProfitWidget, 
  DividendsWidget, 
  ReturnWidget,
  ConsolidatedStatsWidget
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

// Composable для аналитики портфеля
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
  profitChartData,
  safeLoadAnalytics
} = usePortfolioAnalytics()

// При прямом переходе на /analitics данные могут ещё не загрузиться — подстраховка
onMounted(async () => {
  if (!portfolios.value?.length) {
    await dashboardStore.fetchDashboard(false, false)
    await safeLoadAnalytics()
  }
})

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

    <div v-else-if="!portfolios.length" class="empty-state">
      <p>Нет портфелей для отображения аналитики.</p>
    </div>

    <div v-else-if="selectedPortfolioAnalytics" class="widgets-grid">
      <!-- Статы: на десктопе — 4 виджета, на мобильном — один сводный -->
      <div class="stats-desktop">
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
      </div>
      <div class="stats-mobile">
        <WidgetContainer gridColumn="1" minHeight="var(--widget-height-small)">
          <ConsolidatedStatsWidget
            :total-amount="totalCapitalWidgetData.totalAmount"
            :invested-amount="totalCapitalWidgetData.investedAmount"
            :total-profit="profitWidgetData.totalProfit"
            :monthly-change="profitWidgetData.monthlyChange"
            :analytics="profitWidgetData.analytics"
            :annual-dividends="calculatedAnnualDividends"
            :return-percent="returnData.returnPercent"
            :return-percent-on-invested="returnData.returnPercentOnInvested"
          />
        </WidgetContainer>
      </div>

      <!-- Динамика капитала и динамика прибыли — одинаковая высота (large) -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-large)">
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

      <!-- Виджет динамики прибыли (та же высота, что и динамика капитала) -->
      <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-large)">
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

    <div v-else class="empty-state">
      <p>Нет данных аналитики для выбранного портфеля.</p>
    </div>
  </PageLayout>
</template>

<style scoped>
.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: min-content;
  width: 100%;
  min-width: 0;
}

.stats-desktop {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(12, 1fr);
  gap: var(--spacing);
}
.stats-mobile {
  display: none;
  grid-column: 1 / -1;
}

/* Планшет: статы 2x2 (как на дашборде), остальные виджеты на всю ширину */
@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .stats-desktop {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }
  .stats-desktop :deep(.widget-container) {
    grid-column: span 1 !important;
  }
  .widgets-grid > :deep(.widget-container) {
    grid-column: 1 / -1 !important;
  }
}

@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
    gap: 10px;
  }
  .stats-desktop {
    display: none;
  }
  .stats-mobile {
    display: block;
  }
  .widgets-grid :deep(.widget-container) {
    grid-column: 1 / -1 !important;
  }
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: #6b7280;
  font-size: 15px;
}
</style>
