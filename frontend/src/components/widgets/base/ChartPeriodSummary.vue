<script setup>
import { computed } from 'vue'

const props = defineProps({
  startDate: { type: [String, Date], default: null },
  endDate: { type: [String, Date], default: null },
  changeValue: { type: Number, default: 0 },
  changePercent: { type: Number, default: 0 },
  formatValue: { type: Function, default: null },
  showDot: { type: Boolean, default: true }
})

const isPositive = computed(() => props.changeValue >= 0)

function fmtShortDate(raw) {
  if (!raw) return ''
  const d = new Date(raw)
  if (isNaN(d.getTime())) return ''
  const day = d.getDate()
  const month = d.toLocaleString('ru-RU', { month: 'short' }).replace('.', '')
  const year = String(d.getFullYear()).slice(-2)
  return `${day} ${month}. ${year}`
}

const dateRangeText = computed(() => {
  if (!props.startDate || !props.endDate) return ''
  return `${fmtShortDate(props.startDate)} - ${fmtShortDate(props.endDate)}`
})

const absChangeText = computed(() => {
  const abs = Math.abs(props.changeValue)
  const sign = props.changeValue >= 0 ? '+' : '−'
  const formatted = props.formatValue ? props.formatValue(abs) : abs.toLocaleString('ru-RU')
  return `${sign}${formatted} ₽`
})

const percentText = computed(() => {
  const pct = Math.abs(props.changePercent)
  return pct.toFixed(2) + '%'
})
</script>

<template>
  <div class="chart-period-summary">
    <span v-if="dateRangeText" class="cps-date-range">{{ dateRangeText }}</span>
    <span v-if="showDot" class="cps-dot" :class="{ 'cps-dot--positive': isPositive, 'cps-dot--negative': !isPositive }"></span>
    <span class="cps-change" :class="{ 'cps-change--positive': isPositive, 'cps-change--negative': !isPositive }">
      {{ absChangeText }}
      <span class="cps-pct">(
        <svg v-if="isPositive" class="cps-arrow" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 7L5 3L8 7" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <svg v-else class="cps-arrow" width="10" height="10" viewBox="0 0 10 10" fill="none">
          <path d="M2 3L5 7L8 3" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        {{ percentText }})</span>
    </span>
  </div>
</template>

<style scoped>
.chart-period-summary {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  white-space: nowrap;
}

.cps-date-range {
  font-size: 12px;
  font-weight: 400;
  color: var(--text-tertiary, #6b7280);
  letter-spacing: 0.01em;
}

.cps-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

.cps-dot--positive {
  background-color: #3b82f6;
}

.cps-dot--negative {
  background-color: #ef4444;
}

.cps-change {
  font-size: 13px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 2px;
}

.cps-change--positive {
  color: var(--positiveColor, #1cbd88);
}

.cps-change--negative {
  color: var(--negativeColor, #ef4444);
}

.cps-pct {
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 1px;
}

.cps-arrow {
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .chart-period-summary {
    gap: 4px;
  }
  .cps-date-range {
    font-size: 11px;
  }
  .cps-change {
    font-size: 12px;
  }
}

@media (max-width: 480px) {
  .cps-date-range {
    display: none;
  }
}
</style>
