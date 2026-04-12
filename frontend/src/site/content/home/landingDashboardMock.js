/**
 * СТАТИЧНЫЕ ДАННЫЕ ДЛЯ DASHBOARD (ПОЛТОРА ГОДА)
 * Синхронизация: Capital (498.5k) − (позиции + остаток) ≈ unrealized (58.64k);
 * общий P&L (60.5k) = разложение по realized/unrealized/dividends/…
 * Yield: 13.81%
 * Div Yield: ~9.2% (45,862 руб/год)
 */
const profitData = {
  realized_pl: -12348,
  unrealized_pl: 58640,
  dividends: 57980,
  coupons: 14800,
  commissions: -1200,
  taxes: -8800
}
const TOTAL_AMOUNT = 498500;
const INVESTED_AMOUNT = 439860;
/** Остаток на счёте в моке (0 — как в сценарии «всё в позициях») */
const PORTFOLIO_BALANCE = 0;
const INVESTED_WITH_BALANCE = INVESTED_AMOUNT + PORTFOLIO_BALANCE;
const TOTAL_PROFIT = Object.values(profitData).reduce((acc, value) => acc + value, 0);
const MONTHLY_PROFIT_CHANGE = 8400; // Условный плюс за последний месяц
const RETURN_PERCENT = 15.18;
const RETURN_PERCENT_ON_INVESTED = 17.81;

export const landingDashboardTotalCapital = {
  totalAmount: TOTAL_AMOUNT,
  investedAmount: INVESTED_WITH_BALANCE,
  unrealizedPl: profitData.unrealized_pl,
  unrealizedPercent:
    INVESTED_WITH_BALANCE > 0
      ? (profitData.unrealized_pl / INVESTED_WITH_BALANCE) * 100
      : 0,
}

export const landingDashboardProfit = {
  totalAmount: TOTAL_AMOUNT,
  totalProfit: TOTAL_PROFIT,
  monthlyChange: MONTHLY_PROFIT_CHANGE,
  investedAmount: INVESTED_WITH_BALANCE,
  analytics: {
    totals: {
      // Сумма этих полей должна давать TOTAL_PROFIT (60500)
      realized_pl: -12348,
      unrealized_pl: 58640,
      dividends: 57980,
      coupons: 14800,
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
  totalInvested: INVESTED_WITH_BALANCE,
}

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
    "2026-02-22", "2026-03-01", "2026-03-08", "2026-03-15", "2026-03-22", "2026-03-29", "2026-04-01"
  ],

  // Инвестиции: ежемесячные пополнения + периодические дивиденды + ежедневные купоны (мелкие приращения между шагами)
  data_invested: [
    0, 50000, 50340, 50530, 80530, 80720, 80940, 81130, 106130, 106380, 106640, 109140, 109410,
    134410, 134680, 134920, 135180, 160180, 160420, 160680, 160950, 161240, 194740, 195020, 195310,
    195620, 220620, 220890, 221180, 221480, 221790, 241790, 242080, 242380, 242680, 271680, 272030,
    272390, 272740, 273100, 298100, 298440, 298790, 299140, 319140, 319500, 319860, 320210, 320570,
    350570, 350940, 351320, 351710, 376710, 377100, 377490, 377890, 397890, 398280, 398680, 399090,
    420090, 420540, 421000, 421470, 426470, 426920, 427380, 427850, 430850, 431310, 431780, 432260,
    435260, 435740, 436230, 438000, 438000, 438560
  ],

  // Капитал: волатильный, вначале ниже инвестиций, два заметных провала (апрель, октябрь), в итоге растёт до 498.5k
  data_value: [
    0, 50000, 49100, 49500, 79800, 78900, 79400, 80200, 105200, 106100, 107800, 110500, 109800,
    133800, 135200, 137500, 138200, 159600, 161800, 164200, 166500, 168100, 198200, 200500, 199100,
    197800, 218400, 215200, 213800, 216500, 219200, 238500, 241200, 244800, 247500, 275200, 278400,
    281600, 284200, 286800, 310200, 312500, 311800, 313400, 332100, 329800, 327500, 330200, 332800,
    358200, 362400, 365800, 363500, 382200, 378400, 374800, 372100, 394200, 398800, 405200, 410600,
    426800, 432400, 438200, 441500, 448200, 452100, 455800, 460200, 465400, 468200, 472500, 478800,
    482100, 486400, 492300, 498500, 498500, 497200
  ],

  // Баланс: остаток денег на счёте, колеблется от 0 до ~10 000
  data_balance: [
    0, 2800, 4100, 3500, 5100, 7200, 6800, 4300, 2100, 3400, 5600, 1200, 2800,
    4500, 3100, 1800, 5200, 7800, 6200, 3400, 2100, 4600, 3200, 1500, 5800,
    8200, 9100, 7400, 4200, 2800, 1500, 3800, 5400, 7200, 4100, 2200, 800,
    3500, 6100, 5400, 7800, 4500, 2100, 3600, 5200, 8400, 9100, 6300, 2800,
    1200, 4500, 3100, 7600, 8900, 6200, 3400, 1800, 4200, 5800, 2100, 600,
    3500, 7200, 9400, 5800, 2100, 4800, 6500, 3200, 7400, 5100, 2800, 1200,
    4600, 8200, 5300, 3800, 2000, 1300
  ]
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