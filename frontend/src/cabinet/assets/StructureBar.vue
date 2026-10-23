<script setup>
/**
 * Структура портфеля одной полосой: доли типов активов и свободных денег.
 * Цвет закреплён за типом (typeColor), подписи — в легенде под полосой.
 */
import { computed, ref } from 'vue'
import { typeColor, typeGroup, OTHER } from '../palette'
import { money, pct } from '../format'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  cash: { type: Number, default: 0 },
})

const CASH = 'Свободные деньги'

const parts = computed(() => {
  const map = new Map()
  for (const r of props.rows) {
    if (!(r.value > 0)) continue
    const g = typeGroup(r.type)
    map.set(g, (map.get(g) || 0) + r.value)
  }
  const list = [...map].map(([label, value]) => ({ label, value, color: typeColor(label) }))
  list.sort((a, b) => b.value - a.value)
  if (props.cash > 0) list.push({ label: CASH, value: props.cash, color: OTHER, cash: true })
  const total = list.reduce((s, p) => s + p.value, 0) || 1
  return list.map((p) => ({ ...p, share: (p.value / total) * 100 }))
})

const hover = ref(null)
</script>

<template>
  <section class="sb cv-card">
    <div class="sb__head">
      <h2 class="sb__title">Структура</h2>
      <span class="sb__sub">по типам активов</span>
    </div>

    <div class="sb__bar" @mouseleave="hover = null">
      <span
        v-for="p in parts"
        :key="p.label"
        class="sb__seg"
        :class="{ 'is-cash': p.cash, 'is-dim': hover && hover !== p.label }"
        :style="{ flexGrow: p.share, background: p.cash ? undefined : p.color }"
        @mouseenter="hover = p.label"
      />
    </div>

    <ul class="sb__legend">
      <li
        v-for="p in parts"
        :key="p.label"
        :class="{ 'is-dim': hover && hover !== p.label }"
        @mouseenter="hover = p.label"
        @mouseleave="hover = null"
      >
        <i :class="{ 'is-cash': p.cash }" :style="{ background: p.cash ? undefined : p.color }" />
        <span>{{ p.label }}</span>
        <b class="cv-num">{{ pct(p.share, { sign: false }) }}</b>
        <small class="cv-num">{{ money(p.value) }}</small>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.sb { display: flex; flex-direction: column; gap: 16px; padding: 20px 22px; }
.sb__head { display: flex; align-items: baseline; gap: 10px; }
.sb__title { margin: 0; font-size: 14px; font-weight: 600; color: var(--cv-ink); }
.sb__sub { font-size: 12.5px; color: var(--cv-dim); }

.sb__bar { display: flex; gap: 2px; height: 10px; }
.sb__seg { min-width: 3px; flex-basis: 0; border-radius: 2px; transition: opacity .2s, flex-grow .6s var(--cv-ease); }
.sb__seg:first-child { border-radius: 5px 2px 2px 5px; }
.sb__seg:last-child { border-radius: 2px 5px 5px 2px; }
.sb__seg:only-child { border-radius: 5px; }
.sb__seg.is-dim, .sb__legend li.is-dim { opacity: .35; }
.is-cash { background: repeating-linear-gradient(135deg, #5d606c 0 2px, transparent 2px 5px); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .12); }

.sb__legend { display: flex; flex-wrap: wrap; gap: 8px 22px; margin: 0; padding: 0; list-style: none; }
.sb__legend li { display: inline-flex; align-items: baseline; gap: 7px; font-size: 12.5px; color: var(--cv-mut); transition: opacity .2s; cursor: default; }
.sb__legend i { align-self: center; width: 8px; height: 8px; flex: none; border-radius: 2px; }
.sb__legend b { font-weight: 600; color: var(--cv-ink); }
.sb__legend small { font-size: 11.5px; color: var(--cv-dim); }

@media (max-width: 768px) {
  .sb { padding: 16px; }
  .sb__legend { gap: 8px 16px; }
  .sb__legend small { display: none; }
}
</style>
