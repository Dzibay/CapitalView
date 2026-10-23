/**
 * Текст ошибки для пользователя из ответа API.
 * Бэкенд отвечает { success: false, error, error_code } (иногда detail — строка или объект);
 * axios-сообщение «Request failed with status code 400» пользователю не показываем.
 */
export function apiErrorMessage(error, fallback = 'Что-то пошло не так. Попробуйте ещё раз.') {
  const data = error?.response?.data
  const detail = data?.detail
  // Ошибка валидации: конкретнее «Ошибка валидации данных» — текст из валидатора поля
  const validation = (data?.details?.validation_errors || [])
    .map((e) => String(e.message || '').replace(/^Value error,\s*/, ''))
    .filter(Boolean)
  const text =
    validation[0] ||
    data?.error ||
    (typeof detail === 'string' ? detail : detail?.error)
  if (text) return text
  if (error?.response) return fallback
  if (error?.request) return 'Нет связи с сервером. Проверьте интернет и попробуйте ещё раз.'
  return error?.message || fallback
}

export function apiErrorCode(error) {
  const data = error?.response?.data
  return data?.error_code || data?.detail?.error_code || null
}
