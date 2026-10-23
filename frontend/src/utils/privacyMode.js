import { ref, watch } from 'vue'

/**
 * Приватный режим: скрывает денежные суммы во всём кабинете.
 * Проценты и количества остаются видимыми. Состояние хранится в localStorage.
 * formatCurrency / formatOperationAmount читают ref во время рендера, поэтому
 * переключение сразу перерисовывает все компоненты, которые ими пользуются.
 */
const STORAGE_KEY = 'cv:privacy'

function readInitial() {
  try {
    return localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

export const privacyMode = ref(readInitial())

watch(privacyMode, (on) => {
  try {
    localStorage.setItem(STORAGE_KEY, on ? '1' : '0')
  } catch {
    // localStorage недоступен — режим живёт до перезагрузки
  }
})

export function togglePrivacyMode() {
  privacyMode.value = !privacyMode.value
}

export const PRIVACY_MASK = '•••••'

/** «−1 234,50 ₽» → «••••• ₽»: знак и цифры скрываются, символ валюты остаётся. */
export function maskAmount(formatted) {
  return String(formatted).replace(/[-−+]?\d[\d\s  .,]*/, `${PRIVACY_MASK} `).replace(/\s+$/, '').replace(/\s{2,}/g, ' ')
}
