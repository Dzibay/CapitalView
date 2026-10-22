<script setup>
import { computed, reactive, watch } from 'vue'
import { gsap } from 'gsap'
import { formatRub } from './useLandingMotion'

/** Интерактивный ребалансер: веса классов → донат, риск-метр и прогноз. */
const classes = [
  { id: 'eq', label: 'Акции', c: '#2f5bff', r: 0.14, vol: 22 },
  { id: 'bd', label: 'Облигации', c: '#8aa6ff', r: 0.095, vol: 6 },
  { id: 'fd', label: 'Фонды', c: '#111111', r: 0.12, vol: 15 },
  { id: 'gd', label: 'Золото', c: '#e8b84a', r: 0.08, vol: 14 },
  { id: 'cr', label: 'Крипто', c: '#ff8a5c', r: 0.3, vol: 70 }
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
  gsap.to(shown, { ...Object.fromEntries(raw.map((v, i) => [i, v])), duration: 0.7, ease: 'elastic.out(1, 0.75)', overwrite: true })
})

const segments = computed(() => {
  let off = 0
  return classes.map((c, i) => {
    const len = (shown[i] / shownSum.value) * C
    const seg = { c: c.c, dash: `${Math.max(len - 4, 0)} ${C}`, off: -off }
    off += len
    return seg
  })
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
      <div class="br__presets">
        <button
          v-for="(_, name) in presets"
          :key="name"
          type="button"
          :class="{ 'is-on': activePreset === name }"
          @click="applyPreset(name)"
        >{{ name }}</button>
      </div>
      <label v-for="(c, i) in classes" :key="c.id" class="br__row">
        <span class="br__name"><i :style="{ background: c.c }" />{{ c.label }}</span>
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
          <span class="pb-mono">Доходность</span>
          <b>{{ (tw.ret * 100).toFixed(1) }}%</b>
          <small>в год, ожидаемо</small>
        </div>
      </div>

      <div class="br__side">
        <div class="br__gauge">
          <svg viewBox="0 0 200 110">
            <defs>
              <linearGradient id="br-g" x1="0" x2="1">
                <stop offset="0" stop-color="#c8f560" />
                <stop offset=".55" stop-color="#e8b84a" />
                <stop offset="1" stop-color="#ff5c3a" />
              </linearGradient>
            </defs>
            <path d="M15,100 A85,85 0 0 1 185,100" fill="none" stroke="#ece8df" stroke-width="14" stroke-linecap="round" />
            <path
              d="M15,100 A85,85 0 0 1 185,100"
              fill="none" stroke="url(#br-g)" stroke-width="14" stroke-linecap="round"
              pathLength="100" :stroke-dasharray="`${tw.risk * 100} 100`"
            />
            <g :transform="`rotate(${-90 + tw.risk * 180} 100 100)`">
              <line x1="100" y1="100" x2="100" y2="30" stroke="#111" stroke-width="3" stroke-linecap="round" />
            </g>
            <circle cx="100" cy="100" r="7" fill="#111" />
          </svg>
          <div class="br__profile">
            <span class="pb-mono">Риск-профиль</span>
            <b>{{ profile }}</b>
          </div>
        </div>
        <div class="br__future">
          <span class="pb-mono">1 000 000 ₽ через 10 лет</span>
          <b>{{ formatRub(tw.future) }}</b>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.br {
  display: grid; grid-template-columns: 1fr 1.15fr; gap: clamp(24px, 4vw, 56px);
  background: rgba(255, 255, 255, 0.8); border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 32px; padding: clamp(20px, 3.5vw, 44px);
  backdrop-filter: blur(16px);
  box-shadow: 0 50px 100px -60px rgba(17, 17, 17, 0.5);
}
.br__presets { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 22px; }
.br__presets button {
  border: 1px solid rgba(17, 17, 17, 0.15); background: transparent; color: #111;
  padding: 9px 16px; border-radius: 999px; font: 600 13px 'Inter Tight', sans-serif; cursor: pointer;
  transition: background 0.25s, color 0.25s;
}
.br__presets button:hover { background: rgba(17, 17, 17, 0.06); }
.br__presets button.is-on { background: #111; color: #fff; border-color: #111; }
.br__row { display: grid; grid-template-columns: 110px 1fr 46px; align-items: center; gap: 14px; padding: 12px 0; border-bottom: 1px solid rgba(17, 17, 17, 0.07); }
.br__name { display: flex; align-items: center; gap: 8px; font-weight: 600; color: #111; font-size: 15px; }
.br__name i { width: 10px; height: 10px; border-radius: 3px; }
.br__row b { text-align: right; font: 600 14px 'JetBrains Mono', monospace; color: #111; }
.br__row input {
  -webkit-appearance: none; appearance: none; width: 100%; height: 6px; border-radius: 6px;
  background: linear-gradient(90deg, var(--c) var(--p), #ece8df var(--p)); outline: none; cursor: pointer;
}
.br__row input::-webkit-slider-thumb {
  -webkit-appearance: none; width: 22px; height: 22px; border-radius: 50%;
  background: #fff; border: 2px solid #111; box-shadow: 0 4px 10px rgba(17, 17, 17, 0.2);
  transition: transform 0.2s;
}
.br__row input:active::-webkit-slider-thumb { transform: scale(1.25); }
.br__row input::-moz-range-thumb { width: 20px; height: 20px; border-radius: 50%; background: #fff; border: 2px solid #111; }

.br__viz { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; align-items: center; }
.br__donut { position: relative; }
.br__donut svg { width: 100%; transform: rotate(-90deg); }
.br__track { fill: none; stroke: #ece8df; stroke-width: 26; }
.br__seg { fill: none; stroke-width: 26; }
.br__center { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; gap: 2px; }
.br__center b { font: 800 clamp(28px, 3.4vw, 46px) / 1 'Inter Tight', sans-serif; letter-spacing: -0.03em; color: #111; font-variant-numeric: tabular-nums; }
.br__center small { color: #7a766e; font-size: 12px; }
.br__side { display: grid; gap: 22px; }
.br__gauge svg { width: 100%; max-width: 240px; display: block; }
.br__profile { display: grid; gap: 4px; margin-top: 6px; }
.br__profile b { font: 800 22px 'Inter Tight', sans-serif; color: #111; letter-spacing: -0.02em; }
.br__future { padding: 16px 18px; border-radius: 18px; background: #111; color: #fff; display: grid; gap: 6px; }
.br__future .pb-mono { color: #8b877f; }
.br__future b { font: 800 clamp(22px, 2.4vw, 30px) 'Inter Tight', sans-serif; letter-spacing: -0.02em; color: #c8f560; font-variant-numeric: tabular-nums; }

@media (max-width: 899px) {
  .br { grid-template-columns: 1fr; border-radius: 24px; }
  .br__row { grid-template-columns: 92px 1fr 40px; gap: 10px; }
  .br__viz { grid-template-columns: 1fr; gap: 20px; }
  .br__donut { width: min(240px, 80%); margin: 0 auto; }
  .br__side { grid-template-columns: 1fr; justify-items: center; text-align: center; }
  .br__future { width: 100%; box-sizing: border-box; }
}
</style>
