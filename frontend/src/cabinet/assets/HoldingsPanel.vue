<script setup>
/**
 * Панель позиций страницы «Активы»: поиск, режим «по портфелям / все позиции», сортировка по колонкам.
 * В режиме портфелей у каждого узла дерева своя секция с прямыми позициями и свободными деньгами;
 * на узком экране таблица заменяется карточками.
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, MoreHorizontal, ChevronDown, ArrowDown, ArrowUp, Loader2, Wallet } from 'lucide-vue-next'
import CvSegmented from '../ui/CvSegmented.vue'
import ToggleSwitch from '../../components/base/ToggleSwitch.vue'
import { useContextMenu } from '../../composables/useContextMenu'
import { typeColor } from '../palette'
import { money, moneyIn, pct, num, plural } from '../format'
import { toHolding, sortRows } from './holdings'

const props = defineProps({
  /** [{ portfolio, depth }] — выбранная ветка в порядке дерева */
  nodes: { type: Array, default: () => [] },
  updating: { type: Object, default: () => new Set() },
  showSold: { type: Boolean, default: false },
})
const emit = defineEmits(['update:showSold'])
const router = useRouter()
const { openMenu } = useContextMenu()

// ── режим, поиск, сортировка ─────────────────────────────────────────────
const MODES = [
  { value: 'groups', label: 'По портфелям' },
  { value: 'flat', label: 'Все позиции' },
]
const mode = ref(localStorage.getItem('cv.assets.mode') === 'flat' ? 'flat' : 'groups')
watch(mode, (m) => localStorage.setItem('cv.assets.mode', m))

const query = ref('')
const sort = ref({ key: 'value', dir: 'desc' })
function sortBy(key) {
  sort.value = sort.value.key === key
    ? { key, dir: sort.value.dir === 'desc' ? 'asc' : 'desc' }
    : { key, dir: key === 'name' ? 'asc' : 'desc' }
}

const matches = (r) => {
  const q = query.value.trim().toLowerCase()
  return !q || r.name.toLowerCase().includes(q) || r.ticker.toLowerCase().includes(q)
}

// ── строки ───────────────────────────────────────────────────────────────
const allRows = computed(() =>
  props.nodes.flatMap(({ portfolio }) =>
    (portfolio.assets || []).map((a) => toHolding(a, portfolio)).filter((r) => props.showSold || !r.sold),
  ),
)
const total = computed(() => {
  const root = props.nodes[0]?.portfolio
  return Number(root?.total_value) || allRows.value.reduce((s, r) => s + r.value, 0) + cashTotal.value || 1
})
const cashTotal = computed(() => props.nodes.reduce((s, n) => s + (Number(n.portfolio.balance) || 0), 0))
const share = (v) => (v / total.value) * 100
const maxShare = computed(() => Math.max(1, ...allRows.value.map((r) => share(r.value))))

const flatRows = computed(() => sortRows(allRows.value.filter(matches), sort.value.key, sort.value.dir))

const collapsed = ref(new Set(JSON.parse(localStorage.getItem('cv.assets.collapsed') || '[]')))
function toggle(id) {
  const s = new Set(collapsed.value)
  s.has(id) ? s.delete(id) : s.add(id)
  collapsed.value = s
  localStorage.setItem('cv.assets.collapsed', JSON.stringify([...s]))
}

const sections = computed(() => {
  const searching = !!query.value.trim()
  return props.nodes
    .map(({ portfolio: p, depth }) => {
      const own = allRows.value.filter((r) => r.portfolioId === p.id)
      const rows = sortRows(own.filter(matches), sort.value.key, sort.value.dir)
      const cash = Number(p.balance) || 0
      return {
        id: p.id,
        raw: p,
        name: p.name,
        depth,
        value: Number(p.total_value) || 0,
        count: own.length,
        rows,
        cash: !searching && cash ? cash : 0,
        open: searching || !collapsed.value.has(p.id),
        hidden: searching && !rows.length,
        broker: !!p.connection?.broker_id,
      }
    })
    .filter((s) => !s.hidden)
})

const shownCount = computed(() => (mode.value === 'flat' ? flatRows.value.length : sections.value.reduce((s, x) => s + x.rows.length, 0)))
const hasPositions = computed(() => allRows.value.length > 0)

// ── узкий экран → карточки ───────────────────────────────────────────────
const mq = typeof window !== 'undefined' ? window.matchMedia('(max-width: 1024px)') : null
const cards = ref(!!mq?.matches)
const onMq = (e) => { cards.value = e.matches }
onMounted(() => mq?.addEventListener('change', onMq))
onBeforeUnmount(() => mq?.removeEventListener('change', onMq))

// ── форматирование ───────────────────────────────────────────────────────
const tone = (v) => (v > 0 ? 'cv-up' : v < 0 ? 'cv-down' : '')
const fmtPrice = (r) => moneyIn(r.price, r.currency, { digits: r.price < 10 ? 4 : 2 }).replace(/(,\d*?[1-9])0+(?=\D)|,0+(?=\D)/, '$1')
const fmtAvg = (r) => moneyIn(r.avg, r.currency, { digits: r.avg < 10 ? 4 : 2 }).replace(/(,\d*?[1-9])0+(?=\D)|,0+(?=\D)/, '$1')
const fmtQty = (r) => num(r.qty, r.qty % 1 ? 6 : 0)

const COLS = [
  { key: 'name', label: 'Актив', cls: 'c-name' },
  { key: null, label: 'Цена', cls: 'r c-price' },
  { key: 'value', label: 'Стоимость', cls: 'r' },
  { key: 'profit', label: 'Прибыль', cls: 'r' },
  { key: 'day', label: 'За день', cls: 'r' },
  { key: 'income', label: 'Доход', cls: 'r c-inc' },
]

function open(r) {
  if (r.assetId != null) router.push(`/assets/${r.assetId}`)
}
</script>

<template>
  <section class="hp cv-card">
    <!-- панель инструментов -->
    <div class="hp__bar">
      <label class="hp__search">
        <Search :size="15" class="hp__search-ic" />
        <input v-model="query" class="hp__input" type="search" placeholder="Поиск по названию или тикеру" />
        <button v-if="query" type="button" class="hp__clear" aria-label="Очистить" @click="query = ''">×</button>
      </label>
      <CvSegmented v-model="mode" :options="MODES" size="sm" aria-label="Группировка" />
      <ToggleSwitch :model-value="showSold" label="Проданные" @update:model-value="emit('update:showSold', $event)" />
    </div>

    <!-- пусто -->
    <div v-if="!hasPositions && mode === 'flat'" class="hp__empty">
      <b>Позиций пока нет</b>
      <p>Добавьте актив вручную или импортируйте портфель из брокера.</p>
    </div>
    <div v-else-if="query && !shownCount" class="hp__empty">
      <b>Ничего не найдено</b>
      <p>По запросу «{{ query }}» позиций нет.</p>
      <button type="button" class="cv-btn cv-btn--sm" @click="query = ''">Сбросить поиск</button>
    </div>

    <!-- таблица -->
    <div v-else-if="!cards" class="hp__tablewrap">
      <table class="hp__table">
        <thead>
          <tr>
            <th v-for="c in COLS" :key="c.label" :class="c.cls">
              <button v-if="c.key" type="button" class="hp__th" :class="{ 'is-on': sort.key === c.key }" @click="sortBy(c.key)">
                {{ c.label }}
                <component :is="sort.dir === 'asc' ? ArrowUp : ArrowDown" v-if="sort.key === c.key" :size="12" />
              </button>
              <template v-else>{{ c.label }}</template>
            </th>
            <th class="c-act" />
          </tr>
        </thead>

        <!-- все позиции -->
        <tbody v-if="mode === 'flat'">
          <tr v-for="r in flatRows" :key="r.id" class="hp__row" :class="{ 'is-sold': r.sold }" @click="open(r)">
            <td class="c-name">
              <span class="hp__asset">
                <i :style="{ background: typeColor(r.type) }" />
                <span>
                  <b>{{ r.name }}<em v-if="r.leverage > 1">×{{ r.leverage }}</em></b>
                  <small>{{ r.ticker }}<template v-if="r.ticker"> · </template>{{ r.portfolioName }}</small>
                </span>
              </span>
            </td>
            <td class="r c-price">
              <template v-if="r.deposit">—</template>
              <template v-else>
                <b class="cv-num">{{ fmtPrice(r) }}</b>
                <small class="cv-num">{{ fmtQty(r) }} шт · ср. {{ fmtAvg(r) }}</small>
              </template>
            </td>
            <td class="r">
              <b class="cv-num">{{ money(r.value) }}</b>
              <span class="hp__w"><span :style="{ width: `${(share(r.value) / maxShare) * 100}%` }" /></span>
              <small class="cv-num">{{ pct(share(r.value), { sign: false }) }}</small>
            </td>
            <td class="r">
              <b class="cv-num" :class="tone(r.profit)">{{ money(r.profit, { sign: true }) }}</b>
              <small class="cv-num" :class="tone(r.ret)">{{ pct(r.ret) }}</small>
            </td>
            <td class="r">
              <span v-if="r.deposit" class="hp__dash">—</span>
              <template v-else>
                <b class="cv-num" :class="tone(r.dayPct)">{{ pct(r.dayPct, { digits: 2 }) }}</b>
                <small class="cv-num">{{ money(r.day, { sign: true }) }}</small>
              </template>
            </td>
            <td class="r c-inc">
              <template v-if="r.income">
                <b class="cv-num">{{ pct(r.income, { sign: false, digits: 2 }) }}</b>
                <small>{{ r.incomeKind }}</small>
              </template>
              <span v-else class="hp__dash">—</span>
            </td>
            <td class="c-act">
              <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" aria-label="Действия" @click.stop="openMenu($event, 'asset', r.raw)">
                <MoreHorizontal :size="16" />
              </button>
            </td>
          </tr>
        </tbody>

        <!-- по портфелям -->
        <tbody v-for="s in sections" v-else :key="s.id" class="hp__group" :class="{ 'is-open': s.open }">
          <tr class="hp__ghead" @click="toggle(s.id)">
            <td :colspan="COLS.length + 1">
              <div class="hp__gh" :style="{ '--d': s.depth }">
                <ChevronDown :size="15" class="hp__chev" />
                <b>{{ s.name }}</b>
                <span v-if="s.count" class="hp__gmeta">{{ s.count }} {{ plural(s.count, 'позиция', 'позиции', 'позиций') }}</span>
                <span v-if="s.broker" class="hp__tag">брокер</span>
                <Loader2 v-if="updating.has(s.id)" :size="14" class="hp__spin" />
                <span class="hp__gval">
                  <b class="cv-num">{{ money(s.value) }}</b>
                  <small v-if="s.depth" class="cv-num">{{ pct(share(s.value), { sign: false }) }}</small>
                </span>
                <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" aria-label="Действия с портфелем" @click.stop="openMenu($event, 'portfolio', s.raw)">
                  <MoreHorizontal :size="16" />
                </button>
              </div>
            </td>
          </tr>
          <template v-if="s.open">
            <tr v-for="r in s.rows" :key="r.id" class="hp__row" :class="{ 'is-sold': r.sold }" @click="open(r)">
              <td class="c-name">
                <span class="hp__asset" :style="{ '--d': s.depth }">
                  <i :style="{ background: typeColor(r.type) }" />
                  <span>
                    <b>{{ r.name }}<em v-if="r.leverage > 1">×{{ r.leverage }}</em><em v-if="r.sold">продан</em></b>
                    <small>{{ r.ticker || r.type }}</small>
                  </span>
                </span>
              </td>
              <td class="r c-price">
                <template v-if="r.deposit">—</template>
                <template v-else>
                  <b class="cv-num">{{ fmtPrice(r) }}</b>
                  <small class="cv-num">{{ fmtQty(r) }} шт · ср. {{ fmtAvg(r) }}</small>
                </template>
              </td>
              <td class="r">
                <b class="cv-num">{{ money(r.value) }}</b>
                <span class="hp__w"><span :style="{ width: `${(share(r.value) / maxShare) * 100}%` }" /></span>
                <small class="cv-num">{{ pct(share(r.value), { sign: false }) }}</small>
              </td>
              <td class="r">
                <b class="cv-num" :class="tone(r.profit)">{{ money(r.profit, { sign: true }) }}</b>
                <small class="cv-num" :class="tone(r.ret)">{{ pct(r.ret) }}</small>
              </td>
              <td class="r">
                <span v-if="r.deposit" class="hp__dash">—</span>
                <template v-else>
                  <b class="cv-num" :class="tone(r.dayPct)">{{ pct(r.dayPct, { digits: 2 }) }}</b>
                  <small class="cv-num">{{ money(r.day, { sign: true }) }}</small>
                </template>
              </td>
              <td class="r c-inc">
                <template v-if="r.income">
                  <b class="cv-num">{{ pct(r.income, { sign: false, digits: 2 }) }}</b>
                  <small>{{ r.incomeKind }}</small>
                </template>
                <span v-else class="hp__dash">—</span>
              </td>
              <td class="c-act">
                <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" aria-label="Действия" @click.stop="openMenu($event, 'asset', r.raw)">
                  <MoreHorizontal :size="16" />
                </button>
              </td>
            </tr>
            <tr v-if="s.cash" class="hp__cash">
              <td class="c-name">
                <span class="hp__asset" :style="{ '--d': s.depth }">
                  <i class="is-cash" />
                  <span><b>Свободные деньги</b><small>на счёте</small></span>
                </span>
              </td>
              <td class="c-price" />
              <td class="r">
                <b class="cv-num">{{ money(s.cash) }}</b>
                <small class="cv-num">{{ pct(share(s.cash), { sign: false }) }}</small>
              </td>
              <td :colspan="COLS.length - 2" />
            </tr>
            <tr v-if="!s.rows.length && !s.cash && !query" class="hp__none">
              <td :colspan="COLS.length + 1"><span :style="{ '--d': s.depth }">В этом портфеле нет позиций</span></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- карточки -->
    <div v-else class="hp__cards">
      <template v-if="mode === 'flat'">
        <button v-for="r in flatRows" :key="r.id" type="button" class="hp__card" :class="{ 'is-sold': r.sold }" @click="open(r)">
          <i :style="{ background: typeColor(r.type) }" />
          <span class="hp__cmain">
            <b>{{ r.name }}</b>
            <small>{{ r.ticker }}<template v-if="r.ticker"> · </template>{{ r.portfolioName }}</small>
          </span>
          <span class="hp__camt">
            <b class="cv-num">{{ money(r.value) }}</b>
            <small class="cv-num" :class="tone(r.ret)">{{ pct(r.ret) }}</small>
          </span>
          <span class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" role="button" aria-label="Действия" @click.stop="openMenu($event, 'asset', r.raw)"><MoreHorizontal :size="16" /></span>
        </button>
      </template>
      <template v-else>
        <div v-for="s in sections" :key="s.id" class="hp__cgroup">
          <div class="hp__cghead" :style="{ '--d': s.depth }" @click="toggle(s.id)">
            <ChevronDown :size="15" class="hp__chev" :class="{ 'is-closed': !s.open }" />
            <span class="hp__cgname"><b>{{ s.name }}</b><small v-if="s.count">{{ s.count }} {{ plural(s.count, 'позиция', 'позиции', 'позиций') }}</small></span>
            <Loader2 v-if="updating.has(s.id)" :size="14" class="hp__spin" />
            <b class="cv-num hp__cgval">{{ money(s.value) }}</b>
            <span class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" role="button" aria-label="Действия с портфелем" @click.stop="openMenu($event, 'portfolio', s.raw)"><MoreHorizontal :size="16" /></span>
          </div>
          <template v-if="s.open">
            <button v-for="r in s.rows" :key="r.id" type="button" class="hp__card" :class="{ 'is-sold': r.sold }" @click="open(r)">
              <i :style="{ background: typeColor(r.type) }" />
              <span class="hp__cmain">
                <b>{{ r.name }}</b>
                <small>{{ r.ticker || r.type }}<template v-if="!r.deposit"> · {{ fmtQty(r) }} шт</template></small>
              </span>
              <span class="hp__camt">
                <b class="cv-num">{{ money(r.value) }}</b>
                <small class="cv-num" :class="tone(r.ret)">{{ pct(r.ret) }}</small>
              </span>
              <span class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" role="button" aria-label="Действия" @click.stop="openMenu($event, 'asset', r.raw)"><MoreHorizontal :size="16" /></span>
            </button>
            <div v-if="s.cash" class="hp__card is-cashrow">
              <Wallet :size="14" class="hp__cash-ic" />
              <span class="hp__cmain"><b>Свободные деньги</b></span>
              <span class="hp__camt"><b class="cv-num">{{ money(s.cash) }}</b></span>
              <span />
            </div>
          </template>
        </div>
      </template>
    </div>
  </section>
</template>

<style scoped>
.hp { display: flex; flex-direction: column; min-width: 0; padding: 0; }

/* ── панель инструментов ─────────────────────────────────────────────── */
.hp__bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; padding: 16px 20px; }
.hp__search { position: relative; flex: 1 1 260px; min-width: 200px; }
.hp__search-ic { position: absolute; left: 13px; top: 50%; transform: translateY(-50%); color: var(--cv-dim); pointer-events: none; }
.hp__search:focus-within .hp__search-ic { color: var(--cv-accent-ink); }
.hp__input {
  width: 100%; height: 38px; padding: 0 34px 0 37px; box-sizing: border-box;
  border: 0; border-radius: 10px; outline: none;
  background: rgba(255, 255, 255, .04); box-shadow: inset 0 0 0 1px var(--cv-line);
  color: var(--cv-ink); font-size: 13.5px; transition: box-shadow .2s, background .2s;
}
.hp__input::-webkit-search-cancel-button { display: none; }
.hp__input::placeholder { color: var(--cv-dim); }
.hp__input:hover { box-shadow: inset 0 0 0 1px var(--cv-line-2); }
.hp__input:focus { background: rgba(255, 255, 255, .06); box-shadow: inset 0 0 0 1px var(--cv-accent-line), 0 0 0 3px rgba(100, 116, 255, .12); }
.hp__clear {
  position: absolute; right: 7px; top: 50%; transform: translateY(-50%);
  width: 24px; height: 24px; border: 0; border-radius: 7px; background: transparent;
  color: var(--cv-mut); font-size: 17px; line-height: 1; cursor: pointer;
}
.hp__clear:hover { background: var(--cv-hover); color: var(--cv-ink); }

/* ── таблица ─────────────────────────────────────────────────────────── */
.hp__tablewrap { overflow-x: auto; }
.hp__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.hp__table th {
  padding: 9px 12px; text-align: left; white-space: nowrap;
  font-size: 11px; font-weight: 550; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim);
  border-top: 1px solid var(--cv-line); border-bottom: 1px solid var(--cv-line);
}
.hp__th {
  display: inline-flex; align-items: center; gap: 4px; padding: 0; border: 0; background: none;
  font: inherit; letter-spacing: inherit; text-transform: inherit; color: inherit; cursor: pointer;
}
.hp__th:hover, .hp__th.is-on { color: var(--cv-ink-2); }
.hp__table td { padding: 10px 12px; color: var(--cv-ink-2); border-bottom: 1px solid var(--cv-line); vertical-align: middle; }
.hp__table .r { text-align: right; }
.hp__table th:first-child, .hp__table td:first-child { padding-left: 20px; }
.hp__table th:last-child, .hp__table td:last-child { padding-right: 12px; }
.hp__table td b { display: block; font-weight: 550; color: var(--cv-ink); white-space: nowrap; }
.hp__table td small { display: block; margin-top: 2px; font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; }
.hp__table td b.cv-up, .hp__table td small.cv-up { color: var(--cv-up); }
.hp__table td b.cv-down, .hp__table td small.cv-down { color: var(--cv-down); }
.c-act { width: 30px; }
.hp__dash { color: var(--cv-dim); }

.hp__row { cursor: pointer; transition: background .15s; }
.hp__row:hover { background: var(--cv-hover); }
.hp__row.is-sold td > * { opacity: .5; }

.hp__asset { display: flex; align-items: center; gap: 11px; min-width: 0; padding-left: calc(var(--d, 0) * 18px); }
.hp__asset > i { width: 3px; height: 28px; flex: none; border-radius: 2px; }
.hp__asset > span { min-width: 0; }
.hp__asset b { max-width: 260px; overflow: hidden; text-overflow: ellipsis; }
.hp__asset em { margin-left: 6px; padding: 1px 5px; border-radius: 5px; background: rgba(255, 255, 255, .06); font-size: 10.5px; font-style: normal; font-weight: 600; color: var(--cv-mut); vertical-align: 1px; }
.hp__asset small { max-width: 260px; overflow: hidden; text-overflow: ellipsis; }
.is-cash { background: repeating-linear-gradient(135deg, #5d606c 0 2px, transparent 2px 5px); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .12); }

.hp__w { display: block; width: 64px; height: 2px; margin: 5px 0 0 auto; border-radius: 1px; background: rgba(255, 255, 255, .06); overflow: hidden; }
.hp__w span { display: block; height: 100%; margin-left: auto; border-radius: 1px; background: var(--cv-accent); opacity: .75; }
.hp__w + small { margin-top: 3px !important; }

/* группа-портфель */
.hp__ghead { cursor: pointer; }
.hp__ghead td { padding: 0 !important; background: rgba(255, 255, 255, .018); }
.hp__ghead:hover td { background: var(--cv-hover); }
.hp__group + .hp__group .hp__ghead td { border-top: 1px solid var(--cv-line); }
.hp__gh { display: flex; align-items: center; gap: 10px; min-height: 48px; padding: 0 12px 0 calc(16px + var(--d) * 18px); }
.hp__gh > b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hp__gmeta { font-size: 12px; color: var(--cv-dim); white-space: nowrap; }
.hp__tag { padding: 2px 7px; border-radius: 6px; font-size: 10.5px; font-weight: 600; letter-spacing: .02em; color: var(--cv-accent-ink); background: var(--cv-accent-soft); }
.hp__gval { display: flex; align-items: baseline; gap: 8px; margin-left: auto; white-space: nowrap; }
.hp__gval b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); }
.hp__gval small { font-size: 11.5px; color: var(--cv-dim); }
.hp__chev { flex: none; color: var(--cv-dim); transform: rotate(-90deg); transition: transform .25s var(--cv-ease); }
.hp__group.is-open .hp__chev, .hp__cghead .hp__chev { transform: none; }
.hp__spin { color: var(--cv-accent-ink); animation: hp-spin 1s linear infinite; }

.hp__cash td { color: var(--cv-mut); }
.hp__none td { padding: 14px 20px !important; font-size: 12.5px; color: var(--cv-dim) !important; }
.hp__none span { padding-left: calc(var(--d) * 18px + 14px); }
.hp__group:last-child tr:last-child td { border-bottom: 0; }

@media (max-width: 1280px) {
  .hp__table .c-inc { display: none; }
  .hp__table th, .hp__table td { padding-left: 9px; padding-right: 9px; }
  .hp__asset b, .hp__asset small { max-width: 190px; }
}

/* ── карточки ────────────────────────────────────────────────────────── */
.hp__cards { display: flex; flex-direction: column; border-top: 1px solid var(--cv-line); }
.hp__cgroup + .hp__cgroup { border-top: 1px solid var(--cv-line); }
.hp__cghead {
  display: grid; grid-template-columns: 15px minmax(0, 1fr) auto auto 30px; align-items: center; gap: 10px;
  padding: 11px 8px 11px calc(14px + var(--d) * 14px); background: rgba(255, 255, 255, .018); cursor: pointer;
}
.hp__cghead:has(.hp__spin) { grid-template-columns: 15px minmax(0, 1fr) auto auto auto 30px; }
.hp__cgname { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.hp__cgname b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hp__cgname small { font-size: 11.5px; color: var(--cv-dim); }
.hp__cgval { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); white-space: nowrap; }
.hp__cghead .hp__chev.is-closed { transform: rotate(-90deg); }

.hp__card {
  display: grid; grid-template-columns: 3px minmax(0, 1fr) auto 30px; align-items: center; gap: 12px;
  width: 100%; padding: 10px 8px 10px 16px; border: 0; border-top: 1px solid var(--cv-line);
  background: transparent; text-align: left; font: inherit; color: inherit; cursor: pointer;
}
.hp__card:hover { background: var(--cv-hover); }
.hp__card > i { width: 3px; height: 28px; border-radius: 2px; }
.hp__card.is-sold > * { opacity: .5; }
.hp__card.is-cashrow { cursor: default; grid-template-columns: 14px minmax(0, 1fr) auto 30px; padding-left: 12px; }
.hp__card.is-cashrow:hover { background: transparent; }
.hp__cash-ic { color: var(--cv-dim); }
.hp__cmain { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.hp__cmain b { font-size: 13.5px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hp__cmain small { font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hp__camt { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; white-space: nowrap; }
.hp__camt b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); }
.hp__camt small { font-size: 11.5px; font-weight: 550; color: var(--cv-dim); }
.hp__camt small.cv-up { color: var(--cv-up); }
.hp__camt small.cv-down { color: var(--cv-down); }

.hp__empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 48px 16px 56px; text-align: center; border-top: 1px solid var(--cv-line); }
.hp__empty b { color: var(--cv-ink); font-size: 14.5px; font-weight: 550; }
.hp__empty p { margin: 0; font-size: 13px; color: var(--cv-mut); }
.hp__empty .cv-btn { margin-top: 6px; }

@keyframes hp-spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .hp__bar { padding: 14px; gap: 10px; }
  .hp__search { flex-basis: 100%; min-width: 0; }
}
</style>
