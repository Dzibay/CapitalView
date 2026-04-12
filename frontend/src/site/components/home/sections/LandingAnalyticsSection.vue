<script setup>
import { ref, computed, provide } from 'vue'
import { LANDING_DASH_REVEAL_KEY } from '../../../../constants/landingDashboardReveal'
import { WidgetContainer } from '../../../../components/widgets/base'
import { TotalCapitalWidget, DividendsWidget, ReturnWidget } from '../../../../components/widgets/stats'
import { PortfolioChartWidget, AssetAllocationWidget, PayoutsChartWidget } from '../../../../components/widgets/charts'
import {
  landingDashboardTotalCapital,
  landingDashboardDividends,
  landingDashboardReturn,
  landingDashboardPortfolioChart,
  landingDashboardAssetAllocation,
  landingDashboardPayouts
} from '../../../content/home/landingDashboardMock'

const dashboardReveal = ref(true)
provide(LANDING_DASH_REVEAL_KEY, dashboardReveal)

const capital = computed(() => landingDashboardTotalCapital)
const dividends = computed(() => landingDashboardDividends)
const returns = computed(() => landingDashboardReturn)
const chartData = computed(() => landingDashboardPortfolioChart)
const allocation = computed(() => landingDashboardAssetAllocation)
const payouts = computed(() => landingDashboardPayouts)

const blocks = [
  {
    num: '01',
    heading: 'Учёт акций и облигаций\nв одном окне',
    desc: 'Акции, облигации, ETF, валюта и любые другие инструменты — CapitalView объединяет все виды инвестиций в единой панели. Агрегатор брокерских счетов с актуальными ценами.',
    features: ['Автоимпорт из Т-Инвестиции', 'Ручное добавление любых активов', 'Несколько портфелей одновременно'],
    widget: 'stats'
  },
  {
    num: '02',
    heading: 'Доходность\nпортфеля',
    desc: 'Отслеживайте, как меняется стоимость портфеля день за днём. Реальная доходность с учётом комиссий, налогов и реинвестиций — без иллюзий.',
    features: ['Графики за любой период', 'Учёт комиссий и налогов', 'Сравнение с бенчмарками'],
    widget: 'chart'
  },
  {
    num: '03',
    heading: 'Дивидендный\nкалендарь',
    desc: 'Отслеживание дивидендов и купонов: полная история начисленных выплат и прогноз будущих. Дивиденды, купоны и амортизации — по каждому активу, с точными датами.',
    features: ['Дивидендный календарь', 'Прогноз будущих выплат', 'Детализация по каждому активу'],
    widget: 'payouts'
  },
  {
    num: '04',
    heading: 'Структура\nи баланс портфеля',
    desc: 'Управление портфелем: видите, как распределены ваши вложения по классам активов, секторам и валютам. Находите перекосы и поддерживайте оптимальный баланс.',
    features: ['По классам, секторам, валютам', 'Рекомендации по балансировке', 'Сравнение с целевой структурой'],
    widget: 'allocation'
  }
]
</script>

<template>
  <section id="features" class="section snap-section analytics-section">
    <div class="container analytics-container">
      <div class="analytics-header">
        <div class="analytics-label reveal">Возможности</div>
        <h2 class="analytics-title reveal">Аналитика<br>инвестиционного портфеля</h2>
        <p class="analytics-desc reveal">Полная картина портфеля — учёт акций, облигаций и криптовалюты. Отслеживание доходности, дивидендов и купонов в одной платформе вместо десятка таблиц.</p>
      </div>

      <div
        v-for="(block, idx) in blocks"
        :key="idx"
        class="analytics-block reveal"
        :class="{ reverse: idx % 2 !== 0 }"
      >
        <div class="block-text">
          <div class="block-num">{{ block.num }}</div>
          <h3 class="block-heading" v-html="block.heading.replace('\n', '<br>')" />
          <p class="block-desc">{{ block.desc }}</p>
          <div class="block-features">
            <div v-for="f in block.features" :key="f" class="block-feature">
              <span class="block-feature-dot" />
              {{ f }}
            </div>
          </div>
        </div>

        <div class="block-widget">
          <!-- Распределение активов (донат) -->
          <WidgetContainer v-if="block.widget === 'allocation'" min-height="320px">
            <AssetAllocationWidget :asset-allocation="allocation" />
          </WidgetContainer>

          <!-- Динамика капитала (линейный график) -->
          <WidgetContainer v-else-if="block.widget === 'chart'" min-height="320px">
            <PortfolioChartWidget :chart-data="chartData" />
          </WidgetContainer>

          <!-- Выплаты по месяцам (столбчатый график) -->
          <WidgetContainer v-else-if="block.widget === 'payouts'" min-height="320px">
            <PayoutsChartWidget :payouts="payouts" mode="past" title="Выплаты по месяцам" />
          </WidgetContainer>

          <!-- Статистические карточки -->
          <div v-else-if="block.widget === 'stats'" class="stats-stack">
            <WidgetContainer min-height="112px">
              <TotalCapitalWidget
                :total-amount="capital.totalAmount"
                :invested-amount="capital.investedAmount"
                :unrealized-pl="capital.unrealizedPl"
                :unrealized-percent="capital.unrealizedPercent"
              />
            </WidgetContainer>
            <WidgetContainer min-height="112px">
              <DividendsWidget :annual-dividends="dividends.annualDividends" />
            </WidgetContainer>
            <WidgetContainer min-height="112px">
              <ReturnWidget
                :return-percent="returns.returnPercent"
                :return-percent-on-invested="returns.returnPercentOnInvested"
                :total-value="returns.totalValue"
                :total-invested="returns.totalInvested"
              />
            </WidgetContainer>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
section#features.analytics-section {
  position: relative;
  overflow: hidden;
  padding: clamp(72px, 10vh, 100px) 0;
  background: transparent;
}

/* ── Container ── */
.analytics-container {
  position: relative;
  z-index: 1;
}

/* ── Header ── */
.analytics-header {
  padding-bottom: 48px;
  max-width: 600px;
}

.analytics-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.analytics-title {
  font-family: var(--font-display);
  font-size: clamp(36px, 4.5vw, 48px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.03em;
  color: #0f172a;
  margin-bottom: 16px;
}

.analytics-desc {
  font-family: var(--font-body);
  font-size: 17px;
  line-height: 1.65;
  color: #64748b;
}

/* ── Zigzag block ── */
.analytics-block {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(32px, 5vw, 72px);
  align-items: center;
  padding: clamp(48px, 6vh, 80px) 0;
  border-top: 1px solid rgba(15, 23, 42, 0.04);
}
.analytics-block:first-of-type {
  border-top: none;
}

.analytics-block.reverse .block-text {
  order: 2;
}
.analytics-block.reverse .block-widget {
  order: 1;
}

/* ── Text side ── */
.block-num {
  font-family: var(--font-display);
  font-weight: 100;
  font-size: 80px;
  line-height: 1;
  color: rgba(59, 130, 246, 0.08);
  letter-spacing: -0.06em;
  margin-bottom: -8px;
}

.block-heading {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: clamp(28px, 3.5vw, 40px);
  line-height: 1.12;
  letter-spacing: -0.03em;
  color: #0f172a;
  margin-bottom: 16px;
}

.block-desc {
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  color: #64748b;
  max-width: 460px;
}

.block-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 24px;
}

.block-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  color: #475569;
}

.block-feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  flex-shrink: 0;
}

/* ── Widget side ── */
.block-widget {
  min-width: 0;
}

.block-widget :deep(.widget) {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 40px rgba(15, 23, 42, 0.06);
  padding: 1.25rem 1.5rem;
}

/* ── Stats stack ── */
.stats-stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .analytics-block {
    grid-template-columns: 1fr;
    gap: 32px;
  }
  .analytics-block.reverse .block-text {
    order: 1;
  }
  .analytics-block.reverse .block-widget {
    order: 2;
  }
  .block-num {
    font-size: 56px;
  }
}

@media (max-width: 600px) {
  .block-heading {
    font-size: 28px;
  }
}
</style>
