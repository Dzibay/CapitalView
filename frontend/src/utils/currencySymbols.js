const currencySymbols = {
  RUB: '₽',
  USD: '$',
  EUR: '€',
  GBP: '£',
  CNY: '¥',
  JPY: '¥',
  CHF: '₣',
  KZT: '₸',
  UAH: '₴',
  USDT: '₮',
}

export function getCurrencySymbol(ticker) {
  if (!ticker) return ''
  const clean = ticker.replace(/\d+|UTSTOM/gi, '').toUpperCase()
  return currencySymbols[clean] || clean
}
