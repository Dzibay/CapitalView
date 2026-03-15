/**
 * Плагин Pinia для автоматической синхронизации состояния с localStorage.
 *
 * Использование — добавьте опцию `persist` в определение store:
 *
 *   defineStore('ui', {
 *     state: () => ({ ... }),
 *     persist: ['selectedPortfolioId', 'expandedPortfolios'],
 *     ...
 *   })
 *
 * При создании store плагин загружает перечисленные ключи из localStorage.
 * При каждом изменении состояния записывает их обратно.
 * Формат ключа в хранилище: `pinia:<storeId>:<key>`.
 */

function tryParse(raw) {
  try {
    return JSON.parse(raw)
  } catch {
    return raw
  }
}

function storageKey(storeId, key) {
  return `pinia:${storeId}:${key}`
}

export function piniaPersistedState({ store, options }) {
  const keys = options.persist
  if (!keys || !Array.isArray(keys) || keys.length === 0) return

  const legacyMap = options.persistLegacyKeys || {}

  // Загрузка сохранённого состояния из localStorage
  for (const key of keys) {
    const sk = storageKey(store.$id, key)
    try {
      let raw = localStorage.getItem(sk)

      // Миграция из старого ключа, если новый ещё не существует
      if (raw === null && legacyMap[key]) {
        const legacyRaw = localStorage.getItem(legacyMap[key])
        if (legacyRaw !== null) {
          raw = legacyRaw
          localStorage.setItem(sk, raw)
          localStorage.removeItem(legacyMap[key])
        }
      }

      if (raw !== null) {
        store.$patch({ [key]: tryParse(raw) })
      }
    } catch {
      // localStorage недоступен — пропускаем
    }
  }

  // Сохранение при изменении состояния
  store.$subscribe((_mutation, state) => {
    for (const key of keys) {
      try {
        const val = state[key]
        const sk = storageKey(store.$id, key)
        if (val === null || val === undefined) {
          localStorage.removeItem(sk)
        } else {
          localStorage.setItem(sk, JSON.stringify(val))
        }
      } catch {
        // игнорируем ошибки записи
      }
    }
  })
}
