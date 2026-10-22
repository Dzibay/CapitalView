<script setup>
import { computed, reactive, watch } from 'vue'
import { gsap } from 'gsap'
import LandingIcon from './LandingIcon.vue'
import { formatRub } from './useLandingMotion'

/** Интерактивный ребалансер: веса классов → донат, риск-метр и прогноз. */
const classes = [
  { id: 'eq', label: 'Акции', icon: 'candles', c: '#3d5afe', r: 0.14, vol: 22 },
  { id: 'bd', label: 'Облигации', icon: 'bond', c: '#22b8cf', r: 0.095, vol: 6 },
  { id: 'fd', label: 'Фонды', icon: 'layers', c: '#8b5cf6', r: 0.12, vol: 15 },
  { id: 'gd', label: 'Золото', icon: 'gold', c: '#f5b544', r: 0.08, vol: 14 },
  { id: 'cr', label: 'Крипто', icon: 'bitcoin', c: '#ff7a45', r: 0.3, vol: 70 }
]
const presets = {
  'Консерватор': [20, 60, 10, 10, 0],
  'Баланс': [40, 30, 15, 10, 5],
  'Агрессор': [60, 5, 10, 5, 20]
}

const raw = reactive([40, 30, 15, 10, 5])
const shown = reactive(classes.map((_, i) => raw[i]))
const C = 2 * Math.PI * 70

const sum = computed(() => raw.reduce((a, b) => a + b, 0) || 1)
const weights = computed(() => raw.map((v) => v / sum.value))
const shownSum = computed(() => shown.reduce((a, b) => a + b, 0) || 1)

const expReturn = computed(() => weights.value.reduce((a, w, i) => a + w * classes[i].r, 0))
const vol = computed(() => Math.sqrt(weights.value.reduce((a, w, i) => a + (w * classes[i].vol) ** 2, 0)) * 1.25)
const risk = computed(() => Math.min(1, vol.value / 40))
const profile = computed(() => (risk.value < 0.28 ? 'Консервативный' : risk.value < 0.55 ? 'Сбалансированный' : 'Агрессивный'))
const future = computed(() => 1_000_000 * (1 + expReturn.value) ** 10)

const tw = reactive({ risk: 0, future: 0, ret: 0 })
watch([risk, future, expReturn], ([r, f, e]) => {
  gsap.to(tw, { risk: r, future: f, ret: e, duration: 0.8, ease: 'power3.out', overwrite: true })
}, { immediate: true })

watch(raw, () => {
  gsap.to(shown, { ...Object.fromEntries(raw.map((v, i) => [i, v])), duration: 0.9, ease: 'expo.out', overwrite: true })
})

const segments = computed(() => {
  let off = 0
  return classes.map((c, i) => {
    const len = (shown[i] / shownSum.value) * C
    const seg = { c: c.c, dash: `${Math.max(len - 3, 0)} ${C}`, off: -off }
    off += len
    return seg
  })
})

/* траектория роста 1 млн ₽ за 10 лет — для мини-графика */
const growth = computed(() => {
  const r = tw.ret
  const max = 1_000_000 * 1.32 ** 10
  return Array.from({ length: 11 }, (_, y) => {
    const v = 1_000_000 * (1 + r) ** y
    return `${y * 30},${100 - (Math.log(v / 1_000_000) / Math.log(max / 1_000_000)) * 92}`
  }).join(' ')
})

function applyPreset(name) {
  presets[name].forEach((v, i) => { raw[i] = v })
}
const activePreset = computed(() =>
  Object.keys(presets).find((k) => presets[k].every((v, i) => v === raw[i])) || null
)
</script>

<template>
  <div class="br">
    <div class="br__controls">
      <div class="br__presets" role="tablist">
        <button
          v-for="(_, name) in presets"
          :key="name"
          type="button"
          :class="{ 'is-on': activePreset === name }"
          @click="applyPreset(name)"
        >{{ name }}</button>
      </div>
      <label v-for="(c, i) in classes" :key="c.id" class="br__row">
        <span class="br__name">
          <span class="br__icon" :style="{ '--c': c.c }"><LandingIcon :name="c.icon" :size="15" :stroke="1.7" /></span>
          {{ c.label }}
        </span>
        <input v-model.number="raw[i]" type="range" min="0" max="100" step="1" :style="{ '--p': raw[i] + '%', '--c': c.c }" />
        <b>{{ Math.round(weights[i] * 100) }}%</b>
      </label>
    </div>

    <div class="br__viz">
      <div class="br__donut">
        <svg viewBox="0 0 180 180">
          <circle cx="90" cy="90" r="70" class="br__track" />
          <circle
            v-for="(s, i) in segments"
            :key="i"
            cx="90" cy="90" r="70"
            class="br__seg"
            :stroke="s.c"
            :stroke-dasharray="s.dash"
            :stroke-dashoffset="s.off"
          />
        </svg>
        <div class="br__center">
          <small>Ожидаемая доходность</small>
          <b>{{ (tw.ret * 100).toFixed(1).replace('.', ',') }}%</b>
          <small>в год</small>
        </div>
      </div>

      <div class="br__side">
        <div class="br__panel">
          <span class="br__label">Риск-профиль</span>
          <b class="br__profile">{{ profile }}</b>
          <div class="br__meter">
            <i :style="{ left: tw.risk * 100 + '%' }" />
          </div>
          <div class="br__meter-scale"><span>Низкий</span><span>Высокий</span></div>
        </div>
        <div class="br__panel br__panel--dark">
          <span class="br__label">1 000 000 ₽ через 10 лет</span>
          <b class="br__future">{{ formatRub(tw.future) }}</b>
          <svg viewBox="0 0 300 100" preserveAspectRatio="none" class="br__growth">
            <polyline :points="growth" />
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.br {
  position: relative; isolation: isolate;
  display: grid; grid-template-columns: 1fr 1.15fr; gap: clamp(24px, 4vw, 64px);
  border-radius: 32px; padding: clamp(20px, 3.5vw, 48px);
  background: linear-gradient(180deg, #fff, #fbfbfd);
  box-shadow:
    inset 0 1px 0 #fff,
    0 0 0 1px rgba(11,13,18,.06),
    0 1px 2px rgba(11,13,18,.04),
    0 12px 24px -12px rgba(30,40,90,.08),
    0 50px 100px -40px rgba(30,40,90,.28);
}
/* мягкое цветное свечение под карточкой */
.br::before {
  content: ''; position: absolute; inset: 20% 10% -8%; z-index: -1; border-radius: 50%; pointer-events: none;
  background: radial-gradient(50% 50% at 50% 50%, rgba(61,90,254,.25), rgba(139,92,246,.12) 50%, transparent 75%);
  filter: blur(50px);
}
.br__donut svg { filter: drop-shadow(0 18px 24px rgba(30,40,90,.16)); }
.br__presets { display: inline-flex; gap: 2px; padding: 3px; margin-bottom: 18px; border-radius: 12px; background: var(--lp-bg-2); }
.br__presets button {
  border: 0; background: transparent; color: var(--lp-muted);
  padding: 8px 14px; border-radius: 9px; font: 500 13.5px var(--lp-text); cursor: pointer;
  transition: background .25s, color .25s, box-shadow .25s;
}
.br__presets button:hover { color: var(--lp-ink); }
.br__presets button.is-on { background: #fff; color: var(--lp-ink); box-shadow: 0 1px 3px rgba(11,13,18,.1); }
.br__row { display: grid; grid-template-columns: 140px 1fr 44px; align-items: center; gap: 16px; padding: 13px 0; border-bottom: 1px solid var(--lp-line); cursor: pointer; }
.br__row:last-child { border-bottom: 0; }
.br__name { display: flex; align-items: center; gap: 10px; font-weight: 500; color: var(--lp-ink); font-size: 14.5px; }
.br__icon {
  display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; flex: none;
  color: var(--c); background: color-mix(in srgb, var(--c) 10%, white);
}
.br__row b { text-align: right; font-weight: 600; font-size: 14px; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.br__row input {
  -webkit-appearance: none; appearance: none; width: 100%; height: 4px; border-radius: 4px; margin: 0;
  background: linear-gradient(90deg, var(--c) var(--p), #e7e9ee var(--p)); outline: none; cursor: pointer;
}
.br__row input::-webkit-slider-thumb {
  -webkit-appearance: none; width: 20px; height: 20px; border-radius: 50%;
  background: #fff; box-shadow: 0 0 0 1px rgba(11,13,18,.12), 0 2px 6px rgba(11,13,18,.2);
  transition: transform .25s var(--lp-ease);
}
.br__row input:hover::-webkit-slider-thumb { transform: scale(1.12); }
.br__row input:active::-webkit-slider-thumb { transform: scale(1.25); }
.br__row input:focus-visible::-webkit-slider-thumb { box-shadow: 0 0 0 4px rgba(61,90,254,.25), 0 2px 6px rgba(11,13,18,.2); }
.br__row input::-moz-range-thumb { width: 20px; height: 20px; border: 0; border-radius: 50%; background: #fff; box-shadow: 0 0 0 1px rgba(11,13,18,.12), 0 2px 6px rgba(11,13,18,.2); }

.br__viz { display: grid; grid-template-columns: 1fr 1fr; gap: 28px; align-items: center; }
.br__donut { position: relative; }
.br__donut svg { width: 100%; display: block; transform: rotate(-90deg); }
.br__track { fill: none; stroke: var(--lp-bg-2); stroke-width: 20; }
.br__seg { fill: none; stroke-width: 20; }
.br__center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; gap: 4px; }
.br__center b { font-family: var(--lp-display); font-weight: 600; font-size: clamp(30px, 3.4vw, 46px); line-height: 1; letter-spacing: -0.04em; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.br__center small { color: var(--lp-muted); font-size: 12px; }
.br__side { display: grid; gap: 14px; }
.br__panel { padding: 18px; border-radius: 20px; background: var(--lp-bg-2); display: grid; gap: 6px; box-shadow: inset 0 1px 2px rgba(11,13,18,.05); }
.br__label { font-size: 12.5px; color: var(--lp-muted); }
.br__profile { font-family: var(--lp-display); font-size: 21px; font-weight: 600; letter-spacing: -0.02em; color: var(--lp-ink); }
.br__meter { position: relative; height: 6px; margin-top: 10px; border-radius: 6px; background: linear-gradient(90deg, #12b76a, #f5b544 55%, #e5484d); }
.br__meter i {
  position: absolute; top: 50%; width: 16px; height: 16px; margin: -8px 0 0 -8px; border-radius: 50%;
  background: #fff; box-shadow: 0 0 0 1px rgba(11,13,18,.15), 0 3px 8px rgba(11,13,18,.25);
}
.br__meter-scale { display: flex; justify-content: space-between; font-size: 11px; color: var(--lp-muted); margin-top: 4px; }
.br__panel--dark {
  background: radial-gradient(120% 90% at 100% 100%, rgba(61,90,254,.35), transparent 60%), linear-gradient(160deg, #1a1e2c, #0b0d12);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.1), 0 20px 40px -20px rgba(11,13,40,.6);
}
.br__panel--dark .br__label { color: rgba(255,255,255,.55); }
.br__future {
  font-family: var(--lp-display); font-size: clamp(24px, 2.4vw, 32px); font-weight: 600; letter-spacing: -0.03em;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(90deg, #fff, #a5b4ff); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.br__growth { width: 100%; height: 48px; margin-top: 4px; overflow: visible; }
.br__growth polyline { fill: none; stroke: #8b9bff; stroke-width: 2; vector-effect: non-scaling-stroke; stroke-linejoin: round; }

@media (max-width: 1023px) {
  .br { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .br { border-radius: 24px; }
  .br__presets { display: flex; }
  .br__presets button { flex: 1; padding: 8px 6px; }
  .br__row { grid-template-columns: 112px 1fr 38px; gap: 10px; }
  .br__name { font-size: 13.5px; gap: 8px; }
  .br__icon { width: 26px; height: 26px; }
  .br__viz { grid-template-columns: 1fr; gap: 20px; }
  .br__donut { width: min(240px, 80%); margin: 0 auto; }
}
</style>
