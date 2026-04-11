<script setup>
import { ref, computed, onMounted, onUnmounted, provide, nextTick } from 'vue'
import { LANDING_DASH_REVEAL_KEY } from '../../constants/landingDashboardReveal'
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  Coins,
  ArrowLeftRight,
  Settings,
  Bell
} from 'lucide-vue-next'
import { WidgetContainer } from '../widgets/base'
import {
  TotalCapitalWidget,
  PortfolioProfitWidget,
  DividendsWidget,
  ReturnWidget,
  ConsolidatedStatsWidget
} from '../widgets/stats'
import { PortfolioChartWidget, AssetAllocationWidget } from '../widgets/charts'
import {
  landingDashboardTotalCapital,
  landingDashboardProfit,
  landingDashboardDividends,
  landingDashboardReturn,
  landingDashboardPortfolioChart,
  landingDashboardAssetAllocation,
  landingDashboardUserPreview
} from '../../content/landingDashboardMock'

const props = defineProps({
  /**
   * false — сразу полные цифры и графики без счётчиков/дорисовки (удобно для отладки и a11y).
   * true — анимации после появления ~50% превью в viewport.
   */
  revealAnimations: {
    type: Boolean,
    default: true
  }
})

const root = ref(null)
/** Триггер анимаций: виджеты с scroll-reveal / scroll-reveal-chart читают через landingRevealRef + unref */
const dashboardReveal = ref(!props.revealAnimations)
provide(LANDING_DASH_REVEAL_KEY, dashboardReveal)

const capital = computed(() => landingDashboardTotalCapital)
const profit = computed(() => landingDashboardProfit)
const dividends = computed(() => landingDashboardDividends)
const returns = computed(() => landingDashboardReturn)
const chartData = computed(() => landingDashboardPortfolioChart)
const allocation = computed(() => landingDashboardAssetAllocation)
const userPreview = landingDashboardUserPreview

/** Срабатывание, когда видно ≥50% площади превью дашборда */
const LANDING_DASH_IO_THRESHOLDS = Array.from({ length: 41 }, (_, i) => i / 40)
const LANDING_DASH_REVEAL_RATIO = 1

let observer
let landingRevealTriggered = false

onMounted(() => {
  if (!props.revealAnimations) return

  observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (landingRevealTriggered || !e.isIntersecting) return
        if (e.intersectionRatio < LANDING_DASH_REVEAL_RATIO) return
        landingRevealTriggered = true
        observer?.unobserve(e.target)
        nextTick(() => {
          dashboardReveal.value = true
        })
      })
    },
    { threshold: LANDING_DASH_IO_THRESHOLDS, rootMargin: '0px' }
  )
  if (root.value) observer.observe(root.value)
})

onUnmounted(() => {
  observer?.disconnect()
})
</script>

<template>
  <div ref="root" class="landing-dash-mock" aria-hidden="true">
    <div class="landing-dash-mock__shell">
      <aside class="landing-dash-mock__sidebar">
        <div class="landing-dash-mock__brand">
          <div class="landing-dash-mock__logo-wrap">
            <img src="/site-logo.webp" alt="" class="landing-dash-mock__logo" width="28" height="28" />
          </div>
          <div class="landing-dash-mock__title">
            <span class="landing-dash-mock__title-main">Capital</span>
            <span class="landing-dash-mock__title-accent">View</span>
          </div>
        </div>

        <nav class="landing-dash-mock__nav" aria-label="">
          <div class="landing-dash-mock__nav-content">
            <div class="landing-dash-mock__section">
              <p class="landing-dash-mock__section-label">Меню</p>
              <ul class="landing-dash-mock__list">
                <li>
                  <span class="landing-dash-mock__item landing-dash-mock__item--active">
                    <span class="landing-dash-mock__ind" aria-hidden="true" />
                    <span class="landing-dash-mock__item-icon">
                      <LayoutDashboard :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Дашборд</span>
                  </span>
                </li>
                <li>
                  <span class="landing-dash-mock__item">
                    <span class="landing-dash-mock__item-icon">
                      <BarChart3 :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Аналитика</span>
                  </span>
                </li>
              </ul>
            </div>

            <div class="landing-dash-mock__section">
              <p class="landing-dash-mock__section-label">Финансы</p>
              <ul class="landing-dash-mock__list">
                <li>
                  <span class="landing-dash-mock__item">
                    <span class="landing-dash-mock__item-icon">
                      <Briefcase :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Активы</span>
                  </span>
                </li>
                <li>
                  <span class="landing-dash-mock__item">
                    <span class="landing-dash-mock__item-icon">
                      <Coins :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Дивиденды</span>
                  </span>
                </li>
                <li>
                  <span class="landing-dash-mock__item">
                    <span class="landing-dash-mock__item-icon">
                      <ArrowLeftRight :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Операции</span>
                  </span>
                </li>
              </ul>
            </div>

            <div class="landing-dash-mock__section">
              <p class="landing-dash-mock__section-label">Дополнительно</p>
              <ul class="landing-dash-mock__list">
                <li>
                  <span class="landing-dash-mock__item">
                    <span class="landing-dash-mock__item-icon">
                      <Settings :size="14" class="landing-dash-mock__ico" />
                    </span>
                    <span class="landing-dash-mock__item-text">Настройки</span>
                  </span>
                </li>
              </ul>
            </div>
          </div>
        </nav>
      </aside>

      <div class="landing-dash-mock__main">
        <header class="landing-dash-mock__header">
          <div class="landing-dash-mock__burger" aria-hidden="true" />
          <div class="landing-dash-mock__header-right">
            <span class="landing-dash-mock__bell" aria-hidden="true">
              <Bell :size="18" />
            </span>
            <div class="landing-dash-mock__user">
              <div class="landing-dash-mock__avatar" aria-hidden="true" />
              <div class="landing-dash-mock__user-text">
                <span class="landing-dash-mock__user-name">{{ userPreview.name }}</span>
                <span class="landing-dash-mock__user-email">{{ userPreview.email }}</span>
              </div>
            </div>
          </div>
        </header>

        <div class="landing-dash-mock__grid">
          <div class="landing-dash-mock__stats landing-dash-mock__stats-desktop">
            <WidgetContainer class="landing-dash-mock__wc" min-height="112px">
              <TotalCapitalWidget
                :total-amount="capital.totalAmount"
                :invested-amount="capital.investedAmount"
                :unrealized-pl="capital.unrealizedPl"
                :unrealized-percent="capital.unrealizedPercent"
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
              />
            </WidgetContainer>
            <WidgetContainer class="landing-dash-mock__wc" min-height="112px">
              <PortfolioProfitWidget
                :total-amount="profit.totalAmount"
                :total-profit="profit.totalProfit"
                :monthly-change="profit.monthlyChange"
                :invested-amount="profit.investedAmount"
                :analytics="profit.analytics"
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
              />
            </WidgetContainer>
            <WidgetContainer class="landing-dash-mock__wc" min-height="112px">
              <DividendsWidget
                :annual-dividends="dividends.annualDividends"
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
              />
            </WidgetContainer>
            <WidgetContainer class="landing-dash-mock__wc" min-height="112px">
              <ReturnWidget
                :return-percent="returns.returnPercent"
                :return-percent-on-invested="returns.returnPercentOnInvested"
                :total-value="returns.totalValue"
                :total-invested="returns.totalInvested"
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
              />
            </WidgetContainer>
          </div>
          <div class="landing-dash-mock__stats landing-dash-mock__stats-mobile">
            <WidgetContainer class="landing-dash-mock__wc" min-height="200px">
              <ConsolidatedStatsWidget
                :total-amount="capital.totalAmount"
                :invested-amount="capital.investedAmount"
                :total-profit="profit.totalProfit"
                :monthly-change="profit.monthlyChange"
                :analytics="profit.analytics"
                :annual-dividends="dividends.annualDividends"
                :return-percent="returns.returnPercent"
                :return-percent-on-invested="returns.returnPercentOnInvested"
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
              />
            </WidgetContainer>
          </div>

          <div class="landing-dash-mock__charts">
            <WidgetContainer class="landing-dash-mock__wc landing-dash-mock__chart-box">
              <PortfolioChartWidget
                :scroll-reveal-chart="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
                :chart-data="chartData"
              />
            </WidgetContainer>
            <WidgetContainer class="landing-dash-mock__wc landing-dash-mock__alloc-box" min-height="240px">
              <AssetAllocationWidget
                :scroll-reveal="revealAnimations"
                :landing-reveal-ref="dashboardReveal"
                :asset-allocation="allocation"
              />
            </WidgetContainer>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.landing-dash-mock {
  position: relative;
  width: 100%;
  /* Высота превью вычисляется от ширины (responsive) */
  aspect-ratio: 16 / 9;
  max-height: min(72vh, 640px);
  /* Радиус ближе к окнам macOS (~12px), чуть крупнее для масштаба превью */
  border-radius: clamp(12px, 1.35cqi, 16px);
  background: #eceff3;
  border: 1px solid rgba(15, 23, 42, 0.14);
  /* «Окно» macOS: внешняя тень + тонкий тёмный ободок + внутренний верхний блик */
  box-shadow:
    0 0 0 0.5px rgba(0, 0, 0, 0.06),
    0 28px 70px -16px rgba(15, 23, 42, 0.22),
    0 12px 28px -10px rgba(15, 23, 42, 0.14),
    0 4px 10px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.75),
    inset 0 0 0 1px rgba(255, 255, 255, 0.22);
  overflow: hidden;
  /* Масштаб типографики и метрик от ширины превью (не трогая сами виджеты) */
  container-type: inline-size;
  container-name: landing-dashboard-preview;
  --text-heading-3-size: clamp(0.6875rem, 2.35cqi, 0.8125rem);
  --text-heading-3-weight: 600;
  --text-value-size: clamp(0.8rem, 3.1cqi, 1.05rem);
  --text-body-secondary-size: clamp(0.65rem, 1.95cqi, 0.78rem);
  --text-caption-size: clamp(0.58rem, 1.75cqi, 0.72rem);
  --text-label-size: clamp(0.65rem, 1.9cqi, 0.78rem);
  /* Виджеты тянут эти токены напрямую — без них цифры/пилюли остаются крупными */
  --widget-font-main: clamp(0.78rem, 2.95cqi, 1rem);
  --widget-font-secondary: clamp(0.62rem, 1.9cqi, 0.76rem);
  --widget-font-small: clamp(0.52rem, 1.45cqi, 0.66rem);
  /* Совпадают с AppSidebar.vue :root (на лендинге без layout всё равно корректные цвета) */
  --sidebar-text-color: #d1d5db;
  --sidebar-primary-gradient: linear-gradient(135deg, #527de5, #6b91ea);
  /* Сайдбар превью: ещё компактнее (иконки/подписи/секции) */
  --landing-sb-width: clamp(118px, 14.5cqi, 164px);
  --landing-sb-brand-h: clamp(34px, 5.4cqi, 44px);
  --landing-sb-pad-x: clamp(0.3rem, 1.05cqi, 0.48rem);
  --landing-sb-logo: clamp(20px, 3.2cqi, 26px);
  --landing-sb-title: clamp(0.58rem, 1.55cqi, 0.72rem);
  --landing-sb-nav-y: clamp(0.3rem, 1.1cqi, 0.5rem);
  --landing-sb-seg-gap: clamp(0.48rem, 1.75cqi, 0.78rem);
  --landing-sb-section-gap: clamp(0.22rem, 0.85cqi, 0.4rem);
  --landing-sb-label: clamp(0.42rem, 1.05cqi, 0.52rem);
  --landing-sb-list-inset: clamp(0.18rem, 0.7cqi, 0.34rem);
  --landing-sb-item-h: clamp(22px, 3.45cqi, 28px);
  --landing-sb-item-pad-x: clamp(0.24rem, 0.9cqi, 0.4rem);
  --landing-sb-item-radius: clamp(0.35rem, 0.95cqi, 0.5rem);
  --landing-sb-item-fs: clamp(0.52rem, 1.3cqi, 0.625rem);
  --landing-sb-list-gap: clamp(0.1rem, 0.38cqi, 0.2rem);
  --landing-sb-icon-box: clamp(16px, 2.45cqi, 22px);
  --landing-sb-ind-h: clamp(0.6rem, 1.75cqi, 0.78rem);
}

.landing-dash-mock__shell {
  display: grid;
  grid-template-columns: minmax(102px, min(var(--landing-sb-width), 100%)) 1fr;
  height: 100%;
  min-height: 0;
}

.landing-dash-mock__stats-mobile {
  display: none;
}

/* Повторяет AppSidebar.vue (.sidebar) */
.landing-dash-mock__sidebar {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: rgba(17, 16, 29, 0.95);
  backdrop-filter: blur(clamp(14px, 2.2cqi, 22px));
  -webkit-backdrop-filter: blur(clamp(14px, 2.2cqi, 22px));
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 2px 0 28px -6px rgba(0, 0, 0, 0.38);
  color: var(--sidebar-text-color, #d1d5db);
}

/* .sidebar__header — компактная версия */
.landing-dash-mock__brand {
  display: flex;
  align-items: center;
  gap: 0;
  flex-shrink: 0;
  height: var(--landing-sb-brand-h);
  padding: 0 var(--landing-sb-pad-x);
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.landing-dash-mock__logo-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-width: calc(var(--landing-sb-logo) * 0.85);
  border-radius: 0;
  overflow: hidden;
}

.landing-dash-mock__logo {
  display: block;
  width: var(--landing-sb-logo);
  height: var(--landing-sb-logo);
  object-fit: cover;
  object-position: center;
}

/* .sidebar__title + .title-part */
.landing-dash-mock__title {
  display: flex;
  align-items: center;
  gap: 0;
  margin: 0 0 0 clamp(0.2rem, 0.6cqi, 0.35rem);
  font-size: var(--landing-sb-title);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.1;
  white-space: nowrap;
}

.landing-dash-mock__title-main {
  color: #fff;
}

.landing-dash-mock__title-accent {
  background: var(--sidebar-primary-gradient, linear-gradient(135deg, #527de5, #6b91ea));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.landing-dash-mock__nav {
  flex: 1;
  min-height: 0;
  padding: var(--landing-sb-nav-y) 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.landing-dash-mock__nav-content {
  display: flex;
  flex-direction: column;
  gap: var(--landing-sb-seg-gap);
}

.landing-dash-mock__section {
  display: flex;
  flex-direction: column;
  gap: var(--landing-sb-section-gap);
}

/* .sidebar__section-title */
.landing-dash-mock__section-label {
  margin: 0;
  padding: 0 var(--landing-sb-pad-x);
  font-size: var(--landing-sb-label);
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: rgba(255, 255, 255, 0.4);
}

.landing-dash-mock__list {
  list-style: none;
  margin: 0;
  padding: 0 var(--landing-sb-list-inset);
  display: flex;
  flex-direction: column;
  gap: var(--landing-sb-list-gap);
}

.landing-dash-mock__list > li {
  position: relative;
}

/* .sidebar__nav-item */
.landing-dash-mock__item {
  position: relative;
  display: flex;
  align-items: center;
  height: var(--landing-sb-item-h);
  padding: 0 var(--landing-sb-item-pad-x);
  border-radius: var(--landing-sb-item-radius);
  font-size: var(--landing-sb-item-fs);
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
  transition: background-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), color 0.3s cubic-bezier(0.4, 0, 0.2, 1),
    transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.landing-dash-mock__item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  transform: translateX(1px);
}

.landing-dash-mock__item--active {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-weight: 600;
  box-shadow: 0 1px 5px rgba(0, 0, 0, 0.12);
}

.landing-dash-mock__item--active:hover {
  transform: translateX(1px);
}

/* .sidebar-active-indicator */
.landing-dash-mock__ind {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: var(--landing-sb-ind-h);
  border-radius: 0 3px 3px 0;
  background: var(--sidebar-primary-gradient, linear-gradient(135deg, #527de5, #6b91ea));
  box-shadow: 0 0 8px 1px hsla(245, 58%, 58%, 0.35);
}

.landing-dash-mock__item:not(.landing-dash-mock__item--active) .landing-dash-mock__ind {
  display: none;
}

.landing-dash-mock__item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: var(--landing-sb-icon-box);
  flex-shrink: 0;
  color: inherit;
}

.landing-dash-mock__item-icon :deep(svg) {
  width: clamp(12px, 1.85cqi, 14px);
  height: clamp(12px, 1.85cqi, 14px);
}

.landing-dash-mock__item--active .landing-dash-mock__item-icon {
  color: #fff;
}

.landing-dash-mock__item:not(.landing-dash-mock__item--active) .landing-dash-mock__item-icon {
  color: rgba(255, 255, 255, 0.7);
}

.landing-dash-mock__item-text {
  margin-left: clamp(2px, 0.45cqi, 4px);
  white-space: nowrap;
}

.landing-dash-mock__ico {
  flex-shrink: 0;
  color: inherit;
}

.landing-dash-mock__main {
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #f8fafc;
}

.landing-dash-mock__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
}

.landing-dash-mock__burger {
  width: 30px;
  height: 22px;
  border-radius: 6px;
  background: linear-gradient(#0f172a, #0f172a) 4px 5px / 18px 2px no-repeat,
    linear-gradient(#0f172a, #0f172a) 4px 10px / 14px 2px no-repeat,
    linear-gradient(#0f172a, #0f172a) 4px 15px / 18px 2px no-repeat;
  opacity: 0.35;
}

.landing-dash-mock__header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.landing-dash-mock__bell {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  color: #64748b;
  background: #f1f5f9;
}

.landing-dash-mock__user {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.landing-dash-mock__avatar {
  width: 32px;
  height: 32px;
  border-radius: 9px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
}

.landing-dash-mock__user-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.landing-dash-mock__user-name {
  font-size: 0.75rem;
  font-weight: 600;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.landing-dash-mock__user-email {
  font-size: 0.625rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 200px;
}

.landing-dash-mock__grid {
  flex: 1;
  min-height: 0;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: auto;
}

.landing-dash-mock__stats-desktop {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

@media (min-width: 900px) {
  .landing-dash-mock__stats-desktop {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

.landing-dash-mock__charts {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
  /* Занимаем высоту под превью — в паре с соседним виджетом строка грида выравнивается по максимуму */
  flex: 1;
  min-height: 0;
  align-items: stretch;
}

@media (min-width: 900px) {
  .landing-dash-mock__charts {
    grid-template-columns: minmax(0, 1.65fr) minmax(0, 1fr);
  }
}

/* Как Dashboard.vue: сайдбар скрыт, статы — ConsolidatedStatsWidget */
@media (max-width: 768px) {
  .landing-dash-mock__shell {
    grid-template-columns: 1fr;
    max-height: none;
  }

  .landing-dash-mock__sidebar {
    display: none;
  }

  .landing-dash-mock__stats-desktop {
    display: none;
  }

  .landing-dash-mock__stats-mobile {
    display: block;
  }

  .landing-dash-mock__charts {
    grid-template-columns: 1fr;
  }

  .landing-dash-mock__alloc-box {
    display: none;
  }
}

.landing-dash-mock__wc {
  min-width: 0;
}

.landing-dash-mock__chart-box,
.landing-dash-mock__alloc-box {
  display: flex;
  flex-direction: column;
  min-height: 0;
  align-self: stretch;
}

.landing-dash-mock__alloc-box :deep(.widget-container) {
  flex: 1;
  min-height: 0;
}

.landing-dash-mock__chart-box :deep(.widget-container) {
  flex: 1;
  min-height: 0;
  height: 100%;
}

.landing-dash-mock__chart-box :deep(.widget) {
  height: 100%;
  min-height: 0;
}

.landing-dash-mock__chart-box :deep(.widget-content) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.landing-dash-mock :deep(.widget) {
  height: 100%;
  padding: 0.55rem 0.65rem;
  border-radius: 12px;
}

.landing-dash-mock :deep(.widget-header) {
  gap: 0.35rem;
}

.landing-dash-mock :deep(.widget-title h2) {
  letter-spacing: 0.02em;
}

.landing-dash-mock :deep(.widget-title-icon),
.landing-dash-mock :deep(.widget-title-icon-placeholder) {
  width: 24px;
  height: 24px;
  border-radius: 6px;
}

.landing-dash-mock :deep(.widget-content) {
  margin-top: 0.4rem;
}

/* Значение + пилюля; при нехватке ширины пилюля переносится на следующую строку */
.landing-dash-mock :deep(.stat-card-content .main-value-row) {
  flex-direction: row;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.25rem 0.35rem;
  margin: 4px 0 6px;
}

.landing-dash-mock :deep(.stat-card-content .main-value-wrapper) {
  flex: 1 1 auto;
  min-width: 0;
}

.landing-dash-mock :deep(.value-change-pill) {
  padding: 0 4px;
  font-size: clamp(0.48rem, 1.35cqi, 0.62rem);
  flex-shrink: 0;
}

.landing-dash-mock :deep(.value-change-pill .sign-prefix) {
  font-size: 0.85em;
}

.landing-dash-mock :deep(.main-value-row .tooltip-wrapper) {
  max-width: 100%;
}

.landing-dash-mock :deep(.capital-info) {
  margin-bottom: 0.35rem;
}

.landing-dash-mock :deep(.capital-info .capital-values) {
  font-size: clamp(0.75rem, 2.2cqi, 0.875rem);
}

.landing-dash-mock :deep(.capital-growth) {
  gap: 0.35rem;
}

.landing-dash-mock :deep(.capital-growth-label) {
  font-size: clamp(0.55rem, 1.65cqi, 0.7rem);
}

.landing-dash-mock :deep(.header-controls) {
  gap: 0.35rem 0.5rem;
  flex-wrap: wrap;
}

.landing-dash-mock :deep(.period-filters) {
  padding: 0.12rem;
  gap: 0.12rem;
}

.landing-dash-mock :deep(.filter-btn) {
  padding: 0.26rem 0.42rem;
  font-size: clamp(0.52rem, 1.55cqi, 0.68rem);
}

.landing-dash-mock :deep(.toggle-switch) {
  gap: 5px;
}

.landing-dash-mock :deep(.toggle-switch-track) {
  width: 34px;
  height: 19px;
  border-radius: 9px;
}

.landing-dash-mock :deep(.toggle-switch-thumb) {
  width: 15px;
  height: 15px;
  top: 2px;
  left: 2px;
}

.landing-dash-mock :deep(.toggle-switch--checked .toggle-switch-thumb) {
  transform: translateX(15px);
}

.landing-dash-mock :deep(.toggle-switch-label) {
  font-size: clamp(0.58rem, 1.65cqi, 0.72rem);
}

/* Динамика капитала: график заполняет место под шапкой/строками сумм (как в полноэкранном дашборде) */
.landing-dash-mock__chart-box :deep(.capital-info) {
  flex-shrink: 0;
}

.landing-dash-mock__chart-box :deep(.chart-wrapper) {
  flex: 1 1 auto !important;
  min-height: clamp(100px, 12cqi, 140px) !important;
  height: auto !important;
  max-height: none !important;
}

.landing-dash-mock :deep(.allocation-container) {
  gap: 0.35rem;
}

/* В виджете фикс 280×280 и брейкпоинты по viewport — в превью режем по cqi */
.landing-dash-mock :deep(.allocation-container .chart-wrapper) {
  width: min(100%, clamp(108px, 32cqi, 188px));
  height: min(100%, clamp(108px, 32cqi, 188px));
  min-height: 0;
  flex-shrink: 0;
}

.landing-dash-mock :deep(.allocation-container .chart-center .center-label) {
  font-size: clamp(0.52rem, 1.5cqi, 0.65rem);
}

.landing-dash-mock :deep(.allocation-container .chart-center .center-percentage) {
  font-size: clamp(0.68rem, 2.2cqi, 0.88rem);
}

.landing-dash-mock :deep(.allocation-container .chart-center .center-value) {
  font-size: clamp(0.55rem, 1.65cqi, 0.7rem);
}

.landing-dash-mock :deep(.allocation-container .legends) {
  margin-top: 6px;
  gap: 6px 10px;
  font-size: clamp(0.52rem, 1.5cqi, 0.65rem);
}

.landing-dash-mock :deep(.allocation-container .legend-color) {
  width: 8px;
  height: 8px;
  margin-right: 5px;
}

/* Узкое превью при широком viewport — тот же макет, что на телефоне */
@container landing-dashboard-preview (max-width: 768px) {
  .landing-dash-mock__shell {
    grid-template-columns: 1fr;
    max-height: none;
  }

  .landing-dash-mock__sidebar {
    display: none;
  }

  .landing-dash-mock__stats-desktop {
    display: none;
  }

  .landing-dash-mock__stats-mobile {
    display: block;
  }

  .landing-dash-mock__charts {
    grid-template-columns: 1fr;
  }

  .landing-dash-mock__alloc-box {
    display: none;
  }
}

@container landing-dashboard-preview (max-width: 520px) {
  .landing-dash-mock :deep(.filter-btn) {
    padding: 0.22rem 0.36rem;
    font-size: clamp(0.5rem, 1.45cqi, 0.62rem);
  }
}

@media (max-width: 899px) {
  .landing-dash-mock__user-name,
  .landing-dash-mock__user-email {
    max-width: 140px;
  }
}
</style>
