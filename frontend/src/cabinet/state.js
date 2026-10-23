import { ref } from 'vue'

/** Общее состояние оболочки кабинета: палитра команд, режим настройки дашборда, окно выплат. */
export const paletteOpen = ref(false)
export const dashboardEditing = ref(false)
export const missedPayoutsOpen = ref(false)

export function openPalette() { paletteOpen.value = true }
export function closePalette() { paletteOpen.value = false }

export const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent)
export const modKey = isMac ? '⌘' : 'Ctrl'
