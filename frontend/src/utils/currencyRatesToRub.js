/**
 * Курсы из referenceData.currency_rates_to_rub (тикер валютного инструмента → руб. за 1 ед.).
 * Согласовано с currency_rate_to_rub в get_portfolio_assets.
 */

export function stripMoexCurrencySuffix(ticker) {
  if (!ticker || typeof ticker !== 'string') return ''
  return ticker.replace(/\d+|UTSTOM/gi, '').toUpperCase()
}

export function isRubLikeTicker(ticker) {
  const c = stripMoexCurrencySuffix(ticker || '')
  return c === 'RUB' || c === 'SUR'
}

/**
 * @param {string} currencyTicker
 * @param {Record<string, number|string>|null|undefined} ratesMap
 * @returns {number|null} рублей за 1 единицу валюты; null если не RUB и курс не найден
 */
export function rubPerUnitFromRatesMap(currencyTicker, ratesMap) {
  if (isRubLikeTicker(currencyTicker)) return 1
  if (!ratesMap || typeof ratesMap !== 'object') return null

  const t = String(currencyTicker || '').trim()
  let v = ratesMap[t]
  if (v != null && Number(v) > 0) return Number(v)

  const base = stripMoexCurrencySuffix(t)
  if (base === 'RUB' || base === 'SUR') return 1

  v = ratesMap[base]
  if (v != null && Number(v) > 0) return Number(v)

  for (const [key, val] of Object.entries(ratesMap)) {
    if (val == null || Number(val) <= 0) continue
    if (stripMoexCurrencySuffix(key) === base) return Number(val)
  }

  return null
}

/**
 * @param {number} amount — сумма в валюте выплаты
 * @param {string} currencyTicker
 * @param {{ currency_rates_to_rub?: Record<string, number|string> }|null|undefined} referenceData
 * @returns {number|null}
 */
export function payoutAmountToRub(amount, currencyTicker, referenceData) {
  const rates = referenceData?.currency_rates_to_rub
  const rate = rubPerUnitFromRatesMap(currencyTicker, rates)
  if (rate == null) return null
  return Number(amount) * rate
}
