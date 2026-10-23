import { effectiveUnitPriceInCurrency } from '../../utils/effectiveAssetPrice'
import { isDepositLikePortfolioAsset } from '../../utils/depositAssetType'

const isBond = (type) => /bond|облига/i.test(String(type || ''))

/** Дивдоходность за 12 месяцев: с сервера, иначе по выплатам с отсечкой за последний год. */
function dividendYield(a) {
  if (a.dividend_yield_year_pct != null && a.dividend_yield_year_pct !== '') return Number(a.dividend_yield_year_pct) || 0
  const payouts = a.payouts || a.dividends || []
  const price = Number(a.last_price) || 0
  if (!payouts.length || !price) return 0
  const to = new Date()
  const from = new Date(to.getFullYear() - 1, to.getMonth(), to.getDate())
  const sum = payouts
    .filter((d) => (!d.type || String(d.type).toLowerCase() === 'dividend') && d.record_date)
    .filter((d) => { const t = new Date(d.record_date); return t > from && t <= to })
    .reduce((s, d) => s + (parseFloat(d.value) || 0), 0)
  return (sum / price) * 100
}

/**
 * Позиция портфеля → строка таблицы активов. Все суммы в рублях, кроме цен (в валюте бумаги).
 *  - profit — результат с покупки (с сервера), ret — он же в % от вложенного;
 *  - day — изменение стоимости за день.
 */
export function toHolding(a, portfolio) {
  const qty = Number(a.quantity) || 0
  const lev = Number(a.leverage) || 1
  const rate = Number(a.currency_rate_to_rub) || 1
  const price = effectiveUnitPriceInCurrency(a)
  const value = Math.max(0, (qty * price * rate) / lev)
  const profit = Number(a.profit_rub ?? a.profit ?? 0) || 0
  const invested = value - profit
  const dayUnit = Number(a.daily_change) || 0
  const last = Number(a.last_price) || 0
  const bond = isBond(a.type)
  return {
    id: a.portfolio_asset_id,
    assetId: a.asset_id,
    raw: a,
    name: a.name || a.ticker || '—',
    ticker: a.ticker || '',
    type: a.type || 'Другое',
    custom: !!a.is_custom,
    deposit: isDepositLikePortfolioAsset(a),
    sold: qty === 0,
    qty,
    leverage: lev,
    price,
    avg: Number(a.average_price) || 0,
    currency: a.currency_ticker || 'RUB',
    value,
    profit,
    ret: invested > 0 ? (profit / invested) * 100 : 0,
    day: (dayUnit * qty * rate) / lev,
    dayPct: last ? (dayUnit / last) * 100 : 0,
    income: bond ? Number(a.properties?.coupon_percent) || null : dividendYield(a) || null,
    incomeKind: bond ? 'купон' : 'див.',
    portfolioId: portfolio?.id ?? a.portfolio_id,
    portfolioName: portfolio?.name || '',
  }
}

export const SORTS = {
  value: (r) => r.value,
  profit: (r) => r.profit,
  ret: (r) => r.ret,
  day: (r) => r.dayPct,
  income: (r) => r.income ?? -Infinity,
  name: (r) => r.name.toLowerCase(),
}

export function sortRows(rows, key, dir) {
  const get = SORTS[key] || SORTS.value
  const k = dir === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    const x = get(a)
    const y = get(b)
    if (x === y) return b.value - a.value
    return x > y ? k : -k
  })
}
