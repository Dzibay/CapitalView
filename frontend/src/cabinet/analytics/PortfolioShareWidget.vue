<script setup>
/**
 * Доли подпортфелей в выбранном портфеле: сегментная полоса сверху и список с суммами.
 * Цвет закреплён за подпортфелем по порядку в дереве, а не по размеру.
 */
import { computed, ref } from 'vue'
import CvWidget from '../ui/CvWidget.vue'
import { SERIES, OTHER } from '../palette'
import { money, pct } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  /** [{ id, name, value }] — в порядке дерева; собственные активы родителя — отдельным пунктом */
  items: { type: Array, default: () => [] },
})

const rows = computed(() => {
  const list = props.items.map((it, i) => ({ ...it, color: i < SERIES.length ? SERIES[i] : OTHER, value: Math.max(0, Number(it.value) || 0) }))
  const total = list.reduce((s, r) => s + r.value, 0) || 1
  return list.map((r) => ({ ...r, share: (r.value / total) * 100 })).sort((a, b) => b.value - a.value)
})
const hover = ref(null)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Доли портфелей">
    <div class="ps">
      <div class="ps__bar" role="img" :aria-label="rows.map((r) => `${r.name} ${pct(r.share, { sign: false })}`).join(', ')">
        <i
          v-for="r in rows.filter((r) => r.value > 0)"
          :key="r.id"
          :class="{ 'is-dim': hover != null && hover !== r.id }"
          :style="{ flexGrow: r.value, background: r.color }"
          @pointerenter="hover = r.id"
          @pointerleave="hover = null"
        />
      </div>

      <ul class="ps__list" @pointerleave="hover = null">
        <li
          v-for="(r, i) in rows"
          :key="r.id"
          class="ps__row"
          :class="{ 'is-dim': hover != null && hover !== r.id }"
          :style="{ '--i': i }"
          @pointerenter="hover = r.id"
        >
          <i class="ps__sw" :style="{ background: r.color }" />
          <span class="ps__name">{{ r.name }}</span>
          <span class="ps__val cv-num">{{ money(r.value) }}</span>
          <span class="ps__share cv-num">{{ pct(r.share, { sign: false }) }}</span>
        </li>
      </ul>
    </div>
  </CvWidget>
</template>

<style scoped>
.ps { display: flex; flex-direction: column; gap: 18px; min-width: 0; }
.ps__bar { display: flex; gap: 2px; height: 12px; border-radius: 6px; overflow: hidden; }
.ps__bar i { display: block; flex-basis: 0; min-width: 3px; transition: opacity .2s; animation: ps-grow .9s var(--cv-ease) backwards .1s; transform-origin: left; }
.ps__bar i.is-dim { opacity: .3; }
.ps__list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.ps__row {
  display: grid; grid-template-columns: 10px minmax(0, 1fr) auto 56px; align-items: center; gap: 12px;
  height: 40px; padding: 0 10px; margin: 0 -10px; border-radius: 10px;
  transition: opacity .2s, background .2s;
  animation: ps-in .6s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 40ms + 80ms);
}
.ps__row + .ps__row { box-shadow: inset 0 1px 0 var(--cv-line); }
.ps__row:hover { background: var(--cv-hover); box-shadow: none; }
.ps__row.is-dim { opacity: .45; }
.ps__sw { width: 10px; height: 10px; border-radius: 3px; }
.ps__name { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ps__val { font-size: 13px; color: var(--cv-ink-2); white-space: nowrap; }
.ps__share { text-align: right; font-size: 13px; font-weight: 600; color: var(--cv-ink); }

@keyframes ps-in { from { opacity: 0; transform: translateY(4px); } }
@keyframes ps-grow { from { transform: scaleX(0); } }
@media (prefers-reduced-motion: reduce) {
  .ps__row, .ps__bar i { animation: none; }
}
</style>
