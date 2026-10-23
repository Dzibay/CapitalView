<script setup>
/**
 * Площадной график стоимости портфеля.
 * — смена периода = плавный «зум»: GSAP твинит домены осей, путь пересчитывается каждый кадр;
 * — перекрестие с тултипом (слот #tooltip), точки на всех сериях;
 * — перетаскивание выделяет диапазон (v-model:selection), кнопка «Приблизить» зумирует в него;
 * — стрелки ←/→ двигают курсор с клавиатуры, Esc сбрасывает.
 */
import { computed, onBeforeUnmount, onMounted, reactive, ref, useId, watch } from 'vue'
import { scaleLinear, scaleTime } from 'd3-scale'
import { area, line, curveMonotoneX } from 'd3-shape'
import { bisectLeft, bisectRight } from 'd3-array'
import gsap from 'gsap'
import { ZoomIn } from 'lucide-vue-next'
import { useElementSize, prefersReducedMotion } from './useElementSize'
import { axisMoney, dateShort, monthShort } from '../format'

const props = defineProps({
  /** метки времени в мс, по возрастанию */
  dates: { type: Array, required: true },
  /** [{ key, label, values, color, kind: 'area' | 'line' | 'dash' | 'dot' }] — первая серия основная */
  series: { type: Array, required: true },
  /** видимый диапазон [t0, t1] в мс */
  range: { type: Array, required: true },
  height: { type: Number, default: 300 },
  /** выделенный диапазон индексов { i0, i1 } */
  selection: { type: Object, default: null },
  ariaLabel: { type: String, default: 'График' },
})
const emit = defineEmits(['hover', 'update:selection', 'zoom'])

const DAY = 86400000
const PAD = { top: 14, right: 58, bottom: 28, left: 2 }

const uid = useId()
const root = ref(null)
const svgEl = ref(null)
const { width } = useElementSize(root)

const plotW = computed(() => Math.max(0, width.value - PAD.left - PAD.right))
const plotH = computed(() => Math.max(0, props.height - PAD.top - PAD.bottom))

// ── домены (анимируются) ────────────────────────────────────────────────────
const view = reactive({ x0: 0, x1: 1, y0: 0, y1: 1 })
const reveal = ref(prefersReducedMotion() ? 1 : 0)
let tween = null
let introTween = null
let mounted = false

function indexWindow(t0, t1) {
  const d = props.dates
  const i0 = Math.min(d.length - 1, bisectLeft(d, t0))
  const i1 = Math.max(i0, bisectRight(d, t1) - 1)
  return [i0, i1]
}

function domainFor(t0, t1) {
  const [i0, i1] = indexWindow(t0, t1)
  let lo = Infinity
  let hi = -Infinity
  for (const s of props.series) {
    for (let i = i0; i <= i1; i++) {
      const v = s.values[i]
      if (v == null || !Number.isFinite(v)) continue
      if (v < lo) lo = v
      if (v > hi) hi = v
    }
  }
  if (!Number.isFinite(lo)) return [0, 1]
  const span = hi - lo || Math.abs(hi) * 0.1 || 1
  return [lo - span * 0.1, hi + span * 0.16]
}

function sync(animate) {
  if (!props.dates.length) return
  const [t0, t1] = props.range
  const [y0, y1] = domainFor(t0, t1)
  tween?.kill()
  if (!animate || prefersReducedMotion()) {
    Object.assign(view, { x0: t0, x1: t1, y0, y1 })
    return
  }
  tween = gsap.to(view, { x0: t0, x1: t1, y0, y1, duration: 0.9, ease: 'expo.out' })
}

watch(() => [props.range[0], props.range[1], props.dates, props.series], () => sync(mounted))

onMounted(() => {
  sync(false)
  mounted = true
  if (reveal.value < 1) {
    introTween = gsap.to(reveal, { value: 1, duration: 1.5, ease: 'power3.inOut', delay: 0.1 })
  }
})
onBeforeUnmount(() => {
  tween?.kill()
  introTween?.kill()
})

// ── шкалы и пути ───────────────────────────────────────────────────────────
const xs = computed(() => scaleTime().domain([view.x0, view.x1]).range([0, plotW.value]))
const ys = computed(() => scaleLinear().domain([view.y0, view.y1]).range([plotH.value, 0]))

const drawWindow = computed(() => {
  const d = props.dates
  if (!d.length) return [0, -1]
  return [Math.max(0, bisectLeft(d, view.x0) - 1), Math.min(d.length - 1, bisectRight(d, view.x1))]
})

const paths = computed(() => {
  const x = xs.value
  const y = ys.value
  const d = props.dates
  const [i0, i1] = drawWindow.value
  const idx = []
  for (let i = i0; i <= i1; i++) idx.push(i)
  return props.series.map((s) => {
    const ok = (i) => s.values[i] != null && Number.isFinite(s.values[i])
    const res = {
      key: s.key,
      color: s.color,
      kind: s.kind,
      line: line().defined(ok).x((i) => x(d[i])).y((i) => y(s.values[i])).curve(curveMonotoneX)(idx) || '',
    }
    if (s.kind === 'area') {
      res.area = area().defined(ok).x((i) => x(d[i])).y0(plotH.value).y1((i) => y(s.values[i])).curve(curveMonotoneX)(idx) || ''
    }
    return res
  })
})
const primary = computed(() => paths.value[0] || null)
const secondary = computed(() => paths.value.slice(1))
const areas = computed(() => paths.value.filter((p) => p.area))

const yTicks = computed(() => {
  const y = ys.value
  return y.ticks(4)
    .map((v) => ({ v, y: y(v), label: axisMoney(v) }))
    .filter((t) => t.y >= 4 && t.y <= plotH.value - 2)
})

const xTicks = computed(() => {
  const span = view.x1 - view.x0
  const n = Math.max(3, Math.floor(plotW.value / 120))
  const fmt = span > 75 * DAY ? monthShort : dateShort
  return xs.value.ticks(n)
    .map((t) => ({ t: +t, x: xs.value(t), label: fmt(t) }))
    .filter((t) => t.x >= 18 && t.x <= plotW.value - 18)
})

/** «живая» точка на последнем значении */
const live = computed(() => {
  const s = props.series[0]
  const i = props.dates.length - 1
  if (!s || i < 0 || s.values[i] == null) return null
  const x = xs.value(props.dates[i])
  if (x < 0 || x > plotW.value + 1) return null
  return { x, y: ys.value(s.values[i]), color: s.color }
})

// ── наведение и выделение ─────────────────────────────────────────────────
const hover = ref(null)
const dragging = ref(false)
let drag = null

function nearest(px) {
  const d = props.dates
  const t = +xs.value.invert(px)
  let i = bisectLeft(d, t)
  if (i >= d.length) i = d.length - 1
  else if (i > 0 && t - d[i - 1] < d[i] - t) i -= 1
  const [a, b] = indexWindow(view.x0, view.x1)
  return Math.min(b, Math.max(a, i))
}
function localX(e) {
  const r = svgEl.value.getBoundingClientRect()
  return Math.min(plotW.value, Math.max(0, e.clientX - r.left - PAD.left))
}
function setHover(i) {
  if (hover.value === i) return
  hover.value = i
  emit('hover', i)
}

function onDown(e) {
  if (e.button !== 0 || !props.dates.length) return
  const x = localX(e)
  const i = nearest(x)
  if (e.pointerType !== 'touch') {
    drag = { i, x, moved: false }
    e.currentTarget.setPointerCapture?.(e.pointerId)
  }
  setHover(i)
}
function onMove(e) {
  if (!props.dates.length) return
  const x = localX(e)
  const i = nearest(x)
  setHover(i)
  if (!drag) return
  if (!drag.moved && Math.abs(x - drag.x) > 5) {
    drag.moved = true
    dragging.value = true
  }
  if (drag.moved && i !== drag.i) {
    emit('update:selection', { i0: Math.min(drag.i, i), i1: Math.max(drag.i, i) })
  }
}
function onUp() {
  if (drag && !drag.moved && props.selection) emit('update:selection', null)
  drag = null
  dragging.value = false
}
function onLeave() {
  if (!drag) setHover(null)
}
function onKey(e) {
  if (!props.dates.length) return
  const [a, b] = indexWindow(view.x0, view.x1)
  if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
    e.preventDefault()
    const step = e.shiftKey ? 10 : 1
    const cur = hover.value ?? b
    setHover(Math.min(b, Math.max(a, cur + (e.key === 'ArrowLeft' ? -step : step))))
  } else if (e.key === 'Escape') {
    setHover(null)
    emit('update:selection', null)
  }
}

const marks = computed(() => {
  const i = hover.value
  if (i == null || i >= props.dates.length) return null
  const x = xs.value(props.dates[i])
  return {
    i,
    x,
    dots: props.series
      .filter((s) => s.values[i] != null && Number.isFinite(s.values[i]))
      .map((s) => ({ key: s.key, color: s.color, y: ys.value(s.values[i]) })),
  }
})

const tipStyle = computed(() => {
  const m = marks.value
  if (!m) return null
  const flip = m.x > plotW.value * 0.6
  return {
    left: `${PAD.left + m.x}px`,
    top: `${PAD.top + 2}px`,
    transform: flip ? 'translateX(calc(-100% - 14px))' : 'translateX(14px)',
  }
})

const band = computed(() => {
  const s = props.selection
  if (!s || !props.dates[s.i0] || !props.dates[s.i1]) return null
  const a = Math.max(0, xs.value(props.dates[s.i0]))
  const b = Math.min(plotW.value, xs.value(props.dates[s.i1]))
  if (b <= a) return null
  return { x: a, w: b - a, cx: (a + b) / 2 }
})

function zoomToSelection() {
  const s = props.selection
  if (!s) return
  emit('zoom', [props.dates[s.i0], props.dates[s.i1]])
  emit('update:selection', null)
}
</script>

<template>
  <div
    ref="root"
    class="cvc"
    :class="{ 'is-dragging': dragging, 'is-hovering': marks }"
    :style="{ height: `${height}px` }"
    tabindex="0"
    role="figure"
    :aria-label="ariaLabel"
    @keydown="onKey"
    @blur="setHover(null)"
  >
    <svg v-if="width" ref="svgEl" :width="width" :height="height" class="cvc__svg">
      <defs>
        <linearGradient v-for="p in areas" :id="`${uid}-g-${p.key}`" :key="p.key" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" :stop-color="p.color" stop-opacity=".2" />
          <stop offset="65%" :stop-color="p.color" stop-opacity=".045" />
          <stop offset="100%" :stop-color="p.color" stop-opacity="0" />
        </linearGradient>
        <clipPath :id="`${uid}-clip`">
          <rect x="-4" y="-12" :width="plotW * reveal + 8" :height="plotH + 24" />
        </clipPath>
      </defs>

      <g :transform="`translate(${PAD.left},${PAD.top})`">
        <g class="cvc__grid" aria-hidden="true">
          <line v-for="t in yTicks" :key="t.v" x1="0" :x2="plotW" :y1="t.y" :y2="t.y" />
          <line class="is-base" x1="0" :x2="plotW" :y1="plotH" :y2="plotH" />
        </g>
        <g class="cvc__ylab" aria-hidden="true">
          <text v-for="t in yTicks" :key="t.v" :x="plotW + 12" :y="t.y" dy="0.32em">{{ t.label }}</text>
        </g>
        <g class="cvc__xlab" aria-hidden="true">
          <text v-for="t in xTicks" :key="t.t" :x="t.x" :y="plotH + 20" text-anchor="middle">{{ t.label }}</text>
        </g>

        <g :clip-path="`url(#${uid}-clip)`">
          <path v-for="p in areas" :key="`a-${p.key}`" :d="p.area" :fill="`url(#${uid}-g-${p.key})`" class="cvc__area" />
          <path
            v-for="p in secondary"
            :key="`l-${p.key}`"
            :d="p.line"
            class="cvc__line"
            :class="`is-${p.kind}`"
            :stroke="p.color"
          />
          <path v-if="primary" :d="primary.line" class="cvc__line is-primary" :stroke="primary.color" />
        </g>

        <g v-if="band" class="cvc__band" aria-hidden="true">
          <rect x="0" y="0" :width="band.x" :height="plotH" class="cvc__dim" />
          <rect :x="band.x + band.w" y="0" :width="Math.max(0, plotW - band.x - band.w)" :height="plotH" class="cvc__dim" />
          <line :x1="band.x" :x2="band.x" y1="0" :y2="plotH" class="cvc__edge" />
          <line :x1="band.x + band.w" :x2="band.x + band.w" y1="0" :y2="plotH" class="cvc__edge" />
        </g>

        <g v-if="live && reveal > 0.98 && !marks" :transform="`translate(${live.x},${live.y})`" class="cvc__live" aria-hidden="true">
          <circle r="9" :fill="live.color" class="cvc__pulse" />
          <circle r="4" :fill="live.color" class="cvc__dot" />
        </g>

        <g v-if="marks" class="cvc__cross" aria-hidden="true">
          <line :x1="marks.x" :x2="marks.x" y1="0" :y2="plotH" />
          <circle v-for="d in marks.dots" :key="d.key" :cx="marks.x" :cy="d.y" r="4.5" :fill="d.color" class="cvc__hdot" />
        </g>

        <rect
          class="cvc__hit"
          x="0"
          y="0"
          :width="plotW"
          :height="plotH + PAD.bottom"
          @pointerdown="onDown"
          @pointermove="onMove"
          @pointerup="onUp"
          @pointercancel="onUp"
          @pointerleave="onLeave"
        />
      </g>
    </svg>

    <div v-if="marks && $slots.tooltip" class="cv-tip cvc__tip" :style="tipStyle">
      <slot name="tooltip" :index="marks.i" />
    </div>

    <Transition name="cvc-fade">
      <button
        v-if="band && !dragging && band.w > 28"
        type="button"
        class="cvc__zoom"
        :style="{ left: `${PAD.left + band.cx}px`, top: `${PAD.top + plotH - 42}px` }"
        @click="zoomToSelection"
      >
        <ZoomIn :size="14" :stroke-width="2.2" /> Приблизить
      </button>
    </Transition>
  </div>
</template>

<style scoped>
.cvc {
  position: relative;
  width: 100%;
  outline: none;
  user-select: none;
  -webkit-user-select: none;
}
.cvc:focus-visible { outline: 2px solid rgba(130, 143, 255, .55); outline-offset: 4px; border-radius: 12px; }
.cvc__svg { display: block; overflow: visible; }

.cvc__grid line { stroke: rgba(255, 255, 255, .04); }
.cvc__grid line.is-base { stroke: rgba(255, 255, 255, .08); }
.cvc__ylab text, .cvc__xlab text {
  font-size: 11px; fill: var(--cv-dim); font-variant-numeric: tabular-nums;
}

.cvc__line { fill: none; stroke-width: 1.75; stroke-linecap: round; stroke-linejoin: round; }
.cvc__line.is-primary { filter: drop-shadow(0 4px 10px rgba(115, 129, 255, .28)); }
.cvc__line.is-dash { stroke-dasharray: 4 5; stroke-width: 1.4; stroke-linecap: butt; opacity: .85; }
.cvc__line.is-dot { stroke-dasharray: 0 5; stroke-width: 2; opacity: .9; }
.cvc__line.is-line { stroke-width: 1.6; opacity: .9; }

.cvc__dim { fill: rgba(8, 9, 11, .62); }
.cvc__edge { stroke: rgba(180, 188, 255, .45); stroke-width: 1; }

.cvc__cross line { stroke: rgba(255, 255, 255, .2); stroke-width: 1; }
.cvc__hdot { stroke: var(--cv-surface-2); stroke-width: 2; }

.cvc__dot { stroke: var(--cv-surface-2); stroke-width: 2; }
.cvc__pulse {
  opacity: .5;
  transform-box: fill-box; transform-origin: center;
  animation: cvc-pulse 2.2s var(--cv-ease) infinite;
}
@keyframes cvc-pulse {
  0% { transform: scale(.45); opacity: .55; }
  80%, 100% { transform: scale(1.9); opacity: 0; }
}

.cvc__hit { fill: transparent; cursor: crosshair; touch-action: pan-y; }
.cvc.is-dragging .cvc__hit { cursor: ew-resize; }

.cvc__tip { min-width: 196px; transition: left .08s linear; }

.cvc__zoom {
  position: absolute; z-index: 21; transform: translateX(-50%);
  display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 12px;
  border: 0; border-radius: 99px; cursor: pointer;
  font-size: 12.5px; font-weight: 600; color: #fff;
  background: linear-gradient(180deg, #7080ff, #5866ee);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .2), 0 8px 22px -10px rgba(100, 116, 255, .9);
}
.cvc__zoom:hover { filter: brightness(1.08); }
.cvc-fade-enter-active, .cvc-fade-leave-active { transition: opacity .2s var(--cv-ease); }
.cvc-fade-enter-from, .cvc-fade-leave-to { opacity: 0; }
</style>
