import { privacyMode, maskAmount, PRIVACY_MASK } from '../utils/privacyMode'

const nf = new Map()
function getFormat(key, options) {
  let f = nf.get(key)
  if (!f) {
    f = new Intl.NumberFormat('ru-RU', options)
    nf.set(key, f)
  }
  return f
}

const mask = (s) => (privacyMode.value ? maskAmount(s) : s)

/** 1 234 567 ₽ (sign: '+' для положительных) */
export function money(value, { digits = 0, sign = false, currency = 'RUB' } = {}) {
  const v = Number(value) || 0
  const s = getFormat(`m${digits}${currency}`, {
    style: 'currency', currency, minimumFractionDigits: digits, maximumFractionDigits: digits,
  }).format(Math.abs(v))
  const prefix = v < 0 ? '−' : sign && v > 0 ? '+' : ''
  return mask(prefix + s)
}

const CUR_SYMBOL = { USDT: '₮' }

/** Сумма в валюте актива: тикеры вида USD000UTSTOM приводятся к ISO-коду, нестандартные — числом и символом. */
export function moneyIn(value, ticker, { digits = 0, sign = false } = {}) {
  const code = String(ticker || 'RUB').replace(/\d+|UTSTOM/gi, '').toUpperCase() || 'RUB'
  if (/^[A-Z]{3}$/.test(code)) {
    try { return money(value, { digits, sign, currency: code }) } catch { /* неизвестный код */ }
  }
  const v = Number(value) || 0
  const prefix = v < 0 ? '−' : sign && v > 0 ? '+' : ''
  return mask(`${prefix}${getFormat(`n${digits}`, { maximumFractionDigits: digits }).format(Math.abs(v))} ${CUR_SYMBOL[code] || code}`)
}

/** 2,49 млн ₽ */
export function moneyCompact(value, { sign = false } = {}) {
  const v = Number(value) || 0
  const abs = Math.abs(v)
  const s = abs < 100000
    ? getFormat('m0RUB', { style: 'currency', currency: 'RUB', maximumFractionDigits: 0 }).format(abs)
    : getFormat('mc', { style: 'currency', currency: 'RUB', notation: 'compact', maximumFractionDigits: abs < 1e7 ? 2 : 1 }).format(abs)
  const prefix = v < 0 ? '−' : sign && v > 0 ? '+' : ''
  return mask(prefix + s)
}

/** Короткая подпись для осей: 2,5 млн / 840 тыс. */
export function axisMoney(value) {
  if (privacyMode.value) return PRIVACY_MASK.slice(0, 3)
  const abs = Math.abs(value)
  if (abs >= 1e6) return `${(value / 1e6).toLocaleString('ru-RU', { maximumFractionDigits: 1 })} млн`
  if (abs >= 1e3) return `${Math.round(value / 1e3).toLocaleString('ru-RU')} тыс`
  return Math.round(value).toLocaleString('ru-RU')
}

/** +12,4% */
export function pct(value, { digits = 1, sign = true } = {}) {
  const v = Number(value) || 0
  const s = getFormat(`p${digits}`, { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Math.abs(v))
  const prefix = v < 0 ? '−' : sign && v > 0 ? '+' : ''
  return `${prefix}${s}%`
}

export function num(value, digits = 0) {
  return getFormat(`n${digits}`, { maximumFractionDigits: digits }).format(Number(value) || 0)
}

const dShort = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'short' })
const dLong = new Intl.DateTimeFormat('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' })
const dMonth = new Intl.DateTimeFormat('ru-RU', { month: 'short', year: '2-digit' })
const dMonthLong = new Intl.DateTimeFormat('ru-RU', { month: 'long', year: 'numeric' })

const toDate = (d) => (d instanceof Date ? d : new Date(d))
export const dateShort = (d) => dShort.format(toDate(d)).replace('.', '')
export const dateLong = (d) => dLong.format(toDate(d)).replace(' г.', '')
export const monthShort = (d) => dMonth.format(toDate(d)).replace('.', '').replace(' г', '')
export const monthLong = (d) => {
  const s = dMonthLong.format(toDate(d)).replace(' г.', '')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export function plural(n, one, few, many) {
  const a = Math.abs(n) % 100
  const b = a % 10
  if (a > 10 && a < 20) return many
  if (b > 1 && b < 5) return few
  if (b === 1) return one
  return many
}

export const trendClass = (v) => (v > 0 ? 'is-up' : v < 0 ? 'is-down' : '')
