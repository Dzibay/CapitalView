import { PAYOUT_COLORS } from '../palette'

/** Типы выплат страницы «Выплаты»: прогноз дивиденда считается дивидендом. */
export const PAYOUT_KINDS = {
  dividend: { label: 'Дивиденды', one: 'Дивиденд', color: PAYOUT_COLORS.dividends },
  coupon: { label: 'Купоны', one: 'Купон', color: PAYOUT_COLORS.coupons },
  amortization: { label: 'Амортизация', one: 'Амортизация', color: PAYOUT_COLORS.amortizations },
}
export const KIND_ORDER = ['dividend', 'coupon', 'amortization']

export const kindOf = (type) => (PAYOUT_KINDS[type] ? type : 'dividend')

export const MONTHS = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
export const MONTHS_IN = ['январе', 'феврале', 'марте', 'апреле', 'мае', 'июне', 'июле', 'августе', 'сентябре', 'октябре', 'ноябре', 'декабре']
export const MONTHS_SHORT = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек']
export const MONTHS_GEN = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']
