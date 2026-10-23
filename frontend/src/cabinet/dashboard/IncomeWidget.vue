<script setup>
/** Пассивный доход: ожидаемые выплаты в год, средний месяц и прогноз по месяцам на год вперёд. */
import { computed, onMounted, ref } from 'vue'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import { money, monthLong, pct } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  annual: { type: Number, default: 0 },
  yieldPercent: { type: Number, default: 0 },
  yieldOnInvested: { type: Number, default: 0 },
  future: { type: Array, default: () => [] },
})

const monthly = computed(() => (props.annual || 0) / 12)

const monthTotal = (p) =>
  Number(p?.total_amount) || (Number(p?.dividends) || 0) + (Number(p?.coupons) || 0) + (Number(p?.amortizations) || 0)

// прогноз выплат на 12 месяцев вперёд, включая текущий
const LETTERS = ['Я', 'Ф', 'М', 'А', 'М', 'И', 'И', 'А', 'С', 'О', 'Н', 'Д']
const bars = computed(() => {
  const byMonth = new Map((props.future || []).map((p) => [p.month, monthTotal(p)]))
  const now = new Date()
  const list = []
  for (let k = 0; k < 12; k++) {
    const d = new Date(now.getFullYear(), now.getMonth() + k, 1)
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    list.push({ key, date: d, letter: LETTERS[d.getMonth()], total: byMonth.get(key) || 0 })
  }
  const max = Math.max(1, ...list.map((b) => b.total))
  return list.map((b) => ({ ...b, h: b.total / max }))
})
const barsTotal = computed(() => bars.value.reduce((s, b) => s + b.total, 0))
const hoverBar = ref(null)

const grown = ref(false)
onMounted(() => requestAnimationFrame(() => requestAnimationFrame(() => { grown.value = true })))

const fmt = (v) => money(v)
const yieldHint = computed(() => `К текущей стоимости. На вложенный капитал — ${pct(props.yieldOnInvested, { sign: false, digits: 2 })}`)
</script>

<template>
  <CvWidget v-bind="$attrs" title="Пассивный доход">
    <div class="in">
      <div class="in__value">
        <CvNumber :value="annual" :format="fmt" dim />
        <span class="in__unit">в год</span>
      </div>
      <p class="in__sub">
        <span>≈ <b class="cv-num">{{ money(monthly) }}</b> в месяц</span>
        <span class="in__sep" />
        <span :title="yieldHint">доходность <b class="cv-num">{{ pct(yieldPercent, { sign: false, digits: 1 }) }}</b></span>
      </p>

      <div v-if="barsTotal > 0" class="in__fc">
        <div class="in__fc-head">
          <Transition name="in-swap" mode="out-in">
            <span :key="hoverBar?.key || 'all'">{{ hoverBar ? monthLong(hoverBar.date) : 'Следующие 12 месяцев' }}</span>
          </Transition>
          <b class="cv-num">{{ money(hoverBar ? hoverBar.total : barsTotal) }}</b>
        </div>
        <div class="in__fc-bars" :class="{ 'is-grown': grown, 'has-hover': hoverBar }" @pointerleave="hoverBar = null">
          <div
            v-for="(b, i) in bars"
            :key="b.key"
            class="in__fc-col"
            :class="{ 'is-on': hoverBar?.key === b.key, 'is-empty': !b.total }"
            :style="{ '--h': b.h, '--i': i }"
            @pointerenter="hoverBar = b"
          >
            <span class="in__fc-track"><i /></span>
            <small>{{ b.letter }}</small>
          </div>
        </div>
      </div>
      <p v-else class="in__empty">Прогноза выплат пока нет — он появится, когда в портфеле будут дивидендные акции или облигации.</p>
    </div>
  </CvWidget>
</template>

<style scoped>
.in { display: flex; flex-direction: column; height: 100%; min-width: 0; }
.in__value {
  display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;
  font-family: var(--cv-display); font-size: 34px; font-weight: 500; letter-spacing: -0.04em; color: var(--cv-ink);
}
.in__unit { font-family: var(--cv-text); font-size: 13px; font-weight: 500; letter-spacing: 0; color: var(--cv-mut); }
.in__sub { display: flex; align-items: center; flex-wrap: wrap; gap: 4px 8px; margin-top: 10px; font-size: 12.5px; color: var(--cv-mut); }
.in__sub b { color: var(--cv-ink-2); font-weight: 550; }
.in__sub span[title] { cursor: help; }
.in__sep { width: 3px; height: 3px; border-radius: 50%; background: var(--cv-dim); }

.in__fc { flex: 1; display: flex; flex-direction: column; gap: 12px; min-height: 140px; margin-top: 28px; }
.in__fc-head { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; color: var(--cv-mut); }
.in__fc-head b { color: var(--cv-ink); font-weight: 550; }
.in__fc-bars { flex: 1; display: flex; gap: 2px; min-height: 90px; }
.in__fc-col { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 8px; min-width: 0; cursor: default; }
.in__fc-track { position: relative; flex: 1; width: 100%; }
.in__fc-track i {
  position: absolute; left: 50%; bottom: 0; width: min(14px, 70%); height: max(2px, calc(var(--h) * 100%)); border-radius: 4px 4px 1px 1px;
  margin-left: calc(min(14px, 70%) / -2);
  background: var(--cv-s1);
  transform-origin: bottom; transform: scaleY(0);
  transition: transform .9s var(--cv-ease) calc(var(--i) * 40ms + 200ms), opacity .2s, background-color .2s;
}
.in__fc-col.is-empty i { background: rgba(255, 255, 255, .08); }
.in__fc-bars.is-grown .in__fc-track i { transform: scaleY(1); }
.in__fc-bars.has-hover .in__fc-col:not(.is-on) i { opacity: .35; }
.in__fc-col.is-on i { background: var(--cv-s2); }
.in__fc-col small { font-size: 10.5px; color: var(--cv-dim); line-height: 1; }
.in__fc-col.is-on small { color: var(--cv-ink-2); }
.in__empty { margin-top: auto; font-size: 12.5px; line-height: 1.5; color: var(--cv-dim); }

.in-swap-enter-active, .in-swap-leave-active { transition: opacity .12s; }
.in-swap-enter-from, .in-swap-leave-to { opacity: 0; }
</style>
