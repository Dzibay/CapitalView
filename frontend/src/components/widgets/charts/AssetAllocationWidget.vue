<script setup>
import { computed, inject, onMounted, ref, unref, watch, useSlots } from 'vue'
import { PieChart } from 'lucide-vue-next'
import DoughnutChart from '../../charts/DoughnutChart.vue'
import Widget from '../base/Widget.vue'
import EmptyState from '../base/EmptyState.vue'
import { LANDING_DASH_REVEAL_KEY } from '../../../constants/landingDashboardReveal'

// Props
const props = defineProps({
  title: {
    type: String,
    default: 'Распределение активов'
  },
  icon: {
    type: [Object, Function],
    default: () => PieChart
  },
  assetAllocation: {
    type: Object,
    default: null
  },
  /** Подпись суммы в центре кольца (по умолчанию — formatCurrency в RUB) */
  formatCenterValue: {
    type: Function,
    default: null
  },
  /** Показать EmptyState, если данных для графика нет */
  emptyMessage: {
    type: String,
    default: null
  },
  scrollReveal: {
    type: Boolean,
    default: false
  },
  landingRevealRef: {
    type: [Object, Boolean],
    default: null
  }
})

const slots = useSlots()

const injectedLandingReveal = inject(LANDING_DASH_REVEAL_KEY, null)

function revealSource() {
  return props.landingRevealRef ?? injectedLandingReveal
}
const doughnutRemountKey = ref(0)

function bumpDoughnut() {
  doughnutRemountKey.value += 1
}

watch(
  () => {
    if (!props.scrollReveal) return null
    const src = revealSource()
    if (src == null) return false
    return unref(src)
  },
  (ok) => {
    if (props.scrollReveal && ok) bumpDoughnut()
  }
)

onMounted(() => {
  const src = revealSource()
  if (props.scrollReveal && src != null && unref(src)) bumpDoughnut()
})

function formatWholePercent(value) {
  const n = Math.round(Number(value))
  if (!Number.isFinite(n)) return '0'
  return n.toLocaleString('ru-RU')
}

const formatCurrency = (value) => {
  const n = Number(value)
  const opts = { style: 'currency', currency: 'RUB', minimumFractionDigits: 0, maximumFractionDigits: 0 }
  if (!Number.isFinite(n)) {
    return (0).toLocaleString('ru-RU', opts)
  }
  return n.toLocaleString('ru-RU', opts)
}

function formatCenterDisplay(value) {
  if (props.formatCenterValue) return props.formatCenterValue(value)
  return formatCurrency(value)
}

const doughnutLabels = computed(() => props.assetAllocation?.labels ?? [])
const doughnutValues = computed(() => props.assetAllocation?.datasets?.[0]?.data ?? [])
const doughnutColors = computed(
  () => props.assetAllocation?.datasets?.[0]?.backgroundColor ?? []
)

const total = computed(() => {
  if (!props.assetAllocation?.datasets?.length) return 0
  return props.assetAllocation.datasets[0].data.reduce((a, b) => a + (Number(b) || 0), 0)
})

const hasRenderableData = computed(() => {
  const a = props.assetAllocation
  if (!a?.labels?.length || !a.datasets?.[0]?.data?.length) return false
  return total.value > 0
})
</script>

<template>
  <Widget :title="title" :icon="icon">
    <template v-if="slots.header" #header>
      <slot name="header" />
    </template>
    <div v-if="hasRenderableData" class="allocation-container">
      <div class="chart-wrapper">
        <DoughnutChart
          :key="doughnutRemountKey"
          fill-parent
          :labels="doughnutLabels"
          :values="doughnutValues"
          :colors="doughnutColors"
          :format-value="formatCenterDisplay"
          :format-percentage="formatWholePercent"
          :show-legend="false"
          cutout="75%"
        />
      </div>

      <div class="legends">
        <div v-for="(label, i) in assetAllocation.labels" :key="label" class="legend-item">
          <span class="legend-color" :style="{ backgroundColor: assetAllocation.datasets[0].backgroundColor[i] }"></span>
          <span class="legend-label">{{ label }}</span>
        </div>
      </div>
    </div>
    <EmptyState v-else-if="emptyMessage" :message="emptyMessage" />
  </Widget>
</template>

<style scoped>

.allocation-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-width: 0;
  flex: 1;
  min-height: 0;
}

.chart-wrapper {
  position: relative;
  width: 280px;
  height: 280px;
  max-width: 100%;
  flex-shrink: 0;
}

.legends {
  margin-top: 20px;
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  font-size: var(--text-caption-size);
  color: var(--text-tertiary);
}

.legend-item {
  display: flex;
  align-items: center;
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
}

@media (max-width: 1200px) {
  .chart-wrapper {
    width: 240px;
    height: 240px;
  }
  .legends {
    margin-top: 14px;
    gap: 12px;
  }
}

@media (max-width: 768px) {
  .chart-wrapper {
    width: 200px;
    height: 200px;
  }
  .legends {
    margin-top: 12px;
    gap: 10px;
  }
}

@media (max-width: 480px) {
  .chart-wrapper {
    width: 180px;
    height: 180px;
  }
  .legends {
    margin-top: 10px;
    gap: 8px;
  }
}
</style>
