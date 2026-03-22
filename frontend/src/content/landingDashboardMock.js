/**
 * Статичные данные для превью дашборда на лендинге (без API / сторов).
 * Цифры согласованы со скрином реального дашборда CapitalView.
 */

const TOTAL_AMOUNT = 1_220_272
const INVESTED_AMOUNT = 1_239_325
const TOTAL_PROFIT = 64_114.25
/** Для бейджа «изменение прибыли за месяц» ~+55% к прибыли месяц назад */
const MONTHLY_PROFIT_CHANGE = 22_850

/** Метки — первое число месяца (как в PortfolioChartWidget / getPeriodValues) */
const CHART_LABELS = [
  '2023-04-01',
  '2023-05-01',
  '2023-06-01',
  '2023-07-01',
  '2023-08-01',
  '2023-09-01',
  '2023-10-01',
  '2023-11-01',
  '2023-12-01',
  '2024-01-01',
  '2024-02-01',
  '2024-03-01',
  '2024-04-01',
  '2024-05-01',
  '2024-06-01',
  '2024-07-01',
  '2024-08-01',
  '2024-09-01'
]

/** Плавный рост капитала к финальному значению; «инвестиции» — зелёная ступенчатая линия */
const CHART_VALUE = [
  0, 185_000, 312_000, 428_000, 501_000, 589_000, 642_000, 698_000, 755_000, 812_000, 884_000,
  931_000, 978_000, 1_045_000, 1_102_000, 1_148_000, 1_189_000, TOTAL_AMOUNT
]

const CHART_INVESTED = [
  720_000, 750_000, 780_000, 800_000, 820_000, 850_000, 880_000, 900_000, 920_000, 950_000,
  980_000, 1_010_000, 1_040_000, 1_080_000, 1_120_000, 1_160_000, 1_200_000, INVESTED_AMOUNT
]

const CHART_BALANCE = CHART_LABELS.map(() => 0)

export const landingDashboardTotalCapital = {
  totalAmount: TOTAL_AMOUNT,
  investedAmount: INVESTED_AMOUNT
}

export const landingDashboardProfit = {
  totalAmount: TOTAL_AMOUNT,
  totalProfit: TOTAL_PROFIT,
  monthlyChange: MONTHLY_PROFIT_CHANGE,
  investedAmount: INVESTED_AMOUNT,
  analytics: {
    totals: {
      realized_pl: 12_000,
      unrealized_pl: 38_000,
      dividends: 12_000,
      coupons: 2_114.25,
      commissions: 0,
      taxes: 0
    }
  }
}

export const landingDashboardDividends = {
  annualDividends: 193_117
}

export const landingDashboardReturn = {
  returnPercent: 15.83,
  returnPercentOnInvested: 16.16,
  totalValue: TOTAL_AMOUNT,
  totalInvested: INVESTED_AMOUNT
}

export const landingDashboardPortfolioChart = {
  labels: CHART_LABELS,
  data_value: CHART_VALUE,
  data_invested: CHART_INVESTED,
  data_balance: CHART_BALANCE
}

/** Донат: акции ~74%, остальное — облигации и фонд */
const ALLOCATION_STOCKS = 908_340
const ALLOCATION_BONDS = 200_000
const ALLOCATION_FUNDS = 119_135

export const landingDashboardAssetAllocation = {
  labels: ['Акция', 'Облигация', 'Фонд'],
  datasets: [
    {
      data: [ALLOCATION_STOCKS, ALLOCATION_BONDS, ALLOCATION_FUNDS],
      backgroundColor: ['#3b82f6', '#f97316', '#ef4444']
    }
  ]
}

export const landingDashboardUserPreview = {
  name: 'Профессиональный инвестор',
  email: 'root@gmail.com'
}
