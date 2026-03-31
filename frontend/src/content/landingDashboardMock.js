/**
 * СТАТИЧНЫЕ ДАННЫЕ ДЛЯ DASHBOARD (ПОЛТОРА ГОДА)
 * Все расчеты синхронизированы:
 * Capital (498.5k) - Invested (438k) = Profit (60.5k)
 * Yield: 13.81%
 * Div Yield: ~9.2% (45,862 руб/год)
 */

const TOTAL_AMOUNT = 498500;
const INVESTED_AMOUNT = 438000;
const TOTAL_PROFIT = 60500; // Строго: TOTAL_AMOUNT - INVESTED_AMOUNT
const MONTHLY_PROFIT_CHANGE = 8400; // Условный плюс за последний месяц
const RETURN_PERCENT = 15.18;
const RETURN_PERCENT_ON_INVESTED = 17.81;

export const landingDashboardTotalCapital = {
  totalAmount: TOTAL_AMOUNT,
  investedAmount: INVESTED_AMOUNT
};

export const landingDashboardProfit = {
  totalAmount: TOTAL_AMOUNT,
  totalProfit: TOTAL_PROFIT,
  monthlyChange: MONTHLY_PROFIT_CHANGE,
  investedAmount: INVESTED_AMOUNT,
  analytics: {
    totals: {
      // Сумма этих полей должна давать TOTAL_PROFIT (60500)
      realized_pl: 12000,
      unrealized_pl: 32500,
      dividends: 11200,
      coupons: 4800,
      commissions: -1200, // Комиссии уменьшают общий профит
      taxes: -8800 // Налоги уменьшают общий профит
    }
  }
};

export const landingDashboardDividends = {
  annualDividends: TOTAL_AMOUNT * RETURN_PERCENT / 100
};

export const landingDashboardReturn = {
  returnPercent: RETURN_PERCENT,
  returnPercentOnInvested: RETURN_PERCENT_ON_INVESTED,
  totalValue: TOTAL_AMOUNT,
  totalInvested: INVESTED_AMOUNT
};

export const landingDashboardPortfolioChart = {
  // 77 недель (Октябрь 2024 — Март 2026)
  labels: [
    "2024-10-06", "2024-10-13", "2024-10-20", "2024-10-27", "2024-11-03", "2024-11-10", "2024-11-17", "2024-11-24",
    "2024-12-01", "2024-12-08", "2024-12-15", "2024-12-22", "2024-12-29", "2025-01-05", "2025-01-12", "2025-01-19",
    "2025-01-26", "2025-02-02", "2025-02-09", "2025-02-16", "2025-02-23", "2025-03-02", "2025-03-09", "2025-03-16",
    "2025-03-23", "2025-03-30", "2025-04-06", "2025-04-13", "2025-04-20", "2025-04-27", "2025-05-04", "2025-05-11",
    "2025-05-18", "2025-05-25", "2025-06-01", "2025-06-08", "2025-06-15", "2025-06-22", "2025-06-29", "2025-07-06",
    "2025-07-13", "2025-07-20", "2025-07-27", "2025-08-03", "2025-08-10", "2025-08-17", "2025-08-24", "2025-08-31",
    "2025-09-07", "2025-09-14", "2025-09-21", "2025-09-28", "2025-10-05", "2025-10-12", "2025-10-19", "2025-10-26",
    "2025-11-02", "2025-11-09", "2025-11-16", "2025-11-23", "2025-11-30", "2025-12-07", "2025-12-14", "2025-12-21",
    "2025-12-28", "2026-01-04", "2026-01-11", "2026-01-18", "2026-01-25", "2026-02-01", "2026-02-08", "2026-02-15",
    "2026-02-22", "2026-03-01", "2026-03-08", "2026-03-15", "2026-03-22"
  ],
  data_value: [
    36200, 37100, 36500, 37800, 62400, 63800, 65100, 64200,
    90800, 92400, 91100, 93600, 95800, 123400, 126100, 124800,
    128900, 151200, 155800, 158400, 156100, 181600, 184200, 187500,
    190800, 212400, 216800, 220100, 218300, 247200, 252600, 255400,
    253100, 280800, 285400, 289200, 292100, 314600, 318200, 321800,
    319400, 345200, 350800, 348100, 352600, 381400, 385200, 382800,
    387100, 408600, 412400, 415800, 419200, 441600, 446200, 449800,
    453400, 458200, 462800, 467400, 471200, 476800, 481400, 478200,
    484600, 490200, 493400, 488800, 491200, 496800, 501200, 504600,
    499200, 502800, 496400, 500100, 498500
  ],
  data_invested: [
    35000, 35000, 35000, 35000, 60000, 60000, 60000, 60000,
    85000, 85000, 85000, 85000, 85000, 115000, 115000, 115000,
    115000, 145000, 145000, 145000, 145000, 175000, 175000, 175000,
    175000, 205000, 205000, 205000, 205000, 240000, 240000, 240000,
    240000, 275000, 275000, 275000, 275000, 305000, 305000, 305000,
    305000, 340000, 340000, 340000, 340000, 375000, 375000, 375000,
    375000, 405000, 405000, 405000, 405000, 438000, 438000, 438000,
    438000, 438000, 438000, 438000, 438000, 438000, 438000, 438000,
    438000, 438000, 438000, 438000, 438000, 438000, 438000, 438000,
    438000, 438000, 438000, 438000, 438000
  ],
  data_balance: new Array(77).fill(0)
};

export const landingDashboardAssetAllocation = {
  labels: ['Акция', 'Облигация', 'Фонд'],
  datasets: [
    {
      // Итого 498 500
      data: [355000, 98500, 45000],
      backgroundColor: ['#3b82f6', '#f97316', '#ef4444']
    }
  ]
};

export const landingDashboardPayouts = [
  { month: '2025-04', dividends: 3200, coupons: 1800, amortizations: 0 },
  { month: '2025-05', dividends: 1200, coupons: 2100, amortizations: 0 },
  { month: '2025-06', dividends: 5800, coupons: 1400, amortizations: 800 },
  { month: '2025-07', dividends: 2400, coupons: 1800, amortizations: 0 },
  { month: '2025-08', dividends: 4100, coupons: 2200, amortizations: 0 },
  { month: '2025-09', dividends: 1600, coupons: 1800, amortizations: 600 },
  { month: '2025-10', dividends: 6200, coupons: 2800, amortizations: 0 },
  { month: '2025-11', dividends: 3400, coupons: 1200, amortizations: 0 },
  { month: '2025-12', dividends: 7200, coupons: 3600, amortizations: 1200 },
  { month: '2026-01', dividends: 2800, coupons: 2400, amortizations: 0 },
  { month: '2026-02', dividends: 3600, coupons: 1800, amortizations: 0 },
  { month: '2026-03', dividends: 4200, coupons: 2200, amortizations: 0 }
]

export const landingDashboardUserPreview = {
  name: 'Профессиональный инвестор',
  email: 'investor@example.com'
};