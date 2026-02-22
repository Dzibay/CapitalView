/**
 * Утилиты для форматирования валюты
 * Используются во всех виджетах для единообразного форматирования
 */

/**
 * Форматирует число как валюту RUB
 * @param {number} value - Значение для форматирования
 * @param {object} options - Дополнительные опции форматирования
 * @returns {string} Отформатированная строка
 */
export const formatCurrency = (value, options = {}) => {
  const {
    currency = 'RUB',
    maximumFractionDigits = 0,
    minimumFractionDigits = 0,
    ...restOptions
  } = options

  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    maximumFractionDigits,
    minimumFractionDigits,
    ...restOptions
  }).format(value || 0)
}

/**
 * Форматирует число как валюту RUB (сокращенная версия)
 * @param {number} value - Значение для форматирования
 * @returns {string} Отформатированная строка
 */
export const formatMoney = (value) => {
  return formatCurrency(value, { maximumFractionDigits: 0 })
}

/**
 * Форматирует число как процент
 * @param {number} value - Значение в процентах (например, 5.5 для 5.5%)
 * @param {object} options - Дополнительные опции форматирования
 * @returns {string} Отформатированная строка
 */
export const formatPercent = (value, options = {}) => {
  const {
    minimumFractionDigits = 2,
    maximumFractionDigits = 2,
    ...restOptions
  } = options

  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits,
    maximumFractionDigits,
    ...restOptions
  }).format((value || 0) / 100)
}

/**
 * Форматирует сумму операции с точностью до 6 знаков после запятой
 * Используется для отображения операций (выплаты, комиссии и т.д.), где важна точность
 * @param {number} value - Значение для форматирования
 * @param {string} currency - Валюта (по умолчанию 'RUB')
 * @returns {string} Отформатированная строка
 */
export const formatOperationAmount = (value, currency = 'RUB') => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0 ₽'
  }

  // Нормализуем код валюты: берем только первые 3 символа и приводим к верхнему регистру
  // Это защищает от некорректных значений типа "RUB000UTSTOM"
  let normalizedCurrency = 'RUB'
  if (currency && typeof currency === 'string') {
    // Извлекаем первые 3 символа и проверяем, что это буквы
    const currencyCode = currency.trim().substring(0, 3).toUpperCase()
    // Список валидных кодов валют (ISO 4217)
    const validCurrencyCodes = ['RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
    if (validCurrencyCodes.includes(currencyCode)) {
      normalizedCurrency = currencyCode
    }
  }

  const numValue = Number(value)
  
  // Если число целое - показываем без дробной части
  if (numValue % 1 === 0) {
    try {
      return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: normalizedCurrency,
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
      }).format(numValue)
    } catch (error) {
      // Если валюта не поддерживается Intl.NumberFormat, используем наш формат
      const currencySymbols = {
        'RUB': '₽',
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'CNY': '¥',
        'JPY': '¥',
        'BTC': '₿',
        'ETH': 'Ξ',
        'USDT': '₮',
        'USDC': '₮',
        'BNB': 'BNB',
        'SOL': '◎'
      }
      const symbol = currencySymbols[normalizedCurrency] || normalizedCurrency
      return `${new Intl.NumberFormat('ru-RU').format(numValue)} ${symbol}`
    }
  }

  // Для дробных чисел используем toFixed(6) и убираем лишние нули
  // Это гарантирует точность до 6 знаков после запятой
  let formatted = numValue.toFixed(6)
  
  // Убираем лишние нули в конце (но сохраняем минимум один знак, если число < 1)
  formatted = formatted.replace(/\.?0+$/, '')
  
  // Если после удаления нулей осталась только точка, добавляем один ноль
  if (formatted.endsWith('.')) {
    formatted = formatted.slice(0, -1)
  }
  
  // Разделяем на целую и дробную части
  const parts = formatted.split('.')
  let integerPart = parts[0]
  const fractionPart = parts[1] || ''
  
  // Для отрицательных чисел обрабатываем знак отдельно
  const isNegative = integerPart.startsWith('-')
  if (isNegative) {
    integerPart = integerPart.slice(1)
  }
  
  // Форматируем целую часть с разделителями тысяч
  const integerNum = parseInt(integerPart) || 0
  const formattedInteger = new Intl.NumberFormat('ru-RU').format(integerNum)
  
  // Определяем символ валюты
  const currencySymbols = {
    'RUB': '₽',
    'USD': '$',
    'EUR': '€',
    'GBP': '£',
    'CNY': '¥',
    'JPY': '¥',
    'BTC': '₿',
    'ETH': 'Ξ',
    'USDT': '₮',
    'USDC': '₮',
    'BNB': 'BNB',
    'SOL': '◎'
  }
  const currencySymbol = currencySymbols[normalizedCurrency] || normalizedCurrency
  
  // Возвращаем отформатированное значение
  const sign = isNegative ? '-' : ''
  return fractionPart 
    ? `${sign}${formattedInteger},${fractionPart} ${currencySymbol}`
    : `${sign}${formattedInteger} ${currencySymbol}`
}