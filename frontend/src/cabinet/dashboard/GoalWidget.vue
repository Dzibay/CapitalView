<script setup>
/**
 * Финансовая цель: кольцо прогресса и прогноз даты достижения
 * (ежемесячная капитализация: cur = cur·(1 + r/12) + взнос; с инфляцией цель растёт раз в год).
 */
import { computed, onMounted, ref, watch } from 'vue'
import { Target, Pencil } from 'lucide-vue-next'
import CvWidget from '../ui/CvWidget.vue'
import CvNumber from '../ui/CvNumber.vue'
import Sparkline from '../charts/Sparkline.vue'
import EditGoalModal from '../../components/modals/EditGoalModal.vue'
import { money, moneyCompact, monthLong, pct, plural } from '../format'

defineOptions({ inheritAttrs: false })

const props = defineProps({
  goal: { type: Object, required: true },
  defaultReturn: { type: Number, default: 0 },
  onSave: { type: Function, required: true },
})

const showModal = ref(false)
const saving = ref(false)
const local = ref(null)
watch(() => props.goal, () => { local.value = null })

const g = computed(() => ({ ...props.goal, ...(local.value || {}) }))
const target = computed(() => Number(g.value.targetAmount) || 0)
const hasGoal = computed(() => target.value > 0)
const current = computed(() => Number(g.value.currentAmount) || 0)
const annualReturn = computed(() => Number(g.value.annualReturn) || props.defaultReturn || 0)
const monthly = computed(() => Number(g.value.monthlyContribution) || 0)
const inflation = computed(() => (g.value.useInflation ? Number(g.value.inflationRate) || 7.5 : 0))

const projection = computed(() => {
  if (!hasGoal.value) return null
  const r = annualReturn.value / 12 / 100
  const start = new Date()
  const y0 = start.getFullYear()
  const targetAt = (m) => {
    if (!inflation.value) return target.value
    const d = new Date(start)
    d.setMonth(d.getMonth() + m)
    return target.value * Math.pow(1 + inflation.value / 100, d.getFullYear() - y0)
  }
  let cur = current.value
  let reached = cur >= targetAt(0) ? 0 : null
  const path = [cur]
  for (let m = 1; m <= 240 && reached == null; m++) {
    cur = cur * (1 + r) + monthly.value
    path.push(cur)
    if (cur >= targetAt(m)) reached = m
  }
  const date = reached == null ? null : new Date(start.getFullYear(), start.getMonth() + reached, 1)
  const monthAt = (m) => new Date(start.getFullYear(), start.getMonth() + m, 1)
  return {
    reached,
    date,
    targetThen: targetAt(reached ?? 240),
    path,
    targets: path.map((_, m) => targetAt(m)),
    labels: path.map((_, m) => monthAt(m)),
  }
})

/** цель с поправкой на инфляцию к году достижения (как в прежнем виджете) */
const effectiveTarget = computed(() => (inflation.value ? projection.value?.targetThen || target.value : target.value))
const progress = computed(() => (hasGoal.value ? Math.min(100, (current.value / (effectiveTarget.value || 1)) * 100) : 0))
const left = computed(() => Math.max(0, effectiveTarget.value - current.value))

const eta = computed(() => {
  const p = projection.value
  if (!p) return ''
  if (p.reached === 0) return 'Цель достигнута'
  if (p.reached == null) return 'Больше 20 лет при текущих взносах'
  const y = Math.floor(p.reached / 12)
  const m = p.reached % 12
  const parts = []
  if (y) parts.push(`${y} ${plural(y, 'год', 'года', 'лет')}`)
  if (m) parts.push(`${m} ${plural(m, 'месяц', 'месяца', 'месяцев')}`)
  return `через ${parts.join(' ')}`
})

// кольцо
const R = 54 // viewBox 120, толщина 6
const C = 2 * Math.PI * R
const drawn = ref(false)
onMounted(() => requestAnimationFrame(() => requestAnimationFrame(() => { drawn.value = true })))
const dash = computed(() => C * (1 - (drawn.value ? progress.value : 0) / 100))

async function save(newGoal) {
  if (!props.goal?.portfolioId || saving.value) return
  const annual = newGoal.annualReturn ?? props.defaultReturn ?? 0
  const data = {
    portfolioId: props.goal.portfolioId,
    targetAmount: newGoal.targetAmount,
    monthlyContribution: newGoal.monthlyContribution || 0,
    annualReturn: annual,
    useInflation: newGoal.useInflation || false,
    inflationRate: newGoal.inflationRate || 7.5,
  }
  saving.value = true
  try {
    await props.onSave(data)
    local.value = {
      targetAmount: data.targetAmount,
      monthlyContribution: data.monthlyContribution,
      annualReturn: data.annualReturn,
      useInflation: data.useInflation,
      inflationRate: data.inflationRate,
    }
    showModal.value = false
  } catch (err) {
    console.error('[GoalWidget] Ошибка при обновлении цели:', err)
  } finally {
    saving.value = false
  }
}

const fmtPct = (v) => `${Math.round(v)}%`
</script>

<template>
  <CvWidget v-bind="$attrs" title="Цель" :subtitle="hasGoal ? g.title : ''">
    <template #actions>
      <button v-if="hasGoal" type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" title="Изменить цель" @click="showModal = true">
        <Pencil :size="15" />
      </button>
    </template>

    <div v-if="hasGoal" class="gl">
      <div class="gl__top">
        <div class="gl__ring-wrap">
          <svg class="gl__ring" viewBox="0 0 120 120" aria-hidden="true">
            <circle cx="60" cy="60" :r="R" class="gl__track" />
            <circle
              cx="60"
              cy="60"
              :r="R"
              class="gl__arc"
              :class="{ 'is-done': projection?.reached === 0 }"
              :stroke-dasharray="C"
              :stroke-dashoffset="dash"
            />
          </svg>
          <div class="gl__center">
            <b><CvNumber :value="progress" :format="fmtPct" /></b>
          </div>
        </div>

        <div class="gl__facts">
          <b class="cv-num">{{ moneyCompact(current) }}</b>
          <span>из <span class="cv-num">{{ moneyCompact(effectiveTarget) }}</span>{{ inflation ? ' с инфляцией' : '' }}</span>
        </div>
      </div>

      <div class="gl__eta">
        <template v-if="projection?.reached > 0">
          <span>Прогноз</span>
          <b>{{ monthLong(projection.date) }}</b>
          <small>{{ eta }}</small>
        </template>
        <b v-else :class="{ 'cv-up': projection?.reached === 0 }">{{ eta }}</b>
      </div>

      <div v-if="projection?.path.length > 2" class="gl__path">
        <Sparkline
          :values="projection.path"
          :reference="projection.targets"
          reference-label="Цель"
          :labels="projection.labels"
          :format="moneyCompact"
          :label-format="monthLong"
          :mark-index="projection.reached ?? -1"
          :min-height="56"
          aria-label="Прогноз роста капитала до цели"
        />
      </div>
      <p class="gl__assume">
        {{ money(monthly) }}/мес · {{ pct(annualReturn, { sign: false }) }} годовых{{ inflation ? ` · инфляция ${pct(inflation, { sign: false })}` : '' }}
      </p>
    </div>

    <div v-else class="gl-empty">
      <div class="gl-empty__ic"><Target :size="22" :stroke-width="1.75" /></div>
      <b>Поставьте финансовую цель</b>
      <p>Укажите сумму и ежемесячный взнос — покажем, когда вы её достигнете.</p>
      <button type="button" class="cv-btn cv-btn--primary cv-btn--sm" @click="showModal = true">Задать цель</button>
    </div>

    <Teleport to="body">
      <EditGoalModal
        :show="showModal"
        :target-amount="target"
        :monthly-contribution="monthly"
        :annual-return="annualReturn"
        :use-inflation="!!g.useInflation"
        :inflation-rate="Number(g.inflationRate) || 7.5"
        @close="showModal = false"
        @save="save"
      />
    </Teleport>
  </CvWidget>
</template>

<style scoped>
.gl { display: flex; flex-direction: column; height: 100%; min-width: 0; }
.gl__top { display: flex; align-items: center; gap: 18px; }
.gl__ring-wrap { position: relative; width: 96px; height: 96px; flex: none; }
.gl__ring { width: 100%; height: 100%; transform: rotate(-90deg); }
.gl__track { fill: none; stroke: rgba(255, 255, 255, .06); stroke-width: 6; }
.gl__arc {
  fill: none; stroke: var(--cv-s1); stroke-width: 6; stroke-linecap: round;
  transition: stroke-dashoffset 1.6s var(--cv-ease) .15s;
}
.gl__arc.is-done { stroke: var(--cv-up); }
.gl__center { position: absolute; inset: 0; display: grid; place-items: center; }
.gl__center b { font-family: var(--cv-display); font-size: 22px; font-weight: 500; letter-spacing: -0.03em; color: var(--cv-ink); }

.gl__facts { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.gl__facts > b {
  font-family: var(--cv-display); font-size: 24px; font-weight: 500; letter-spacing: -0.03em; color: var(--cv-ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.gl__facts > span { font-size: 12.5px; color: var(--cv-mut); }

.gl__eta { display: flex; align-items: baseline; flex-wrap: wrap; gap: 4px 6px; margin-top: 22px; font-size: 12.5px; color: var(--cv-mut); }
.gl__eta b { font-size: 14px; font-weight: 550; color: var(--cv-ink); }
.gl__eta b.cv-up { color: var(--cv-up); }
.gl__eta small { flex-basis: 100%; font-size: 12px; color: var(--cv-dim); }

.gl__path { flex: 1; display: flex; flex-direction: column; min-height: 72px; margin-top: 16px; }
.gl__assume { margin-top: 12px; font-size: 11.5px; color: var(--cv-dim); }

.gl-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; padding: 12px 8px; text-align: center; }
.gl-empty__ic {
  display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: 6px; border-radius: 14px;
  color: var(--cv-accent-ink); background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line);
}
.gl-empty b { font-size: 15px; font-weight: 550; color: var(--cv-ink); }
.gl-empty p { max-width: 260px; margin-bottom: 8px; font-size: 13px; color: var(--cv-mut); }
</style>
