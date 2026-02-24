/**
 * Утилиты для работы с датами
 * Аналогично backend/app/utils/date.py
 * 
 * Основные функции:
 * - normalizeDateToString: нормализует дату в формат YYYY-MM-DD
 * - formatDateForDisplay: форматирует дату для отображения (DD.MM.YYYY)
 * - extractDateFromString: извлекает дату из строки в формате YYYY-MM-DD
 */

/**
 * Нормализует дату в формат YYYY-MM-DD
 * Обрабатывает различные форматы входящих дат, избегая проблем с часовыми поясами
 * 
 * @param {string|Date|any} date - Дата в любом формате
 * @returns {string|null} - Дата в формате YYYY-MM-DD или null
 */
export function normalizeDateToString(date) {
  if (!date) return null
  
  // Если это уже строка в формате YYYY-MM-DD, возвращаем её
  if (typeof date === 'string') {
    // Проверяем, является ли это валидным форматом YYYY-MM-DD
    if (date.match(/^\d{4}-\d{2}-\d{2}$/)) {
      return date
    }
    
    // Если это ISO строка с временем, извлекаем только дату
    if (date.includes('T')) {
      const datePart = date.split('T')[0]
      if (datePart.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return datePart
      }
    }
    
    // Пытаемся найти дату в формате YYYY-MM-DD в строке
    const dateMatch = date.match(/(\d{4}-\d{2}-\d{2})/)
    if (dateMatch) {
      return dateMatch[1]
    }
    
    // Если строка содержит пробел, берем первую часть
    if (date.includes(' ')) {
      const datePart = date.split(' ')[0]
      if (datePart.match(/^\d{4}-\d{2}-\d{2}$/)) {
        return datePart
      }
    }
  }
  
  // Если это объект Date, используем UTC методы для избежания проблем с часовыми поясами
  if (date instanceof Date) {
    if (isNaN(date.getTime())) {
      return null
    }
    const year = date.getUTCFullYear()
    const month = String(date.getUTCMonth() + 1).padStart(2, '0')
    const day = String(date.getUTCDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }
  
  // Для других типов пытаемся преобразовать в Date
  try {
    const dateObj = new Date(date)
    if (isNaN(dateObj.getTime())) {
      return null
    }
    // Используем UTC методы
    const year = dateObj.getUTCFullYear()
    const month = String(dateObj.getUTCMonth() + 1).padStart(2, '0')
    const day = String(dateObj.getUTCDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  } catch (e) {
    return null
  }
}

/**
 * Форматирует дату для отображения в формате DD.MM.YYYY
 * 
 * @param {string|Date|any} date - Дата в любом формате
 * @returns {string} - Отформатированная дата или пустая строка
 */
export function formatDateForDisplay(date) {
  if (!date) return ''
  
  // Сначала нормализуем дату в YYYY-MM-DD
  const normalizedDate = normalizeDateToString(date)
  if (!normalizedDate) return ''
  
  // Извлекаем компоненты даты
  const [year, month, day] = normalizedDate.split('-')
  if (!year || !month || !day) return ''
  
  return `${day}.${month}.${year}`
}

/**
 * Извлекает дату из строки в формате YYYY-MM-DD
 * Используется для безопасного извлечения даты без создания Date объекта
 * 
 * @param {string} dateString - Строка с датой
 * @returns {string|null} - Дата в формате YYYY-MM-DD или null
 */
export function extractDateFromString(dateString) {
  if (!dateString || typeof dateString !== 'string') return null
  
  // Если это уже формат YYYY-MM-DD
  if (dateString.match(/^\d{4}-\d{2}-\d{2}$/)) {
    return dateString
  }
  
  // Пытаемся найти дату в формате YYYY-MM-DD
  const dateMatch = dateString.match(/(\d{4}-\d{2}-\d{2})/)
  if (dateMatch) {
    return dateMatch[1]
  }
  
  return null
}

/**
 * Сравнивает две даты
 * 
 * @param {string|Date|any} date1 - Первая дата
 * @param {string|Date|any} date2 - Вторая дата
 * @returns {number} - -1 если date1 < date2, 0 если равны, 1 если date1 > date2
 */
export function compareDates(date1, date2) {
  const normalized1 = normalizeDateToString(date1)
  const normalized2 = normalizeDateToString(date2)
  
  if (!normalized1 && !normalized2) return 0
  if (!normalized1) return -1
  if (!normalized2) return 1
  
  if (normalized1 < normalized2) return -1
  if (normalized1 > normalized2) return 1
  return 0
}

/**
 * Проверяет, является ли дата валидной
 * 
 * @param {string|Date|any} date - Дата для проверки
 * @returns {boolean} - true если дата валидна
 */
export function isValidDate(date) {
  const normalized = normalizeDateToString(date)
  if (!normalized) return false
  
  const dateObj = new Date(normalized + 'T00:00:00')
  return !isNaN(dateObj.getTime())
}
