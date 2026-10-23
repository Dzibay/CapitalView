<script setup>
/**
 * ⌘K / Ctrl+K: разделы, действия, портфели, активы портфеля и поиск по справочнику бумаг.
 */
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import {
  Search, CornerDownLeft, ArrowUp, ArrowDown, Eye, EyeOff, LayoutGrid, PanelLeft, Bell, LogOut,
  FolderTree, Globe, Loader2,
} from 'lucide-vue-next'
import { useDashboardStore } from '../../stores/dashboard.store'
import { useUIStore } from '../../stores/ui.store'
import { authService } from '../../services/authService.js'
import { searchReferenceAssets } from '../../services/referenceService'
import { privacyMode, togglePrivacyMode } from '../../utils/privacyMode'
import { paletteOpen, closePalette, dashboardEditing, missedPayoutsOpen } from '../state'
import { buildNavSections } from '../nav'
import { flattenPortfolioTree } from '../portfolioTree'
import { moneyCompact } from '../format'
import { typeColor } from '../palette'

const props = defineProps({
  user: { type: Object, default: null },
})

const router = useRouter()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const query = ref('')
const input = ref(null)
const listEl = ref(null)
const active = ref(0)

const isAdmin = computed(() => Boolean(props.user?.is_admin))
const norm = (s) => String(s || '').toLowerCase().replace(/ё/g, 'е')

function score(item, q) {
  if (!q) return 1
  const label = norm(item.label)
  const hay = `${label} ${norm(item.hint)} ${norm(item.keywords)}`
  if (label.startsWith(q)) return 3
  if (label.includes(` ${q}`)) return 2.5
  if (hay.includes(q)) return 2
  // все слова запроса встречаются где-то
  const words = q.split(/\s+/).filter(Boolean)
  return words.length > 1 && words.every((w) => hay.includes(w)) ? 1.5 : 0
}

// ─── источники ───────────────────────────────────────────────────────────
const pageItems = computed(() =>
  buildNavSections(props.user).flatMap((s) =>
    s.items.map((it) => ({
      id: `page:${it.link}`,
      group: 'Разделы',
      label: it.name,
      hint: it.locked ? 'По подписке' : s.title,
      icon: it.icon,
      keywords: it.keywords,
      run: () => router.push(it.locked ? '/billing' : it.link),
    })),
  ),
)

const actionItems = computed(() => {
  const list = [
    {
      id: 'act:privacy',
      group: 'Действия',
      label: privacyMode.value ? 'Показать суммы' : 'Скрыть суммы',
      hint: 'Приватный режим',
      keywords: 'приватность скрыть деньги privacy',
      icon: privacyMode.value ? Eye : EyeOff,
      run: togglePrivacyMode,
    },
    {
      id: 'act:sidebar',
      group: 'Действия',
      label: uiStore.isSidebarCollapsed ? 'Развернуть меню' : 'Свернуть меню',
      keywords: 'сайдбар панель',
      icon: PanelLeft,
      run: () => uiStore.toggleSidebar(),
    },
  ]
  if (!isAdmin.value) {
    list.unshift({
      id: 'act:layout',
      group: 'Действия',
      label: 'Настроить дашборд',
      hint: 'Порядок и размер виджетов',
      keywords: 'виджеты раскладка редактировать',
      icon: LayoutGrid,
      run: async () => {
        if (router.currentRoute.value.path !== '/dashboard') await router.push('/dashboard')
        dashboardEditing.value = true
      },
    })
    const n = dashboardStore.missedPayoutsCount || 0
    list.push({
      id: 'act:missed',
      group: 'Действия',
      label: 'Неполученные выплаты',
      hint: n ? `${n}` : '',
      keywords: 'дивиденды купоны уведомления',
      icon: Bell,
      run: () => { missedPayoutsOpen.value = true },
    })
  }
  list.push({
    id: 'act:logout',
    group: 'Действия',
    label: 'Выйти из аккаунта',
    keywords: 'logout выход',
    icon: LogOut,
    run: () => { authService.logout(); router.push('/login') },
  })
  return list
})

const portfolioItems = computed(() =>
  isAdmin.value
    ? []
    : flattenPortfolioTree(dashboardStore.portfolios || []).map(({ portfolio: p, depth }) => ({
        id: `pf:${p.id}`,
        group: 'Портфели',
        label: p.name,
        hint: moneyCompact(p.total_value),
        icon: FolderTree,
        indent: depth,
        current: p.id === uiStore.selectedPortfolioId,
        run: () => uiStore.setSelectedPortfolioId(p.id),
      })),
)

const assetItems = computed(() => {
  if (isAdmin.value) return []
  const seen = new Map()
  for (const p of dashboardStore.portfolios || []) {
    for (const a of p.assets || []) {
      if (!a.asset_id || Number(a.quantity) === 0) continue
      const value = Number(a.quantity) * (Number(a.last_price) + Number(a.accrued_coupon || 0)) * (Number(a.currency_rate_to_rub) || 1) / (Number(a.leverage) || 1)
      const prev = seen.get(a.asset_id)
      if (prev) prev.value += value
      else seen.set(a.asset_id, { a, value })
    }
  }
  return [...seen.values()]
    .sort((x, y) => y.value - x.value)
    .map(({ a, value }) => ({
      id: `asset:${a.asset_id}`,
      group: 'Мои активы',
      label: a.name,
      hint: moneyCompact(value),
      ticker: a.ticker,
      keywords: `${a.ticker} ${a.type}`,
      dot: typeColor(a.type),
      run: () => router.push(`/assets/${a.asset_id}`),
    }))
})

// ─── поиск по справочнику ────────────────────────────────────────────────
const remote = ref([])
const remoteLoading = ref(false)
let remoteTimer = null
let remoteSeq = 0
watch(query, (q) => {
  clearTimeout(remoteTimer)
  const s = q.trim()
  if (isAdmin.value || s.length < 2) {
    remote.value = []
    remoteLoading.value = false
    return
  }
  remoteLoading.value = true
  remoteTimer = setTimeout(async () => {
    const seq = ++remoteSeq
    try {
      const list = await searchReferenceAssets(s, 8)
      if (seq !== remoteSeq) return
      const own = new Set(assetItems.value.map((i) => i.id))
      remote.value = list
        .filter((r) => !own.has(`asset:${r.id}`))
        .map((r) => ({
          id: `ref:${r.id}`,
          group: 'Биржа',
          label: r.name,
          ticker: r.ticker,
          icon: Globe,
          run: () => router.push(`/assets/${r.id}`),
        }))
    } catch {
      if (seq === remoteSeq) remote.value = []
    } finally {
      if (seq === remoteSeq) remoteLoading.value = false
    }
  }, 220)
})

// ─── итоговый список ─────────────────────────────────────────────────────
const groups = computed(() => {
  const q = norm(query.value.trim())
  const take = (items, limit) =>
    items
      .map((it) => ({ it, s: score(it, q) }))
      .filter((x) => x.s > 0)
      .sort((a, b) => b.s - a.s)
      .slice(0, limit)
      .map((x) => x.it)

  const out = []
  const push = (title, items) => { if (items.length) out.push({ title, items }) }
  if (q) {
    push('Мои активы', take(assetItems.value, 6))
    push('Разделы', take(pageItems.value, 6))
    push('Портфели', take(portfolioItems.value, 5))
    push('Действия', take(actionItems.value, 6))
    push('Биржа', remote.value)
  } else {
    push('Разделы', pageItems.value)
    push('Действия', actionItems.value)
    push('Портфели', portfolioItems.value)
    push('Мои активы', assetItems.value.slice(0, 5))
  }
  return out
})

const flat = computed(() => groups.value.flatMap((g) => g.items))
watch(flat, () => { if (active.value >= flat.value.length) active.value = 0 })
watch(query, () => { active.value = 0 })

function run(item) {
  closePalette()
  item?.run?.()
}

function move(delta) {
  const n = flat.value.length
  if (!n) return
  active.value = (active.value + delta + n) % n
  nextTick(() => {
    listEl.value?.querySelector('.is-active')?.scrollIntoView({ block: 'nearest' })
  })
}

function onInputKey(e) {
  if (e.key === 'ArrowDown') { e.preventDefault(); move(1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1) }
  else if (e.key === 'Enter') { e.preventDefault(); run(flat.value[active.value]) }
  else if (e.key === 'Escape') { e.preventDefault(); closePalette() }
}

// ─── горячие клавиши ─────────────────────────────────────────────────────
function onGlobalKey(e) {
  if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K' || e.code === 'KeyK')) {
    e.preventDefault()
    paletteOpen.value = !paletteOpen.value
  }
}
onMounted(() => window.addEventListener('keydown', onGlobalKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))

watch(paletteOpen, (open) => {
  if (open) {
    query.value = ''
    active.value = 0
    nextTick(() => input.value?.focus())
  }
})

const indexOf = (item) => flat.value.indexOf(item)
</script>

<template>
  <Teleport to="body">
    <div class="cv">
      <Transition name="cv-cmd">
        <div v-if="paletteOpen" class="cv-cmd" @pointerdown.self="closePalette">
          <div class="cv-cmd__panel" role="dialog" aria-modal="true" aria-label="Командная палитра">
            <div class="cv-cmd__search">
              <Search :size="18" class="cv-cmd__search-icon" />
              <input
                ref="input"
                v-model="query"
                type="text"
                placeholder="Найти актив, раздел или действие…"
                autocomplete="off"
                spellcheck="false"
                aria-label="Поиск"
                @keydown="onInputKey"
              />
              <Loader2 v-if="remoteLoading" :size="16" class="cv-cmd__spin" />
              <kbd class="cv-kbd">Esc</kbd>
            </div>

            <div ref="listEl" class="cv-cmd__list" role="listbox">
              <template v-if="flat.length">
                <div v-for="g in groups" :key="g.title" class="cv-cmd__group">
                  <div class="cv-cmd__gtitle">{{ g.title }}</div>
                  <button
                    v-for="item in g.items"
                    :key="item.id"
                    type="button"
                    role="option"
                    class="cv-cmd__item"
                    :class="{ 'is-active': indexOf(item) === active }"
                    :aria-selected="indexOf(item) === active"
                    :style="item.indent ? { paddingLeft: `${12 + item.indent * 18}px` } : null"
                    @mousemove="active = indexOf(item)"
                    @click="run(item)"
                  >
                    <span class="cv-cmd__icon">
                      <span v-if="item.dot" class="cv-cmd__dot" :style="{ background: item.dot }" />
                      <component :is="item.icon" v-else :size="16" />
                    </span>
                    <span class="cv-cmd__label">{{ item.label }}</span>
                    <span v-if="item.ticker" class="cv-cmd__ticker">{{ item.ticker }}</span>
                    <span v-if="item.current" class="cv-cmd__current">текущий</span>
                    <span v-if="item.hint" class="cv-cmd__hint cv-num">{{ item.hint }}</span>
                    <CornerDownLeft :size="14" class="cv-cmd__enter" />
                  </button>
                </div>
              </template>
              <div v-else-if="!remoteLoading" class="cv-cmd__empty">
                Ничего не нашлось по запросу «{{ query }}»
              </div>
            </div>

            <div class="cv-cmd__foot">
              <span><kbd class="cv-kbd"><ArrowUp :size="11" /></kbd><kbd class="cv-kbd"><ArrowDown :size="11" /></kbd> выбрать</span>
              <span><kbd class="cv-kbd"><CornerDownLeft :size="11" /></kbd> открыть</span>
              <span class="cv-cmd__brand">CapitalView</span>
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </Teleport>
</template>

<style scoped>
.cv { background: none; }
.cv-cmd {
  position: fixed; inset: 0; z-index: 2000;
  display: flex; justify-content: center; align-items: flex-start;
  padding: 12vh 16px 16px;
  background: rgba(3, 4, 8, .62);
  backdrop-filter: blur(6px); -webkit-backdrop-filter: blur(6px);
}
.cv-cmd__panel {
  width: min(640px, 100%); max-height: min(560px, 76vh);
  display: flex; flex-direction: column; overflow: hidden;
  border-radius: 20px;
  background: rgba(17, 20, 29, .94);
  backdrop-filter: blur(24px) saturate(160%); -webkit-backdrop-filter: blur(24px) saturate(160%);
  box-shadow: var(--cv-pop-shadow), 0 0 0 1px rgba(124, 142, 255, .12), 0 40px 120px -20px rgba(91, 116, 255, .25);
}
.cv-cmd__search {
  display: flex; align-items: center; gap: 12px; height: 60px; padding: 0 18px; flex: none;
  box-shadow: inset 0 -1px 0 var(--cv-line);
}
.cv-cmd__search-icon { color: var(--cv-mut); flex: none; }
.cv-cmd__search input {
  flex: 1; min-width: 0; height: 100%; border: 0; outline: 0; background: transparent;
  font: 500 16px/1 var(--cv-text); color: var(--cv-ink); letter-spacing: -0.01em;
}
.cv-cmd__search input::placeholder { color: var(--cv-dim); }
.cv-cmd__spin { color: var(--cv-mut); animation: cv-spin 1s linear infinite; }
@keyframes cv-spin { to { transform: rotate(360deg); } }

.cv-cmd__list { flex: 1; min-height: 0; overflow-y: auto; padding: 6px 8px 8px; overscroll-behavior: contain; }
.cv-cmd__group + .cv-cmd__group { margin-top: 4px; }
.cv-cmd__gtitle { padding: 10px 12px 6px; font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim); }
.cv-cmd__item {
  position: relative; display: flex; align-items: center; gap: 12px; width: 100%; height: 42px; padding: 0 12px;
  border: 0; border-radius: 12px; background: transparent; cursor: pointer; text-align: left;
  color: var(--cv-ink-2); font-size: 13.5px;
}
.cv-cmd__item.is-active { background: rgba(91, 116, 255, .14); color: var(--cv-ink); box-shadow: inset 0 0 0 1px rgba(124, 142, 255, .18); }
.cv-cmd__icon {
  display: grid; place-items: center; width: 28px; height: 28px; border-radius: 9px; flex: none;
  color: var(--cv-mut); background: rgba(255, 255, 255, .045); box-shadow: inset 0 0 0 1px var(--cv-line);
}
.cv-cmd__item.is-active .cv-cmd__icon { color: var(--cv-accent-ink); background: rgba(91, 116, 255, .16); }
.cv-cmd__dot { width: 9px; height: 9px; border-radius: 3px; }
.cv-cmd__label { flex: 0 1 auto; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-cmd__ticker {
  flex: none; padding: 2px 6px; border-radius: 6px; font-size: 11px; font-weight: 600; color: var(--cv-mut);
  background: rgba(255, 255, 255, .05);
}
.cv-cmd__current { flex: none; font-size: 11px; color: var(--cv-accent-ink); }
.cv-cmd__hint { margin-left: auto; flex: none; font-size: 12.5px; color: var(--cv-mut); }
.cv-cmd__enter { flex: none; color: var(--cv-mut); opacity: 0; margin-left: 4px; }
.cv-cmd__hint + .cv-cmd__enter { margin-left: 4px; }
.cv-cmd__label + .cv-cmd__enter, .cv-cmd__ticker + .cv-cmd__enter, .cv-cmd__current + .cv-cmd__enter { margin-left: auto; }
.cv-cmd__item.is-active .cv-cmd__enter { opacity: 1; }
.cv-cmd__empty { padding: 36px 16px; text-align: center; color: var(--cv-mut); font-size: 13.5px; }

.cv-cmd__foot {
  display: flex; align-items: center; gap: 16px; height: 42px; padding: 0 18px; flex: none;
  box-shadow: inset 0 1px 0 var(--cv-line); font-size: 12px; color: var(--cv-dim);
}
.cv-cmd__foot span { display: inline-flex; align-items: center; gap: 6px; }
.cv-cmd__foot .cv-kbd { min-width: 18px; height: 18px; padding: 0 3px; }
.cv-cmd__brand { margin-left: auto; font-weight: 600; background: var(--cv-grad); -webkit-background-clip: text; background-clip: text; color: transparent; }

.cv-cmd-enter-active { transition: opacity .2s ease; }
.cv-cmd-leave-active { transition: opacity .15s ease; }
.cv-cmd-enter-active .cv-cmd__panel { transition: transform .32s var(--cv-ease), opacity .2s; }
.cv-cmd-leave-active .cv-cmd__panel { transition: transform .15s ease, opacity .15s; }
.cv-cmd-enter-from, .cv-cmd-leave-to { opacity: 0; }
.cv-cmd-enter-from .cv-cmd__panel { transform: translateY(-10px) scale(.97); opacity: 0; }
.cv-cmd-leave-to .cv-cmd__panel { transform: scale(.98); opacity: 0; }

@media (max-width: 768px) {
  .cv-cmd { padding: 10px; }
  .cv-cmd__panel { max-height: calc(100dvh - 20px - var(--cv-bottom-h)); }
  .cv-cmd__foot { display: none; }
}
</style>
