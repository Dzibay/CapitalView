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
