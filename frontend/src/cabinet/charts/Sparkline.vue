<script setup>
/**
 * Компактный график-тренд: линия с градиентной заливкой, опорная пунктирная линия,
 * режим «выше/ниже нуля» и подсказка при наведении. Растягивается на всю высоту контейнера.
 */
import { computed, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import gsap from 'gsap'
import { scaleLinear } from 'd3-scale'
import { area as d3area, line as d3line, curveMonotoneX } from 'd3-shape'
import { useElementSize, prefersReducedMotion } from './useElementSize'

const props = defineProps({
  values: { type: Array, required: true },
  labels: { type: Array, default: () => [] },
  /** пунктирная опорная линия той же длины (цель, вложено и т. п.) */
  reference: { type: Array, default: null },
  format: { type: Function, default: (v) => String(v) },
  labelFormat: { type: Function, default: (l) => String(l ?? '') },
  referenceLabel: { type: String, default: '' },
  color: { type: String, default: '#7381ff' },
  /** заливка зелёным выше нуля и красным ниже */
  diverging: { type: Boolean, default: false },
  markIndex: { type: Number, default: -1 },
  minHeight: { type: Number, default: 64 },
  ariaLabel: { type: String, default: '' },
})

const uid = useId()
const box = ref(null)
const { width, height } = useElementSize(box)
const PAD = { t: 6, b: 4, x: 2 }

const n = computed(() => props.values.length)
const ok = computed(() => n.value > 1 && width.value > 0 && height.value > 0)

const x = computed(() => scaleLinear().domain([0, Math.max(1, n.value - 1)]).range([PAD.x, width.value - PAD.x]))
const y = computed(() => {
  const all = props.values.concat(props.reference || []).filter(Number.isFinite)
  let lo = Math.min(...all)
  let hi = Math.max(...all)
  if (props.diverging) { lo = Math.min(lo, 0); hi = Math.max(hi, 0) }
  if (lo === hi) { lo -= 1; hi += 1 }
  const pad = (hi - lo) * 0.1
  return scaleLinear().domain([lo - (props.diverging ? pad : pad * 0.4), hi + pad]).range([height.value - PAD.b, PAD.t])
})

const zeroY = computed(() => (props.diverging ? y.value(0) : height.value))
const linePath = computed(() => (ok.value ? d3line().x((_, i) => x.value(i)).y((v) => y.value(v)).curve(curveMonotoneX)(props.values) : ''))
const areaPath = computed(() =>
  ok.value ? d3area().x((_, i) => x.value(i)).y0(zeroY.value).y1((v) => y.value(v)).curve(curveMonotoneX)(props.values) : '',
)
const refPath = computed(() =>
  ok.value && props.reference?.length === n.value ? d3line().x((_, i) => x.value(i)).y((v) => y.value(v))(props.reference) : '',
)
const mark = computed(() =>
  ok.value && props.markIndex >= 0 && props.markIndex < n.value
    ? { x: x.value(props.markIndex), y: y.value(props.values[props.markIndex]) }
    : null,
)

// появление слева направо
const reveal = ref(prefersReducedMotion() ? 1 : 0)
let tween
onMounted(() => {
  if (reveal.value < 1) tween = gsap.to(reveal, { value: 1, duration: 1.3, ease: 'power3.inOut', delay: 0.25 })
})
onBeforeUnmount(() => tween?.kill())

// наведение
const hover = ref(-1)
function onMove(e) {
  if (!ok.value) return
  const r = box.value.getBoundingClientRect()
  const i = Math.round(x.value.invert(e.clientX - r.left))
  hover.value = Math.max(0, Math.min(n.value - 1, i))
}
const tip = computed(() => {
  const i = hover.value
  if (i < 0 || !ok.value) return null
  const px = x.value(i)
  return {
    x: px,
    y: y.value(props.values[i]),
    flip: px > width.value * 0.6,
    label: props.labelFormat(props.labels[i]),
    value: props.format(props.values[i]),
    ref: props.reference ? props.format(props.reference[i]) : null,
  }
})
</script>

<template>
  <div
    ref="box"
    class="spk"
    :style="{ minHeight: `${minHeight}px` }"
    role="img"
    :aria-label="ariaLabel"
    @pointermove="onMove"
    @pointerleave="hover = -1"
  >
    <svg v-if="ok" :width="width" :height="height" class="spk__svg" aria-hidden="true">
      <defs>
        <linearGradient :id="`${uid}-fill`" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" :stop-color="color" stop-opacity=".2" />
          <stop offset="100%" :stop-color="color" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="`${uid}-up`" x1="0" y1="0" x2="0" :y2="zeroY" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#5bd18b" stop-opacity=".2" />
          <stop offset="100%" stop-color="#5bd18b" stop-opacity="0" />
        </linearGradient>
        <linearGradient :id="`${uid}-down`" x1="0" :y1="zeroY" x2="0" :y2="height" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#f2777a" stop-opacity="0" />
          <stop offset="100%" stop-color="#f2777a" stop-opacity=".2" />
        </linearGradient>
        <clipPath :id="`${uid}-reveal`">
          <rect x="0" y="-4" :width="width * reveal" :height="height + 8" />
        </clipPath>
        <clipPath :id="`${uid}-above`"><rect x="0" y="-4" :width="width" :height="Math.max(0, zeroY + 4)" /></clipPath>
        <clipPath :id="`${uid}-below`"><rect x="0" :y="zeroY" :width="width" :height="Math.max(0, height - zeroY + 4)" /></clipPath>
      </defs>

      <line v-if="diverging" :x1="0" :x2="width" :y1="zeroY" :y2="zeroY" class="spk__zero" />

      <g :clip-path="`url(#${uid}-reveal)`">
        <template v-if="diverging">
          <path :d="areaPath" :fill="`url(#${uid}-up)`" :clip-path="`url(#${uid}-above)`" />
          <path :d="areaPath" :fill="`url(#${uid}-down)`" :clip-path="`url(#${uid}-below)`" />
          <path :d="linePath" class="spk__line" stroke="#5bd18b" :clip-path="`url(#${uid}-above)`" />
          <path :d="linePath" class="spk__line" stroke="#f2777a" :clip-path="`url(#${uid}-below)`" />
        </template>
        <template v-else>
          <path :d="areaPath" :fill="`url(#${uid}-fill)`" />
          <path :d="linePath" class="spk__line" :stroke="color" />
        </template>
        <path v-if="refPath" :d="refPath" class="spk__ref" />
      </g>

      <g v-if="mark && reveal > 0.98" :transform="`translate(${mark.x},${mark.y})`">
        <g class="spk__mark">
          <circle r="8" :fill="color" opacity=".14" />
          <circle r="4" :fill="color" stroke="#101115" stroke-width="2" />
        </g>
      </g>

      <g v-if="tip">
        <line :x1="tip.x" :x2="tip.x" :y1="0" :y2="height" class="spk__cross" />
        <circle :cx="tip.x" :cy="tip.y" r="4" :fill="diverging ? (values[hover] >= 0 ? '#5bd18b' : '#f2777a') : color" stroke="#101115" stroke-width="2" />
      </g>
    </svg>

    <div v-if="tip" class="cv-tip spk__tip" :class="{ 'is-flip': tip.flip }" :style="{ left: `${tip.x}px` }">
      <div v-if="tip.label" class="cv-tip__date">{{ tip.label }}</div>
      <div class="cv-tip__row"><b>{{ tip.value }}</b></div>
      <div v-if="tip.ref && referenceLabel" class="cv-tip__row"><span>{{ referenceLabel }}</span><b>{{ tip.ref }}</b></div>
    </div>
  </div>
</template>

<style scoped>
.spk { position: relative; flex: 1; min-width: 0; touch-action: pan-y; cursor: crosshair; }
.spk__svg { position: absolute; inset: 0; overflow: visible; }
.spk__line { fill: none; stroke-width: 1.75; stroke-linejoin: round; stroke-linecap: round; }
.spk__ref { fill: none; stroke: #8a8d99; stroke-width: 1.25; stroke-dasharray: 3 4; opacity: .7; }
.spk__zero { stroke: rgba(255, 255, 255, .1); stroke-dasharray: 2 4; }
.spk__cross { stroke: rgba(255, 255, 255, .2); stroke-width: 1; }
.spk__mark { animation: spk-pop .5s var(--cv-ease); transform-box: fill-box; transform-origin: center; }
@keyframes spk-pop { from { opacity: 0; transform: scale(.4); } }
.spk__tip {
  position: absolute; bottom: calc(100% + 6px); transform: translateX(-12px); pointer-events: none; z-index: 5;
  white-space: nowrap; min-width: 0;
}
.spk__tip.is-flip { transform: translateX(calc(-100% + 12px)); }
</style>
