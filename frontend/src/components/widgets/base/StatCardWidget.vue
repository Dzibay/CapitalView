<script setup>
import { computed, inject, onUnmounted, ref, unref, watch } from 'vue'
import Widget from './Widget.vue'
import ValueChangePill from './ValueChangePill.vue'
import Tooltip from '../../base/Tooltip.vue'
import { formatCurrency } from '../../../utils/formatCurrency'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

const props = defineProps({
  title: {
    type: String,
    required: true
  },
  icon: {
    type: [Object, Function],
    default: null
  },
  mainValue: {
    type: [Number, String],
    required: true
  },
  mainValueFormat: {
    type: String,
    default: 'currency',
    validator: (value) => ['currency', 'percent', 'number', 'custom'].includes(value)
  },
  mainValueTooltip: {
    type: String,
    default: null
  },
  changeValue: {
    type: Number,
    default: null
  },
  changeIsPositive: {
    type: Boolean,
    default: null
  },
  changeTooltip: {
    type: String,
    default: null
  },
  secondaryText: {
    type: String,
    default: null
  },
  secondaryValue: {
    type: [Number, String],
    default: null
  },
  secondaryFormat: {
    type: String,
    default: 'currency',
    validator: (value) => ['currency', 'percent', 'number', 'custom'].includes(value)
  },
  secondaryClass: {
    type: String,
    default: null
  },
  changePosition: {
    type: String,
    default: 'right',
    validator: (value) => ['right', 'below'].includes(value)
  },
  secondaryTextSuffix: {
    type: String,
    default: null
  },
  secondaryTooltip: {
    type: String,
    default: null
  },
  mainValueSuffix: {
    type: String,
    default: null
  },
  /** Лендинг: счётчик и лёгкий scale при появлении превью в зоне видимости */
  scrollReveal: {
    type: Boolean,
    default: false
  },
  mainCurrencyMaxDigits: {
    type: Number,
    default: null
  },
  mainCurrencyMinDigits: {
    type: Number,
    default: null
  },
  /** Ref или уже развёрнутый boolean из шаблона родителя */
  landingRevealRef: {
    type: [Object, Boolean],
    default: null
  }
})

const injectedLandingReveal = inject(LANDING_DASH_REVEAL_KEY, null)

function revealSource() {
  return props.landingRevealRef ?? injectedLandingReveal
}

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

const animMain = ref(0)
const animSecondary = ref(0)
const animChange = ref(0)
const popScale = ref(1)

let rafId = null

function readTargets() {
  const main = props.mainValueFormat === 'custom' ? null : Number(props.mainValue) || 0
  let sec = null
  if (props.secondaryValue !== null && props.secondaryValue !== undefined && props.secondaryFormat !== 'custom') {
    sec = Number(props.secondaryValue) || 0
  }
  const ch =
    props.changeValue === null || props.changeValue === undefined ? null : Number(props.changeValue) || 0
  return { main, sec, ch }
}

function applyStaticTargets() {
  const { main, sec, ch } = readTargets()
  if (main !== null) animMain.value = main
  if (sec !== null) animSecondary.value = sec
  if (ch !== null) animChange.value = ch
  popScale.value = 1
}

function runRevealAnimation() {
  const { main, sec, ch } = readTargets()
  const duration = 920
  if (prefersReducedMotion()) {
    applyStaticTargets()
    return
  }
  const m0 = 0
  const m1 = main ?? 0
  const s1 = sec ?? 0
  const c1 = ch ?? 0
  const start = performance.now()
  if (rafId) cancelAnimationFrame(rafId)
  function frame(now) {
    const u = Math.min(1, (now - start) / duration)
    const t = easeOutCubic(u)
    if (main !== null) animMain.value = m0 + (m1 - m0) * t
    if (sec !== null) animSecondary.value = 0 + (s1 - 0) * t
    if (ch !== null) animChange.value = 0 + (c1 - 0) * t
    popScale.value = 0.92 + 0.08 * t
    if (u < 1) rafId = requestAnimationFrame(frame)
    else {
      rafId = null
      applyStaticTargets()
    }
  }
  if (main !== null) animMain.value = m0
  if (sec !== null) animSecondary.value = 0
  if (ch !== null) animChange.value = 0
  popScale.value = 0.92
  rafId = requestAnimationFrame(frame)
}

function syncReveal() {
  if (!props.scrollReveal) {
    applyStaticTargets()
    return
  }
  const src = revealSource()
  if (src == null) {
    applyStaticTargets()
    return
  }
  const revealed = unref(src)
  if (!revealed) {
    const { main, sec, ch } = readTargets()
    if (main !== null) animMain.value = 0
    if (sec !== null) animSecondary.value = 0
    if (ch !== null) animChange.value = 0
    popScale.value = 0.92
    return
  }
  runRevealAnimation()
}

watch(
  () => {
    if (!props.scrollReveal) return true
    const src = revealSource()
    if (src == null) return true
    return unref(src)
  },
  () => syncReveal(),
  { immediate: true }
)

watch(
  () => [props.mainValue, props.secondaryValue, props.changeValue, props.mainValueFormat],
  () => {
    if (!props.scrollReveal) applyStaticTargets()
    else {
      const src = revealSource()
      if (src != null && unref(src)) runRevealAnimation()
    }
  }
)

onUnmounted(() => {
  if (rafId) cancelAnimationFrame(rafId)
})

const numericMainForFormat = computed(() => {
  if (props.mainValueFormat === 'custom') return null
  if (!props.scrollReveal) return Number(props.mainValue) || 0
  return animMain.value
})

const formattedMainValue = computed(() => {
  if (props.mainValueFormat === 'custom') {
    return props.mainValue
  }
  const n = numericMainForFormat.value ?? 0

  if (props.mainValueFormat === 'currency') {
    const maxD = props.mainCurrencyMaxDigits ?? 0
    const minD = props.mainCurrencyMinDigits ?? 0
    return formatCurrency(n, { maximumFractionDigits: maxD, minimumFractionDigits: minD })
  }

  if (props.mainValueFormat === 'percent') {
    return new Intl.NumberFormat('ru-RU', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(n / 100)
  }

  if (props.mainValueFormat === 'number') {
    return n.toFixed(2)
  }

  return props.mainValue
})

const numericSecondaryForFormat = computed(() => {
  if (props.secondaryValue === null || props.secondaryValue === undefined) return null
  if (props.secondaryFormat === 'custom') return null
  if (!props.scrollReveal) return Number(props.secondaryValue) || 0
  return animSecondary.value
})

const formattedSecondaryValue = computed(() => {
  if (props.secondaryValue === null || props.secondaryValue === undefined) {
    return null
  }

  if (props.secondaryFormat === 'custom') {
    return props.secondaryValue
  }

  const n = numericSecondaryForFormat.value ?? 0

  if (props.secondaryFormat === 'currency') {
    return formatCurrency(n)
  }

  if (props.secondaryFormat === 'percent') {
    return new Intl.NumberFormat('ru-RU', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(n / 100)
  }

  if (props.secondaryFormat === 'number') {
    return n.toFixed(2)
  }

  return props.secondaryValue
})

const displayedChangeValue = computed(() => {
  if (props.changeValue === null || props.changeValue === undefined) return props.changeValue
  if (!props.scrollReveal) return props.changeValue
  return animChange.value
})

const computedChangeIsPositive = computed(() => {
  if (props.changeIsPositive !== null && props.changeIsPositive !== undefined) {
    return props.changeIsPositive
  }
  const v = displayedChangeValue.value
  if (v !== null && v !== undefined) {
    return v >= 0
  }
  return null
})

const mainWrapperStyle = computed(() => {
  if (!props.scrollReveal) return undefined
  return {
    transform: `scale(${popScale.value})`,
    transformOrigin: 'left center',
    willChange: 'transform'
  }
})
</script>

<template>
  <Widget :title="title" :icon="icon" compact>
    <div class="stat-card-content" :class="{ 'change-below': changePosition === 'below' }">
      <div class="main-value-row">
        <div class="main-value-wrapper" :style="mainWrapperStyle">
          <Tooltip v-if="mainValueTooltip" :content="mainValueTooltip" position="top">
            <div class="main-value">
              {{ formattedMainValue }}
            </div>
          </Tooltip>
          <div v-else class="main-value">
            {{ formattedMainValue }}
          </div>
          <span
            v-if="mainValueSuffix || (secondaryText && changePosition !== 'below' && !formattedSecondaryValue)"
            class="main-value-suffix"
          >
            {{ mainValueSuffix || secondaryText }}
          </span>
        </div>

        <Tooltip
          v-if="changeValue !== null && changeValue !== undefined && changeTooltip"
          :content="changeTooltip"
          position="top"
        >
          <ValueChangePill
            v-if="changeValue !== null && changeValue !== undefined"
            :value="displayedChangeValue"
            :is-positive="computedChangeIsPositive"
            format="percent"
          />
        </Tooltip>
        <ValueChangePill
          v-else-if="changeValue !== null && changeValue !== undefined"
          :value="displayedChangeValue"
          :is-positive="computedChangeIsPositive"
          format="percent"
        />
      </div>

      <p v-if="secondaryText || formattedSecondaryValue" class="secondary-text">
        <Tooltip
          v-if="secondaryValue !== null && secondaryValue !== undefined && secondaryTooltip"
          :content="secondaryTooltip"
          position="top"
        >
          <span v-if="secondaryText && formattedSecondaryValue && secondaryText.includes(':')">{{ secondaryText }}</span>
          <span v-if="formattedSecondaryValue !== null" :class="secondaryClass">
            {{ formattedSecondaryValue }}
          </span>
          <span v-if="secondaryText && formattedSecondaryValue && !secondaryText.includes(':')">{{ secondaryText }}</span>
        </Tooltip>
        <template v-else>
          <span v-if="secondaryText && formattedSecondaryValue && secondaryText.includes(':')">{{ secondaryText }}</span>
          <span v-if="formattedSecondaryValue !== null" :class="secondaryClass">
            {{ formattedSecondaryValue }}
          </span>
          <span v-if="secondaryText && formattedSecondaryValue && !secondaryText.includes(':')">{{ secondaryText }}</span>
          <span v-else-if="secondaryText && !formattedSecondaryValue">{{ secondaryText }}</span>
        </template>
        <span v-if="secondaryTextSuffix && formattedSecondaryValue">{{ secondaryTextSuffix }}</span>
      </p>
    </div>
  </Widget>
</template>

<style scoped>
.stat-card-content {
  display: flex;
  flex-direction: column;
}

.main-value-row {
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stat-card-content.change-below .main-value-row {
  flex-direction: column;
  align-items: flex-start;
  gap: 0.25rem;
}

.main-value-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}

.main-value {
  font-size: var(--widget-font-main, 1.5rem);
  font-weight: var(--widget-font-main-weight, 600);
  color: var(--text-primary, #111827);
  line-height: 1.2;
}

.main-value-suffix {
  font-size: var(--widget-font-secondary, 1rem);
  color: var(--text-tertiary, #6b7280);
  line-height: 1;
  padding-bottom: 0.2rem;
  margin: 0;
}

.secondary-text {
  margin: 0;
  margin-top: 0;
  font-size: var(--widget-font-secondary, 1rem);
  color: var(--text-tertiary, #6b7280);
  line-height: 1.2;
}

.secondary-text .positive {
  color: var(--positiveColor, #1cbd88);
}

.secondary-text .negative {
  color: var(--negativeColor, #ef4444);
}
</style>
