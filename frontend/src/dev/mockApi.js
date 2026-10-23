/**
 * Демо-API для локальной разработки без backend.
 * Подключается только в dev при VITE_MOCK_API=1 (см. main.js, `npm run dev:demo`).
 * Ответы повторяют форму success_response бэкенда: { success, ...data }.
 */
import apiClient from '../utils/apiClient'

const DAY = 86400000

function mulberry32(seed) {
  let a = seed >>> 0
  return () => {
    a = (a + 0x6d2b79f5) >>> 0
    let t = a
    t = Math.imul(t ^ (t >>> 15), t | 1)
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61)
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}

const iso = (d) => d.toISOString().slice(0, 10)
const monthKey = (d) => d.toISOString().slice(0, 7)
const round2 = (v) => Math.round(v * 100) / 100

const USD = 92.4

// ─── позиции ────────────────────────────────────────────────────────────────
const POSITIONS = {
  2: [
    ['SBER', 'Сбербанк', 'Акции', 1200, 248.3, 312.4, 2.14, 0, 'RUB', 1],
    ['LKOH', 'Лукойл', 'Акции', 30, 6410, 7124, -46.5, 0, 'RUB', 1],
    ['YDEX', 'Яндекс', 'Акции', 40, 3890, 4212, 38.6, 0, 'RUB', 1],
    ['GAZP', 'Газпром', 'Акции', 800, 168.2, 132.6, -1.18, 0, 'RUB', 1],
    ['SU26238RMFS4', 'ОФЗ 26238', 'Облигации', 150, 598.4, 612.5, 0.9, 14.3, 'RUB', 1],
    ['T', 'Т-Технологии', 'Акции', 25, 2780, 3315, 41.5, 0, 'RUB', 1],
  ],
  3: [
    ['TMOS', 'Т-Капитал Индекс МосБиржи', 'Фонды', 9000, 6.41, 7.12, 0.05, 0, 'RUB', 1],
    ['SNGSP', 'Сургутнефтегаз ап', 'Акции', 3000, 46.8, 58.3, -0.42, 0, 'RUB', 1],
    ['MTSS', 'МТС', 'Акции', 400, 252.1, 236.2, 1.9, 0, 'RUB', 1],
    ['RU000A106Z38', 'РЖД 1Р-28R', 'Облигации', 120, 968.0, 985.2, -0.6, 12.1, 'RUB', 1],
    ['GLDRUB_TOM', 'Золото', 'Драгоценные металлы', 18, 7420, 8655, 62.0, 0, 'RUB', 1],
  ],
  4: [
    ['BTC', 'Bitcoin', 'Криптовалюта', 0.042, 58200, 67240, 812, 0, 'USD', USD],
    ['ETH', 'Ethereum', 'Криптовалюта', 0.9, 2920, 3412, -61, 0, 'USD', USD],
    ['USD000UTSTOM', 'Доллар США', 'Валюта', 1500, 88.1, USD, 0.35, 0, 'RUB', 1],
    ['DEPOSIT', 'Вклад «Накопительный» 18%', 'Вклады', 1, 400000, 412600, 0, 0, 'RUB', 1],
  ],
}

const PORTFOLIOS = [
  { id: 1, name: 'Мой капитал', parent: null, start: 1220, balance: 0 },
  { id: 2, name: 'Т-Инвестиции · ИИС', parent: 1, start: 1180, balance: 18420, broker: 'Т-Инвестиции' },
  { id: 3, name: 'Сбер · Брокерский', parent: 1, start: 900, balance: 6210, broker: 'Сбер Инвестиции' },
  { id: 4, name: 'Крипто и валюта', parent: 1, start: 640, balance: 0 },
]

let assetSeq = 100
let paSeq = 1000

function buildAssets(portfolioId) {
  const rows = POSITIONS[portfolioId] || []
  return rows.map(([ticker, name, type, quantity, avg, last, daily, nkd, cur, rate]) => {
    const isCustom = type === 'Вклады'
    const value = quantity * (last + nkd) * rate
    const invested = quantity * avg * rate
    return {
      portfolio_asset_id: ++paSeq,
      asset_id: ++assetSeq,
      name,
      ticker,
      type,
      properties: {},
      is_custom: isCustom,
      quantity,
      leverage: 1,
      average_price: avg,
      last_price: last,
      accrued_coupon: nkd,
      daily_change: daily,
      profit: round2(value - invested),
      profit_rub: round2(value - invested),
      currency_ticker: cur,
      currency_rate_to_rub: rate,
      first_purchase_date: null,
      first_purchase_price: avg,
      dividend_yield_year_pct: type === 'Акции' ? round2(4 + (ticker.length % 5) * 2.1) : 0,
    }
  })
}

const assetValue = (a) => a.quantity * (Number(a.last_price) + Number(a.accrued_coupon || 0)) * a.currency_rate_to_rub

// ─── история ────────────────────────────────────────────────────────────────
function buildHistory(days, finalValue, finalInvested, finalBalance, seed) {
  const rnd = mulberry32(seed)
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const n = days + 1

  // Пополнения: стартовый взнос + ежемесячные, иногда крупные
  const invested = new Array(n)
  const start = finalInvested * 0.32
  let inv = start
  const steps = []
  for (let i = 0; i < n; i++) {
    if (i > 0 && i % 30 === 0) steps.push(i)
  }
  const perStep = (finalInvested - start) / Math.max(1, steps.length)
  let si = 0
  for (let i = 0; i < n; i++) {
    if (si < steps.length && steps[si] === i) {
      inv += perStep * (0.55 + rnd() * 0.9)
      si++
    }
    invested[i] = inv
  }
  const k = finalInvested / invested[n - 1]
  for (let i = 0; i < n; i++) invested[i] *= k

  // Множитель доходности: случайное блуждание с «мостом» к целевому значению
  const target = Math.log(Math.max(0.2, (finalValue - finalBalance) / finalInvested))
  const walk = new Array(n)
  let w = 0
  let vol = 0.011
  for (let i = 0; i < n; i++) {
    if (i > 0) {
      vol = Math.min(0.03, Math.max(0.006, vol + (rnd() - 0.5) * 0.002))
      const shock = rnd() < 0.006 ? -(0.03 + rnd() * 0.05) : 0
      w += (rnd() - 0.48) * vol * 2 + shock
    }
    walk[i] = w
  }
  const series = []
  let payouts = 0
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1)
    const m = Math.exp(walk[i] - t * (walk[n - 1] - target))
    const bal = finalBalance * (0.4 + 0.6 * t) * (0.7 + rnd() * 0.6)
    const value = invested[i] * m + (i === n - 1 ? finalBalance : bal)
    const date = new Date(today.getTime() - (days - i) * DAY)
    if (date.getUTCDate() === 15) payouts += invested[i] * 0.006
    series.push([
      iso(date),
      round2(value),
      round2(invested[i]),
      round2(payouts),
      round2(value - invested[i]),
      round2(i === n - 1 ? finalBalance : bal),
    ])
  }
  return series
}

function sumSeries(list) {
  const map = new Map()
  for (const series of list) {
    for (const row of series) {
      const cur = map.get(row[0]) || [row[0], 0, 0, 0, 0, 0]
      for (let j = 1; j < 6; j++) cur[j] += row[j]
      map.set(row[0], cur)
    }
  }
  return [...map.values()].sort((a, b) => (a[0] < b[0] ? -1 : 1)).map((r) => r.map((v, j) => (j ? round2(v) : v)))
}

// ─── выплаты ────────────────────────────────────────────────────────────────
function buildPayouts(scale, seed, months, future = false) {
  const rnd = mulberry32(seed)
  const now = new Date()
  const out = []
  for (let i = months; i >= 1; i--) {
    const d = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth() + (future ? months - i + 1 : -i + 1), 1))
    const m = d.getUTCMonth()
    const season = [0.2, 0.15, 0.25, 0.4, 0.9, 1.4, 2.6, 2.1, 0.7, 0.5, 0.35, 1.1][m]
    const dividends = scale * season * (0.6 + rnd() * 0.8) * (future ? 0.85 : 1)
    const coupons = scale * 0.34 * (0.8 + rnd() * 0.4)
    const amortizations = rnd() < 0.12 ? scale * 0.5 * rnd() : 0
    const row = {
      month: monthKey(d),
      dividends: round2(dividends),
      coupons: round2(coupons),
      amortizations: round2(amortizations),
    }
    if (future) {
      row.total_amount = round2(dividends + coupons + amortizations)
      row.payout_count = 1 + Math.floor(rnd() * 5)
    }
    out.push(row)
  }
  return out
}

// ─── сделки ─────────────────────────────────────────────────────────────────
function buildTransactions(portfolios) {
  const rnd = mulberry32(77)
  const txs = []
  let id = 5000
  const now = Date.now()
  for (const p of portfolios) {
    for (const a of p.assets) {
      const count = 2 + Math.floor(rnd() * 4)
      for (let i = 0; i < count; i++) {
        const daysAgo = i === 0 && rnd() < 0.45 ? Math.floor(rnd() * 12) : Math.floor(rnd() * 700)
        const isSell = rnd() < 0.18
        const isAmort = a.type === 'Облигации' && rnd() < 0.2
        const qty = a.type === 'Вклады' ? 1 : Math.max(0.001, round2(a.quantity * (0.1 + rnd() * 0.3)))
        const price = round2(Number(a.average_price) * (0.85 + rnd() * 0.3))
        const date = new Date(now - daysAgo * DAY - Math.floor(rnd() * 8 * 3600000))
        id++
        txs.push({
          id,
          transaction_id: id,
          portfolio_asset_id: a.portfolio_asset_id,
          portfolio_id: p.id,
          portfolio_name: p.name,
          asset_id: a.asset_id,
          asset_name: a.name,
          ticker: a.ticker,
          transaction_type: isAmort ? 'Амортизация' : isSell ? 'Продажа' : 'Покупка',
          transaction_type_id: isAmort ? 3 : isSell ? 2 : 1,
          price,
          quantity: qty,
          transaction_date: date.toISOString(),
          realized_pnl: isSell ? round2(qty * price * (rnd() * 0.2 - 0.05)) : 0,
          currency_ticker: a.currency_ticker,
        })
      }
    }
  }
  return txs.sort((x, y) => (x.transaction_date < y.transaction_date ? 1 : -1))
}

// ─── сборка дашборда ────────────────────────────────────────────────────────
// разрезы по активам и месячные потоки для страницы аналитики
function buildAssetBreakdowns(assets, payouts, rnd) {
  const asset_distribution = assets
    .map((a) => ({ asset_id: a.asset_id, asset_name: a.name, asset_ticker: a.ticker, total_value: round2(assetValue(a)) }))
    .sort((x, y) => y.total_value - x.total_value)

  const asset_returns = assets.map((a) => {
    const value = assetValue(a)
    const invested = a.quantity * a.average_price * a.currency_rate_to_rub
    const payoutsAll = a.type === 'Облигации' ? invested * (0.06 + rnd() * 0.08) : a.type === 'Акции' ? invested * rnd() * 0.07 : 0
    const commissions = invested * 0.003
    const priceChange = value - invested
    const total = priceChange + payoutsAll - commissions
    const yearAgo = invested * (0.82 + rnd() * 0.2)
    const priceYear = value - yearAgo
    const monthAgo = value / (1 + (rnd() - 0.45) * 0.08)
    return {
      asset_id: a.asset_id,
      asset_name: a.name,
      asset_ticker: a.ticker,
      current_value: round2(value),
      invested_amount: round2(invested),
      price_change: round2(priceChange),
      total_payouts: round2(payoutsAll),
      total_commissions: round2(-commissions),
      total_taxes: round2(-payoutsAll * 0.13),
      realized_profit: 0,
      total_return: round2(total),
      return_percent: invested > 0 ? round2((total / invested) * 100) : 0,
      value_year_ago: round2(yearAgo),
      price_change_year: round2(priceYear),
      total_payouts_year: round2(payoutsAll * 0.4),
      total_return_year: round2(priceYear + payoutsAll * 0.4),
      return_percent_year: round2(((priceYear + payoutsAll * 0.4) / yearAgo) * 100),
      value_month_ago: round2(monthAgo),
      price_change_month: round2(value - monthAgo),
      total_return_month: round2(value - monthAgo),
      return_percent_month: round2(((value - monthAgo) / monthAgo) * 100),
    }
  })

  const payoutsTotal = payouts.reduce((s, r) => s + r.dividends + r.coupons, 0)
  const weights = assets.map((a) => (a.type === 'Акции' || a.type === 'Облигации' ? assetValue(a) * (0.5 + rnd()) : 0))
  const wSum = weights.reduce((s, w) => s + w, 0) || 1
  const payouts_by_asset = assets
    .map((a, i) => {
      const amount = (payoutsTotal * weights[i]) / wSum
      return {
        asset_id: a.asset_id,
        asset_name: a.name,
        asset_ticker: a.ticker,
        total_dividends: a.type === 'Акции' ? round2(amount) : 0,
        total_coupons: a.type === 'Облигации' ? round2(amount) : 0,
        total_amortizations: 0,
        total_payouts: round2(amount),
      }
    })
    .filter((r) => r.total_payouts > 0)
    .sort((x, y) => y.total_payouts - x.total_payouts)

  const monthly_flow = payouts.slice(-12).map((r) => {
    const inflow = 20000 + rnd() * 60000 + (rnd() < 0.2 ? 120000 : 0)
    const outflow = rnd() < 0.35 ? -(5000 + rnd() * 40000) : 0
    return { month: r.month, inflow: round2(inflow), outflow: round2(outflow) }
  })

  return { asset_distribution, asset_returns, payouts_by_asset, monthly_flow }
}

function buildAnalytics(totalValue, totalInvested, balance, payouts, future, seed, assets = []) {
  const rnd = mulberry32(seed)
  const breakdowns = buildAssetBreakdowns(assets, payouts, mulberry32(seed + 1000))
  const dividends = payouts.reduce((s, r) => s + r.dividends, 0)
  const coupons = payouts.reduce((s, r) => s + r.coupons, 0)
  const unrealized = totalValue - balance - totalInvested
  const realized = totalInvested * (0.015 + rnd() * 0.02)
  const commissions = totalInvested * 0.0021
  const taxes = (dividends + coupons) * 0.13
  return {
    totals: {
      total_invested: round2(totalInvested),
      total_value: round2(totalValue),
      unrealized_pl: round2(unrealized),
      realized_pl: round2(realized),
      dividends: round2(dividends),
      coupons: round2(coupons),
      commissions: round2(-commissions),
      taxes: round2(-taxes),
      total_profit: round2(unrealized + realized + dividends + coupons - commissions - taxes),
      return_percent: round2(6.4 + rnd() * 3),
      return_percent_on_invested: round2(7.8 + rnd() * 3),
      balance: round2(balance),
      cash_flow: { inflow: round2(totalInvested * 1.1), outflow: round2(totalInvested * 0.1) },
    },
    monthly_payouts: payouts,
    ...breakdowns,
    future_payouts: future,
    operations_breakdown: [],
  }
}

function buildDashboard() {
  const byId = new Map()
  for (const def of PORTFOLIOS) {
    byId.set(def.id, { def, assets: def.parent == null ? [] : buildAssets(def.id) })
  }
  const children = PORTFOLIOS.filter((p) => p.parent === 1)
  const leaf = children.map((def, i) => {
    const { assets } = byId.get(def.id)
    const value = assets.reduce((s, a) => s + assetValue(a), 0) + def.balance
    const invested = assets.reduce((s, a) => s + a.quantity * a.average_price * a.currency_rate_to_rub, 0)
    const series = buildHistory(def.start, value, invested, def.balance, 11 + i * 7)
    const scale = invested / 320
    const payouts = buildPayouts(scale, 31 + i, 36)
    const future = buildPayouts(scale, 51 + i, 12, true)
    const analytics = buildAnalytics(value, invested, def.balance, payouts, future, 91 + i, assets)
    const monthAgo = series[Math.max(0, series.length - 31)]
    return {
      id: def.id,
      name: def.name,
      description: {},
      parent_portfolio_id: def.parent,
      assets,
      history: { series },
      analytics,
      connection: def.broker ? { broker_name: def.broker, status: 'active', last_sync_at: new Date(Date.now() - 3600000 * 3).toISOString() } : null,
      balance: def.balance,
      total_value: round2(value),
      total_invested: round2(invested),
      monthly_change: round2(series[series.length - 1][4] - monthAgo[4]),
    }
  })

  const sumPayouts = (key) => {
    const map = new Map()
    for (const p of leaf) {
      for (const r of p.analytics[key]) {
        const cur = map.get(r.month) || { month: r.month, dividends: 0, coupons: 0, amortizations: 0, total_amount: 0, payout_count: 0 }
        cur.dividends += r.dividends
        cur.coupons += r.coupons
        cur.amortizations += r.amortizations
        cur.total_amount += r.total_amount || 0
        cur.payout_count += r.payout_count || 0
        map.set(r.month, cur)
      }
    }
    return [...map.values()].sort((a, b) => (a.month < b.month ? -1 : 1))
  }

  const rootValue = leaf.reduce((s, p) => s + p.total_value, 0)
  const rootInvested = leaf.reduce((s, p) => s + p.total_invested, 0)
  const rootBalance = leaf.reduce((s, p) => s + p.balance, 0)
  const rootSeries = sumSeries(leaf.map((p) => p.history.series))
  const rootAnalytics = buildAnalytics(rootValue, rootInvested, rootBalance, sumPayouts('monthly_payouts'), sumPayouts('future_payouts'), 7, leaf.flatMap((p) => p.assets))
  const monthAgo = rootSeries[Math.max(0, rootSeries.length - 31)]
  const root = {
    id: 1,
    name: 'Мой капитал',
    description: {
      capital_target_name: 'Финансовая независимость',
      capital_target_value: 6000000,
      capital_target_currency: 'RUB',
      monthly_contribution: 45000,
      annual_return: 14,
      use_inflation: false,
      inflation_rate: 7.5,
    },
    parent_portfolio_id: null,
    assets: [],
    history: { series: rootSeries },
    analytics: rootAnalytics,
    connection: null,
    balance: rootBalance,
    total_value: round2(rootValue),
    total_invested: round2(rootInvested),
    monthly_change: round2(rootSeries[rootSeries.length - 1][4] - monthAgo[4]),
  }

  const portfolios = [root, ...leaf].sort((a, b) => b.total_value - a.total_value)
  const transactions = buildTransactions(leaf)
  return { portfolios, transactions }
}

let state = null
function getState() {
  if (!state) state = buildDashboard()
  return state
}

// ─── история цен и будущие выплаты ──────────────────────────────────────────
function leafAssets(s, portfolioId) {
  const p = s.portfolios.find((x) => x.id === portfolioId)
  if (!p) return []
  if (p.parent_portfolio_id != null) return p.assets.map((a) => ({ ...a, portfolio_id: p.id }))
  return s.portfolios.filter((x) => x.parent_portfolio_id === p.id).flatMap((x) => x.assets.map((a) => ({ ...a, portfolio_id: x.id })))
}

function buildPrices(asset, startDate) {
  if (!asset || asset.is_custom) return []
  const rnd = mulberry32(asset.asset_id * 97)
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const from = startDate ? new Date(startDate) : new Date(today.getTime() - 365 * DAY)
  const days = Math.max(1, Math.round((today - from) / DAY))
  const vol = asset.type === 'Криптовалюта' ? 0.03 : asset.type === 'Облигации' ? 0.002 : 0.014
  const drift = (rnd() - 0.42) * vol * 0.6
  const out = []
  let price = Number(asset.last_price)
  for (let i = 0; i <= days; i++) {
    const d = new Date(today.getTime() - i * DAY)
    const wd = d.getUTCDay()
    if (asset.type !== 'Криптовалюта' && (wd === 0 || wd === 6)) continue
    out.push({ trade_date: iso(d), price: round2(price) })
    price = price / (1 + drift + (rnd() - 0.5) * vol * 2)
  }
  return out.reverse()
}

function buildPayoutPositions(s, portfolioId) {
  const today = new Date()
  today.setUTCHours(0, 0, 0, 0)
  const at = (days) => iso(new Date(today.getTime() + days * DAY))
  const positions = []
  for (const a of leafAssets(s, portfolioId)) {
    const rnd = mulberry32(a.asset_id * 131)
    const payouts = []
    let seq = a.asset_id * 100
    const push = (type, value, record, status = 'expected') => {
      payouts.push({
        id: ++seq,
        type,
        value: round2(value),
        record_date: at(record),
        payment_date: at(record + (type === 'dividend' ? 12 : 0)),
        last_buy_date: at(record - 1),
        basis_quantity: a.quantity,
        expected_total: round2(value * a.quantity),
        status,
      })
    }
    if (a.type === 'Акции') {
      const y = (Number(a.dividend_yield_year_pct) || 6) / 100
      push('dividend', a.last_price * y * 0.55, -150 - Math.floor(rnd() * 60), 'received')
      if (rnd() < 0.75) push(rnd() < 0.3 ? 'forecast' : 'dividend', a.last_price * y * 0.5, 3 + Math.floor(rnd() * 52), rnd() < 0.3 ? 'forecast' : 'expected')
    } else if (a.type === 'Облигации') {
      const monthly = a.ticker.startsWith('RU000')
      const step = monthly ? 30 : 182
      const coupon = (1000 * (monthly ? 0.16 : 0.071)) / (365 / step)
      for (let d = 2 + Math.floor(rnd() * (monthly ? 26 : 40)); d < 75; d += step) push('coupon', coupon, d)
      if (monthly) push('amortization', 100, 41)
    }
    if (!payouts.length) continue
    positions.push({
      portfolio_id: a.portfolio_id,
      asset_id: a.asset_id,
      portfolio_asset_id: a.portfolio_asset_id,
      ticker: a.ticker,
      name: a.name,
      quantity: a.quantity,
      currency_ticker: a.currency_ticker,
      payouts,
    })
  }
  return positions
}

// ─── маршруты ───────────────────────────────────────────────────────────────
const user = () => ({
  id: 1,
  name: 'Алексей',
  email: 'demo@capital-view.ru',
  is_admin: false,
  email_verified: true,
  subscription: {
    status: 'trial',
    has_access: true,
    trial_ends_at: new Date(Date.now() + 9 * DAY).toISOString(),
    access_ends_at: new Date(Date.now() + 9 * DAY).toISOString(),
    current_period_ends_at: null,
  },
})

const supportThread = [
  { id: 1, is_from_admin: false, message: 'Здравствуйте! Подскажите, как добавить второй брокерский счёт?', created_at: new Date(Date.now() - 2 * DAY - 3600000).toISOString() },
  { id: 2, is_from_admin: true, message: 'Добрый день! Откройте «Активы» → «Импорт» и подключите ещё один токен — счёт появится отдельным портфелем.', created_at: new Date(Date.now() - 2 * DAY).toISOString() },
]

const tariffs = [
  { id: 1, name: 'Старт', period_days: 30, price_rub: 390, is_active: true },
  { id: 2, name: 'Оптимальный', period_days: 180, price_rub: 1990, is_active: true },
  { id: 3, name: 'Максимум', period_days: 365, price_rub: 3290, is_active: true },
]

const billingTimeline = () => ({
  registered_at: new Date(Date.now() - 5 * DAY).toISOString(),
  access_ends_at: user().subscription.access_ends_at,
  today: new Date().toISOString(),
  days_left: 9,
  events: [],
})

// ─── деталь актива ──────────────────────────────────────────────────────────
function buildDailyValues(asset, s) {
  const txs = s.transactions.filter((t) => t.portfolio_asset_id === asset.portfolio_asset_id)
  const first = txs.length ? txs[txs.length - 1].transaction_date : new Date(Date.now() - 365 * DAY).toISOString()
  const prices = buildPrices(asset, first.slice(0, 10))
  if (!prices.length) return []
  const n = prices.length
  return prices.map((pr, i) => {
    const qty = round2(asset.quantity * Math.min(1, 0.35 + (0.65 * (i + 1)) / n))
    return { report_date: pr.trade_date, quantity: qty, position_value: round2(qty * pr.price * asset.currency_rate_to_rub) }
  })
}

function buildAssetDetail(s, assetId) {
  const holders = s.portfolios.filter((p) => p.parent_portfolio_id != null)
    .flatMap((p) => p.assets.filter((a) => a.asset_id === assetId).map((a) => ({ a, p })))
  if (!holders.length) return { success: false }
  const { a, p } = holders[0]
  const rnd = mulberry32(assetId * 13)
  const txs = s.transactions.filter((t) => t.asset_id === assetId)
  const payouts = []
  if (a.type === 'Акции' || a.type === 'Облигации') {
    const step = a.type === 'Облигации' ? 182 : 365
    for (let k = -3; k <= 1; k++) {
      const pay = new Date(Date.now() + (k * step + 40) * DAY)
      const rec = new Date(pay.getTime() - 14 * DAY)
      const value = round2(Number(a.last_price) * (a.type === 'Облигации' ? 0.055 : 0.06 + rnd() * 0.05))
      payouts.push({
        type: a.type === 'Облигации' ? 'Купон' : 'Дивиденд',
        value,
        dividend_yield: round2((value / Number(a.last_price)) * 100),
        record_date: iso(rec),
        payment_date: iso(pay),
        last_buy_date: iso(new Date(rec.getTime() - DAY)),
      })
    }
  }
  const cash_operations = payouts.filter((x) => new Date(x.payment_date) < new Date()).map((x, i) => ({
    id: 9000 + i,
    asset_id: assetId,
    type: x.type,
    operation_type: x.type,
    operation_type_id: a.type === 'Облигации' ? 4 : 3,
    amount: round2(x.value * a.quantity * 0.87),
    amount_rub: round2(x.value * a.quantity * 0.87 * a.currency_rate_to_rub),
    currency_ticker: a.currency_ticker,
    operation_date: x.payment_date,
    date: x.payment_date,
  }))
  const portfolios = holders.map(({ a: h, p: hp }) => ({
    portfolio_id: hp.id,
    portfolio_name: hp.name,
    portfolio_asset_id: h.portfolio_asset_id,
    quantity: h.quantity,
    average_price: h.average_price,
    last_price: h.last_price,
    accrued_coupon: h.accrued_coupon,
    daily_change: h.daily_change,
    leverage: 1,
    currency_ticker: h.currency_ticker,
    currency_rate_to_rub: h.currency_rate_to_rub,
    ticker: h.ticker,
    realized_pnl: round2(txs.filter((t) => t.portfolio_asset_id === h.portfolio_asset_id).reduce((x, t) => x + (t.realized_pnl || 0), 0)),
    payouts: round2(cash_operations.reduce((x, o) => x + o.amount_rub, 0)),
    commissions: round2(-h.quantity * h.average_price * h.currency_rate_to_rub * 0.003),
    asset_value: round2(assetValue(h)),
    invested_value: round2(h.quantity * h.average_price * h.currency_rate_to_rub),
    total_pnl: round2(h.profit_rub),
    portfolio_total_value: hp.total_value,
  }))
  return {
    success: true,
    portfolios,
    portfolio_asset: {
      id: a.portfolio_asset_id,
      portfolio_id: p.id,
      asset_id: assetId,
      name: a.name,
      ticker: a.ticker,
      type: a.type,
      leverage: 1,
      last_price: a.last_price,
      daily_change: a.daily_change,
      currency_ticker: a.currency_ticker,
      currency_rate_to_rub: a.currency_rate_to_rub,
      transactions: txs.filter((t) => t.portfolio_asset_id === a.portfolio_asset_id),
      price_history: buildPrices(a, iso(new Date(Date.now() - 3 * 365 * DAY))),
      daily_values: buildDailyValues(a, s),
      cash_operations,
      payouts,
    },
  }
}

// ---------------------------------------------------------------------------
// Подключения брокеров и задачи импорта (форма подключения, окно статуса, настройки).
// Задача проходит «очередь → загрузка → готово» за несколько секунд.
// В токене слово «bad» — брокер отклонит токен, «dup» — счёт уже подключён,
// «expire» — проверку пройдёт, но импорт упадёт с token_invalid.
// ---------------------------------------------------------------------------

const BROKERS = [
  { id: 1, name: 'Т-Инвестиции' },
  { id: 2, name: 'БКС' },
]

const hoursAgo = (h) => new Date(Date.now() - h * 3600000).toISOString()

const brokerConnections = [
  {
    id: 1, portfolio_id: 2, portfolio_name: 'Т-Инвестиции · ИИС', broker_id: 1,
    token_mask: 't.Fq••••3f9a', has_token: true, auto_sync: true,
    last_sync_at: hoursAgo(3), last_sync_status: 'ok', last_sync_error: null,
    last_sync_summary: { inserted_count: 6, accounts: [{ account: 'ИИС' }, { account: 'Брокерский счёт' }] },
  },
  {
    id: 2, portfolio_id: 4, portfolio_name: 'БКС · Брокерский', broker_id: 2,
    token_mask: 'eyJh••••Qx2c', has_token: true, auto_sync: true,
    last_sync_at: hoursAgo(26 * 24), last_sync_status: 'token_invalid',
    last_sync_error: 'Брокер не принял токен: он отозван или истёк. Выпустите новый и обновите его здесь.',
    last_sync_summary: { inserted_count: 0, accounts: [{ account: 'Брокерский счёт' }] },
  },
  {
    id: 3, portfolio_id: 5, portfolio_name: 'Т-Инвестиции · Семейный', broker_id: 1,
    token_mask: 't.Zk••••91be', has_token: true, auto_sync: false,
    last_sync_at: hoursAgo(50), last_sync_status: 'error',
    last_sync_error: 'Т-Инвестиции временно не отвечают. Попробуем снова при следующей синхронизации.',
    last_sync_summary: null,
  },
]

const mockTasks = new Map()
let nextTaskId = 900

const demoImportResult = (portfolioId) => ({
  portfolio_id: portfolioId,
  import_result: {
    inserted_count: 418,
    kept_manual_count: 3,
    accounts: [
      {
        account: 'Брокерский счёт',
        portfolio_id: portfolioId,
        inserted_count: 391,
        skipped_count: 1,
        skipped_operations: [{ type: 'Coupon', isin: 'RU000A105RJ8', date: '2024-11-14T00:00:00', reason: 'asset_not_found' }],
        failed_count: 0,
        failed_operations: [],
        suppressed_count: 2,
        matched_manual_count: 3,
        transfer_count: 2,
        transfers: [
          { direction: 'in', date: '2023-02-06T12:00:00', ticker: 'SBER', name: 'Сбербанк', quantity: 120, price: 152.4, price_source: 'broker_average' },
          { direction: 'in', date: '2023-02-06T12:00:00', ticker: 'RU000A0JXQ93', name: 'ОФЗ 26222', quantity: 15, price: 0, price_source: 'unknown' },
        ],
        reconciliation: { mismatch_count: 0, mismatches: [] },
      },
      {
        account: 'ИИС',
        portfolio_id: portfolioId,
        inserted_count: 27,
        skipped_count: 0,
        failed_count: 0,
        transfer_count: 0,
        transfers: [],
        reconciliation: {
          mismatch_count: 1,
          mismatches: [{ ticker: 'YDEX', name: 'Яндекс', broker_quantity: 5, portfolio_quantity: 4 }],
        },
      },
    ],
  },
})

function createMockTask(portfolioId, { tokenInvalid = false } = {}) {
  const task = { id: nextTaskId++, portfolio_id: portfolioId, created: Date.now(), tokenInvalid, cancelled: false }
  mockTasks.set(task.id, task)
  return task
}

function mockTaskStatus(task) {
  const t = (Date.now() - task.created) / 1000
  const base = { task_id: task.id, portfolio_id: task.portfolio_id, broker_id: 1, trigger: 'manual', started_at: null, completed_at: null, error_message: null, result: null }
  if (task.cancelled) return { ...base, status: 'cancelled', progress: 0 }
  if (t < 1.5) return { ...base, status: 'pending', progress: 0, progress_message: 'В очереди' }
  if (task.tokenInvalid && t >= 3) {
    return {
      ...base, status: 'failed', progress: 10,
      error_message: 'Брокер не принял токен: он отозван или истёк. Выпустите новый токен и обновите его в настройках.',
      result: { error_code: 'token_invalid' }, completed_at: new Date().toISOString(),
    }
  }
  if (t < 7) {
    const progress = Math.min(95, Math.round(10 + (t - 1.5) * 16))
    const progress_message = progress < 40 ? 'Получаем операции у брокера' : progress < 75 ? 'Записываем операции' : 'Сверяем позиции с брокером'
    return { ...base, status: 'processing', progress, progress_message, started_at: new Date(task.created).toISOString() }
  }
  const conn = brokerConnections.find((c) => c.portfolio_id === task.portfolio_id)
  if (conn && !task.applied) {
    task.applied = true
    Object.assign(conn, { last_sync_at: new Date().toISOString(), last_sync_status: 'ok', last_sync_error: null })
  }
  return { ...base, status: 'completed', progress: 100, progress_message: 'Готово', result: demoImportResult(task.portfolio_id), completed_at: new Date().toISOString() }
}

function activeTaskFor(portfolioId) {
  for (const task of mockTasks.values()) {
    if (task.portfolio_id !== portfolioId) continue
    const st = mockTaskStatus(task)
    if (st.status === 'pending' || st.status === 'processing') return { task_id: task.id, status: st.status, progress: st.progress }
  }
  return null
}

function routeBrokers(method, path, body) {
  if (path === '/portfolios/brokers') return { brokers: BROKERS }
  if (path === '/broker-connections/' && method === 'get') {
    return { connections: brokerConnections.map((c) => ({ ...c, active_task: activeTaskFor(c.portfolio_id) })) }
  }
  if (path === '/broker-connections/check-token') {
    const token = String(body?.token || '')
    if (/bad/i.test(token)) return { __status: 400, detail: 'Брокер не принял токен. Проверьте, что скопировали его целиком и он не отозван.' }
    const dup = /dup/i.test(token) ? brokerConnections.find((c) => c.broker_id === body?.broker_id) : null
    return {
      accounts: [
        { id: '2000123', name: 'Брокерский счёт', type: 'ACCOUNT_TYPE_TINKOFF', status: 'ACCOUNT_STATUS_OPEN' },
        { id: '2000456', name: 'ИИС', type: 'ACCOUNT_TYPE_TINKOFF_IIS', status: 'ACCOUNT_STATUS_OPEN' },
        { id: '2000789', name: 'Старый счёт', type: 'ACCOUNT_TYPE_TINKOFF', status: 'ACCOUNT_STATUS_CLOSED' },
      ],
      already_connected: dup ? { portfolio_id: dup.portfolio_id, portfolio_name: dup.portfolio_name } : null,
    }
  }
  if (path === '/broker-connections/sync') {
    const tasks = brokerConnections
      .filter((c) => c.has_token && c.last_sync_status !== 'token_invalid')
      .map((c) => ({ portfolio_id: c.portfolio_id, portfolio_name: c.portfolio_name, connection_id: c.id, task_id: createMockTask(c.portfolio_id).id }))
    return { results: tasks, tasks, message: `Запущено обновлений: ${tasks.length}` }
  }
  let m = path.match(/^\/broker-connections\/(\d+)\/sync$/)
  if (m) {
    const c = brokerConnections.find((x) => x.id === Number(m[1]))
    if (!c) return { __status: 404, detail: 'Подключение не найдено' }
    if (c.last_sync_status === 'token_invalid') return { __status: 409, detail: 'Брокер не принимает сохранённый токен — укажите новый.' }
    const active = activeTaskFor(c.portfolio_id)
    if (active) return { task_id: active.task_id, already_active: true }
    return { task_id: createMockTask(c.portfolio_id).id, already_active: false }
  }
  m = path.match(/^\/broker-connections\/(\d+)\/token$/)
  if (m) {
    const c = brokerConnections.find((x) => x.id === Number(m[1]))
    if (/bad/i.test(String(body?.token || ''))) return { __status: 400, detail: 'Брокер не принял токен. Проверьте, что скопировали его целиком.' }
    const token = String(body?.token || '')
    Object.assign(c, { has_token: true, token_mask: `${token.slice(0, 4)}••••${token.slice(-4)}`, last_sync_status: null, last_sync_error: null })
    return { connection: c, task: body?.sync_now ? { task_id: createMockTask(c.portfolio_id).id } : null }
  }
  m = path.match(/^\/broker-connections\/(\d+)$/)
  if (m) {
    const i = brokerConnections.findIndex((x) => x.id === Number(m[1]))
    if (method === 'patch' && i >= 0) Object.assign(brokerConnections[i], { auto_sync: !!body?.auto_sync })
    if (method === 'delete' && i >= 0) brokerConnections.splice(i, 1)
    return {}
  }
  if (path === '/portfolios/import-broker') {
    const portfolioId = body?.portfolio_id || 2
    const task = createMockTask(portfolioId, { tokenInvalid: /bad|expire/i.test(String(body?.token || '')) })
    return { task_id: task.id, status: 'pending', portfolio_id: portfolioId }
  }
  m = path.match(/^\/portfolios\/(\d+)\/sync$/)
  if (m) return { task_id: createMockTask(Number(m[1])).id }
  m = path.match(/^\/tasks\/(\d+)\/(status|cancel)$/)
  if (m) {
    const task = mockTasks.get(Number(m[1]))
    if (!task) return { __status: 404, detail: 'Задача не найдена' }
    if (m[2] === 'cancel') {
      if (mockTaskStatus(task).status !== 'pending') return { __status: 409, detail: 'Импорт уже идёт — его нельзя отменить' }
      task.cancelled = true
      return {}
    }
    return mockTaskStatus(task)
  }
  if (path === '/tasks/user/list') return { tasks: [] }
  return null
}

function route(method, url, params, body) {
  const s = getState()
  const path = url.replace(/^https?:\/\/[^/]+/, '').replace(/^\/api\/v1/, '').split('?')[0]

  const brokerData = routeBrokers(method, path, body)
  if (brokerData) return brokerData
  if (path === '/auth/check-token') return { user: user() }
  if (path === '/dashboard/') {
    return {
      dashboard: {
        portfolios: s.portfolios,
        recent_transactions: s.transactions.slice(0, 10),
        missed_payouts_count: 2,
      },
    }
  }
  if (path === '/reference/version') return { reference_version: 'demo-1' }
  if (path === '/reference/') {
    return {
      reference_version: 'demo-1',
      reference: {
        currencies: [
          { id: 1, ticker: 'RUB', name: 'Российский рубль' },
          { id: 2, ticker: 'USD', name: 'Доллар США' },
          { id: 3, ticker: 'EUR', name: 'Евро' },
        ],
        currency_rates_to_rub: { USD: USD, EUR: 100.2, CNY: 12.9 },
      },
    }
  }
  if (path === '/reference/assets/search') {
    const q = String(params?.q || '').toLowerCase()
    const all = s.portfolios.flatMap((p) => p.assets)
    const seen = new Set()
    const assets = all
      .filter((a) => !seen.has(a.asset_id) && seen.add(a.asset_id))
      .filter((a) => a.name.toLowerCase().includes(q) || a.ticker.toLowerCase().includes(q))
      .map((a) => ({ id: a.asset_id, name: a.name, ticker: a.ticker, type: a.type, last_price: a.last_price }))
    return { assets }
  }
  if (path === '/transactions/') return { transactions: s.transactions }
  if (path === '/operations/') return { operations: [] }
  if (path.startsWith('/missed-payouts')) return { missed_payouts: [] }
  if (path === '/support/messages') return { messages: supportThread }
  if (path === '/support/message' && method === 'post') {
    supportThread.push({ id: supportThread.length + 1, is_from_admin: false, message: String(body?.message || ''), created_at: new Date().toISOString() })
    return {}
  }
  if (path === '/billing/public') return { trial_days: 14, tariffs }
  if (path === '/billing/me') return { subscription: user().subscription, tariffs, trial_days: 14, timeline: billingTimeline(), payments: [] }
  if (/^\/portfolios\/\d+\/description$/.test(path) && method !== 'get') {
    const id = Number(path.split('/')[2])
    const p = s.portfolios.find((x) => x.id === id)
    if (p && body) {
      p.description = {
        ...p.description,
        capital_target_value: body.capital_target_value ?? body.targetAmount ?? p.description.capital_target_value,
        monthly_contribution: body.monthly_contribution ?? body.monthlyContribution ?? p.description.monthly_contribution,
        annual_return: body.annual_return ?? body.annualReturn ?? p.description.annual_return,
        use_inflation: body.use_inflation ?? body.useInflation ?? p.description.use_inflation,
        inflation_rate: body.inflation_rate ?? body.inflationRate ?? p.description.inflation_rate,
      }
    }
    return { description: p ? [{ id: p.id, name: p.name, description: { ...p.description } }] : [] }
  }
  if (/^\/assets\/\d+\/detail$/.test(path)) {
    return buildAssetDetail(s, Number(path.split('/')[2]))
  }
  if (/^\/assets\/portfolio\/\d+\/daily-values$/.test(path)) {
    const paId = Number(path.split('/')[3])
    const hit = s.portfolios.flatMap((p) => p.assets).find((a) => a.portfolio_asset_id === paId)
    return { success: true, values: hit ? buildDailyValues(hit, s) : [] }
  }
  if (/^\/assets\/\d+\/prices$/.test(path)) {
    const id = Number(path.split('/')[2])
    const asset = s.portfolios.flatMap((p) => p.assets).find((a) => a.asset_id === id)
    return { prices: buildPrices(asset, params?.start_date), currency_ticker: asset?.currency_ticker || 'RUB' }
  }
  if (/^\/portfolios\/\d+\/payout-positions$/.test(path)) {
    return { positions: buildPayoutPositions(s, Number(path.split('/')[2])) }
  }
  return {}
}

export function installMockApi() {
  apiClient.defaults.adapter = async (config) => {
    let body = config.data
    if (typeof body === 'string') {
      try { body = JSON.parse(body) } catch { /* not json */ }
    }
    const { __status, ...data } = route((config.method || 'get').toLowerCase(), config.url || '', config.params, body)
    await new Promise((r) => setTimeout(r, 280 + Math.random() * 320))
    if (__status) {
      // как ответ FastAPI с ошибкой: apiErrorMessage возьмёт detail
      const error = new Error(data.detail || 'demo error')
      error.config = config
      error.response = { data, status: __status, statusText: 'Error', headers: {}, config }
      throw error
    }
    return {
      data: { success: true, message: 'demo', ...data },
      status: 200,
      statusText: 'OK',
      headers: {},
      config,
      request: {},
    }
  }
  if (!localStorage.getItem('access_token')) localStorage.setItem('access_token', 'demo')
  console.info('[CapitalView] Демо-режим: запросы к API обслуживаются src/dev/mockApi.js')
}
