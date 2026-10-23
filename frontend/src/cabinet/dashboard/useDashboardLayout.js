import { computed, reactive, watch } from 'vue'

/**
 * Раскладка главной: порядок, ширина и скрытые виджеты.
 * Хранится в localStorage; неизвестные id отбрасываются, новые виджеты добавляются в конец.
 */
const KEY = 'cv:dashboard-layout:v2'

/** Ширина в колонках 12-колоночной сетки (на планшете и телефоне сужается в CSS). */
export const SPAN = { s: 4, m: 6, l: 8, xl: 12 }

export const WIDGETS = {
  capital: { title: 'Капитал', size: 'l', sizes: ['m', 'l', 'xl'] },
  profit: { title: 'Прибыль', size: 's', sizes: ['s', 'm'] },
  insights: { title: 'Инсайты', size: 'xl', sizes: ['xl'] },
  allocation: { title: 'Состав портфеля', size: 'm', sizes: ['m', 'l', 'xl'] },
  top: { title: 'Крупнейшие позиции', size: 'm', sizes: ['m', 'l', 'xl'] },
  payouts: { title: 'Выплаты', size: 'm', sizes: ['m', 'l', 'xl'] },
  calendar: { title: 'Календарь выплат', size: 'm', sizes: ['s', 'm', 'l'] },
  movers: { title: 'Движение за день', size: 's', sizes: ['s', 'm'] },
  goal: { title: 'Цель', size: 's', sizes: ['s', 'm'] },
  income: { title: 'Пассивный доход', size: 's', sizes: ['s', 'm'] },
  transactions: { title: 'Последние операции', size: 'xl', sizes: ['l', 'xl'] },
}

const DEFAULT_ORDER = Object.keys(WIDGETS)

function defaults() {
  return {
    order: [...DEFAULT_ORDER],
    sizes: Object.fromEntries(DEFAULT_ORDER.map((id) => [id, WIDGETS[id].size])),
    hidden: [],
  }
}

function load() {
  const base = defaults()
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || 'null')
    if (!raw || typeof raw !== 'object') return base
    const known = (id) => Object.prototype.hasOwnProperty.call(WIDGETS, id)
    const order = Array.isArray(raw.order) ? raw.order.filter(known) : []
    for (const id of DEFAULT_ORDER) if (!order.includes(id)) order.push(id)
    const sizes = { ...base.sizes }
    for (const [id, s] of Object.entries(raw.sizes || {})) {
      if (known(id) && WIDGETS[id].sizes.includes(s)) sizes[id] = s
    }
    const hidden = Array.isArray(raw.hidden) ? [...new Set(raw.hidden.filter(known))] : []
    return { order: [...new Set(order)], sizes, hidden }
  } catch {
    return base
  }
}

export function useDashboardLayout() {
  const state = reactive(load())

  watch(state, () => {
    try { localStorage.setItem(KEY, JSON.stringify(state)) } catch { /* приватный режим браузера */ }
  }, { deep: true })

  /** Видимые виджеты в порядке раскладки — именно этот список сортирует перетаскивание. */
  const visible = computed({
    get: () => state.order.filter((id) => !state.hidden.includes(id)),
    set: (ids) => {
      // скрытые остаются на своих местах относительно соседей — просто встраиваем новый порядок видимых
      const hiddenSet = new Set(state.hidden)
      const next = []
      let k = 0
      for (const id of state.order) next.push(hiddenSet.has(id) ? id : ids[k++])
      for (; k < ids.length; k++) next.push(ids[k])
      state.order = next
    },
  })

  const hiddenList = computed(() => state.order.filter((id) => state.hidden.includes(id)))
  const isCustom = computed(() => JSON.stringify(state) !== JSON.stringify(defaults()))

  const resize = (id, size) => { if (WIDGETS[id]?.sizes.includes(size)) state.sizes[id] = size }
  const hide = (id) => { if (!state.hidden.includes(id)) state.hidden.push(id) }
  const show = (id) => { state.hidden = state.hidden.filter((h) => h !== id) }
  const reset = () => Object.assign(state, defaults())

  return { state, visible, hiddenList, isCustom, resize, hide, show, reset }
}
