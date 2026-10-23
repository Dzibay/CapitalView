<script setup>
/**
 * Структура портфеля — treemap (d3-hierarchy).
 * «Типы»: плитка на тип актива, клик — провал внутрь типа. «Активы»: все позиции, сгруппированные по типу.
 * Цвет закреплён за типом актива; подписи — токенами текста, не цветом серии.
 */
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { hierarchy, treemap, treemapSquarify } from 'd3-hierarchy'
import { PieChart, ChevronLeft } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import CvSegmented from '../ui/CvSegmented.vue'
import { useElementSize } from '../charts/useElementSize'
import { effectiveUnitPriceInCurrency } from '../../utils/effectiveAssetPrice'
import { typeColor, typeGroup } from '../palette'
import { money, moneyCompact, pct, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  assets: { type: Array, default: () => [] },
})
const router = useRouter()

const mode = ref('types')
const drill = ref(null)
const MODES = [
  { value: 'types', label: 'Типы' },
  { value: 'assets', label: 'Активы' },
]
watch(mode, () => { drill.value = null })

function assetValue(a) {
  const lev = Number(a.leverage || 1) || 1
  return (Number(a.quantity || 0) * effectiveUnitPriceInCurrency(a) * Number(a.currency_rate_to_rub || 1)) / lev
}

/** позиции одной бумаги из разных подпортфелей складываем */
const items = computed(() => {
  const map = new Map()
  for (const a of props.assets) {
    const v = assetValue(a)
    if (!(v > 0)) continue
    const key = a.asset_id ?? a.ticker ?? a.name
    const profit = Number(a.profit_rub ?? a.profit ?? 0) || 0
    const cur = map.get(key)
    if (cur) {
      cur.value += v
      cur.profit += profit
    } else {
      map.set(key, {
        id: `a:${key}`,
        assetId: a.asset_id,
        label: a.ticker || a.name,
        name: a.name,
        type: typeGroup(a.type),
        value: v,
        profit,
      })
    }
  }
  return [...map.values()]
})

const total = computed(() => items.value.reduce((s, i) => s + i.value, 0))

const groups = computed(() => {
  const map = new Map()
  for (const it of items.value) {
    if (!map.has(it.type)) map.set(it.type, { id: `t:${it.type}`, type: it.type, label: it.type, value: 0, profit: 0, children: [] })
    const g = map.get(it.type)
    g.value += it.value
    g.profit += it.profit
    g.children.push(it)
  }
  const list = [...map.values()].sort((a, b) => b.value - a.value)
  for (const g of list) g.children.sort((a, b) => b.value - a.value)
  return list
})

watch(groups, (list) => {
  if (drill.value && !list.some((g) => g.type === drill.value)) drill.value = null
})

const box = ref(null)
const { width: boxW, height: boxH } = useElementSize(box)

const viewKey = computed(() => (mode.value === 'assets' ? 'assets' : drill.value ? `drill:${drill.value}` : 'types'))

const nodes = computed(() => {
  const w = boxW.value
  const h = boxH.value
  if (!w || !h || !groups.value.length) return []

  let data
  if (mode.value === 'assets') data = { children: groups.value }
  else if (drill.value) data = { children: groups.value.find((g) => g.type === drill.value)?.children || [] }
  else data = { children: groups.value.map((g) => ({ ...g, children: undefined })) }

  const root = hierarchy(data, (d) => d.children).sum((d) => (d.children ? 0 : d.value))
  treemap().size([w, h]).tile(treemapSquarify.ratio(1.4)).paddingInner(2).round(true)(root)

  const scopeTotal = root.value || 1
  return root.leaves().map((n, i) => {
    const d = n.data
    const nw = n.x1 - n.x0
    const nh = n.y1 - n.y0
    return {
      ...d,
      i,
      x: n.x0,
      y: n.y0,
      w: nw,
      h: nh,
      color: typeColor(d.type),
      share: (d.value / (total.value || 1)) * 100,
      localShare: (d.value / scopeTotal) * 100,
      isGroup: !!d.children || (mode.value === 'types' && !drill.value),
      showLabel: nw > 56 && nh > 38,
      showShare: nh > 56,
      showMeta: nw > 92 && nh > 76,
    }
  })
})

// ── взаимодействие ─────────────────────────────────────────────────────────
const hover = ref(null)
const tip = ref({ x: 0, y: 0 })

function onMove(e, n) {
  const r = box.value.getBoundingClientRect()
  hover.value = n.id
  tip.value = { x: e.clientX - r.left, y: e.clientY - r.top }
}
const hovered = computed(() => nodes.value.find((n) => n.id === hover.value) || null)
const tipStyle = computed(() => {
  const flipX = tip.value.x > boxW.value * 0.6
  const flipY = tip.value.y > boxH.value * 0.55
  return {
    left: `${tip.value.x}px`,
    top: `${tip.value.y}px`,
    transform: `translate(${flipX ? 'calc(-100% - 14px)' : '14px'}, ${flipY ? 'calc(-100% - 14px)' : '14px'})`,
  }
})

function open(n) {
  if (mode.value === 'types' && !drill.value) {
    drill.value = n.type
    hover.value = null
  } else if (n.assetId != null) {
    router.push(`/assets/${n.assetId}`)
  }
}

const legendHover = ref(null)
function legendClick(g) {
  mode.value = 'types'
  drill.value = drill.value === g.type ? null : g.type
}

const subtitle = computed(() => {
  const n = items.value.length
  const t = groups.value.length
  return `${n} ${plural(n, 'позиция', 'позиции', 'позиций')} · ${t} ${plural(t, 'тип', 'типа', 'типов')}`
})
</script>

<template>
  <CvWidget v-bind="$attrs" title="Структура портфеля" :subtitle="subtitle" :icon="PieChart">
    <template #actions>
      <CvSegmented v-model="mode" :options="MODES" size="sm" aria-label="Группировка" />
    </template>

    <div class="al">
      <Transition name="al-crumb">
        <div v-if="drill" class="al__crumb">
          <button type="button" class="cv-btn cv-btn--sm cv-btn--ghost" @click="drill = null">
            <ChevronLeft :size="15" /> Все типы
          </button>
          <span class="al__crumb-sep">/</span>
          <i class="al__dot" :style="{ background: typeColor(drill) }" />
          <b>{{ drill }}</b>
          <span class="al__crumb-share cv-num">{{ pct(groups.find((g) => g.type === drill)?.value / (total || 1) * 100, { sign: false }) }}</span>
        </div>
      </Transition>

      <div
        ref="box"
        class="al__map"
        :class="{ 'has-hover': hover || legendHover }"
        @pointerleave="hover = null"
      >
        <Transition name="al-zoom">
          <div :key="viewKey" class="al__layer">
            <button
              v-for="n in nodes"
              :key="n.id"
              type="button"
              class="al__tile"
              :class="{
                'is-hover': hover === n.id || legendHover === n.type,
                'is-group': n.isGroup,
              }"
              :style="{
                transform: `translate(${n.x}px, ${n.y}px)`,
                width: `${n.w}px`,
                height: `${n.h}px`,
                '--c': n.color,
                '--i': n.i,
              }"
              :aria-label="`${n.name || n.label}: ${money(n.value)}, ${pct(n.share, { sign: false })}`"
              @pointermove="onMove($event, n)"
              @focus="hover = n.id"
              @blur="hover = null"
              @click="open(n)"
            >
              <template v-if="n.showLabel">
                <span class="al__name">{{ n.label }}</span>
                <span v-if="n.showShare" class="al__share cv-num">{{ pct(drill ? n.localShare : n.share, { sign: false }) }}</span>
                <span v-if="n.showMeta" class="al__val cv-num">{{ moneyCompact(n.value) }}</span>
              </template>
            </button>
          </div>
        </Transition>

        <div v-if="hovered" class="cv-tip al__tip" :style="tipStyle">
          <div class="cv-tip__date">{{ hovered.isGroup ? 'Тип актива' : hovered.type }}</div>
          <div class="al__tip-name">
            <i class="cv-tip__sw" :style="{ background: hovered.color }" />{{ hovered.name || hovered.label }}
          </div>
          <div class="cv-tip__row"><span>Стоимость</span><b>{{ money(hovered.value) }}</b></div>
          <div class="cv-tip__row"><span>Доля в портфеле</span><b>{{ pct(hovered.share, { sign: false }) }}</b></div>
          <div v-if="hovered.profit" class="cv-tip__row">
            <span>Прибыль</span>
            <b :class="hovered.profit > 0 ? 'cv-up' : 'cv-down'">{{ money(hovered.profit, { sign: true }) }}</b>
          </div>
          <div v-if="hovered.isGroup" class="al__tip-hint">Нажмите, чтобы раскрыть</div>
        </div>

        <div v-if="!items.length" class="al__empty">Добавьте активы, чтобы увидеть структуру портфеля</div>
      </div>

      <ul class="al__legend cv-legend" aria-label="Типы активов">
        <li v-for="g in groups" :key="g.type">
          <button
            type="button"
            class="al__leg"
            :class="{ 'is-on': drill === g.type }"
            @pointerenter="legendHover = g.type"
            @pointerleave="legendHover = null"
            @click="legendClick(g)"
          >
            <i class="cv-legend__sw" :style="{ background: typeColor(g.type) }" />
            <span>{{ g.type }}</span>
            <b class="cv-num">{{ pct(g.value / (total || 1) * 100, { sign: false }) }}</b>
          </button>
        </li>
      </ul>
    </div>
  </CvWidget>
</template>

<style scoped>
.al { display: flex; flex-direction: column; gap: 12px; height: 100%; min-height: 0; }

.al__crumb { display: flex; align-items: center; gap: 8px; margin: -6px 0 -2px -8px; font-size: 13px; color: var(--cv-mut); }
.al__crumb b { color: var(--cv-ink); font-weight: 600; }
.al__crumb-sep { color: var(--cv-dim); }
.al__crumb-share { color: var(--cv-mut); }
.al__dot { width: 8px; height: 8px; border-radius: 3px; }

.al__map { position: relative; flex: 1; min-height: 260px; }
.al__layer { position: absolute; inset: 0; }

.al__tile {
  position: absolute; left: 0; top: 0;
  display: flex; flex-direction: column; align-items: flex-start; justify-content: flex-start; gap: 2px;
  padding: 10px 11px; border: 0; border-radius: 8px; overflow: hidden; cursor: pointer; text-align: left;
  color: var(--cv-ink);
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--c) 30%, var(--cv-surface-2)), color-mix(in srgb, var(--c) 19%, var(--cv-surface-2)));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 26%, transparent), inset 0 1px 0 rgba(255, 255, 255, .05);
  transition:
    transform .6s var(--cv-ease), width .6s var(--cv-ease), height .6s var(--cv-ease),
    opacity .25s, box-shadow .25s, filter .25s;
  animation: al-in .55s var(--cv-ease) backwards;
  animation-delay: calc(min(var(--i), 18) * 28ms);
}
@keyframes al-in {
  from { opacity: 0; filter: blur(6px); }
  to { opacity: 1; filter: none; }
}
.al__tile:hover, .al__tile.is-hover {
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--c) 60%, transparent), inset 0 1px 0 rgba(255, 255, 255, .08);
  filter: brightness(1.1);
}
.al__map.has-hover .al__tile:not(.is-hover) { opacity: .5; }

.al__tile > * { flex: none; }
.al__name { max-width: 100%; font-size: 13px; font-weight: 550; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.al__share { font-size: 12px; color: var(--cv-ink-2); }
.al__val { margin-top: auto; font-size: 12px; color: var(--cv-mut); }

.al__tip { min-width: 210px; }
.al__tip-name { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 13px; font-weight: 600; color: var(--cv-ink); }
.al__tip-hint { margin-top: 6px; font-size: 11.5px; color: var(--cv-accent-ink); }

.al__empty { position: absolute; inset: 0; display: grid; place-items: center; color: var(--cv-mut); font-size: 13px; text-align: center; }

.al__legend { list-style: none; margin: 0; padding: 0; gap: 4px 6px; }
.al__leg {
  display: inline-flex; align-items: center; gap: 7px; height: 26px; padding: 0 9px 0 7px;
  border: 0; border-radius: 8px; background: transparent; cursor: pointer;
  font-size: 12px; color: var(--cv-mut);
  transition: background .2s, color .2s;
}
.al__leg:hover, .al__leg.is-on { background: var(--cv-hover); color: var(--cv-ink); }
.al__leg b { font-weight: 550; color: var(--cv-ink-2); }

.al-zoom-enter-active { transition: opacity .45s var(--cv-ease), transform .55s var(--cv-ease); }
.al-zoom-leave-active { transition: opacity .3s var(--cv-ease), transform .45s var(--cv-ease); }
.al-zoom-enter-from { opacity: 0; transform: scale(.96); }
.al-zoom-leave-to { opacity: 0; transform: scale(1.04); }

.al-crumb-enter-active, .al-crumb-leave-active { transition: opacity .2s, transform .25s var(--cv-ease); }
.al-crumb-enter-from, .al-crumb-leave-to { opacity: 0; transform: translateX(-6px); }
</style>
