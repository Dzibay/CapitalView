import { SERIES, NEUTRAL, OTHER } from '../palette'

/**
 * Группы операций страницы «Операции». Цвет закреплён за группой, а не за рангом;
 * dir — куда откладывается столбик на графике активности: 1 — вверх от нуля, -1 — вниз.
 */
export const OP_GROUPS = {
  buy: { label: 'Покупки', color: SERIES[0], dir: 1 },
  sell: { label: 'Продажи', color: SERIES[1], dir: -1 },
  deposit: { label: 'Пополнения', color: SERIES[0], dir: 1 },
  payout: { label: 'Выплаты', color: SERIES[1], dir: 1 },
  withdraw: { label: 'Выводы', color: NEUTRAL, dir: -1 },
  fee: { label: 'Налоги и комиссии', color: SERIES[5], dir: -1 },
  other: { label: 'Прочее', color: OTHER, dir: 1 },
}

export const TX_ORDER = ['buy', 'sell']
export const OP_ORDER = ['deposit', 'payout', 'withdraw', 'fee', 'other']

/** нормализованный тип (buy, dividend, tax…) → группа */
export function groupOf(slug) {
  if (slug === 'dividend' || slug === 'coupon' || slug === 'amortization') return 'payout'
  if (slug === 'tax' || slug === 'commission') return 'fee'
  return OP_GROUPS[slug] ? slug : 'other'
}
