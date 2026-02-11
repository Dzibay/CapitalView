<script setup>
import { computed } from 'vue'
import Tooltip from '../Tooltip.vue'
import Widget from './Widget.vue'

const props = defineProps({
  returnPercent: {
    type: Number,
    default: 0
  },
  returnPercentOnInvested: {
    type: Number,
    default: 0
  },
  totalValue: {
    type: Number,
    default: 0
  },
  totalInvested: {
    type: Number,
    default: 0
  }
})

const formattedReturnPercent = computed(() => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format((props.returnPercent || 0) / 100)
})

const formattedReturnOnInvestedPercent = computed(() => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'percent',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format((props.returnPercentOnInvested || 0) / 100)
})
</script>

<template>
  <Widget title="Доходность">

    <div class="capital-value-with-change">
      <Tooltip content="Средневзвешенная годовая доходность всех активов в портфеле (на основе текущей стоимости активов и средней дивидендной доходности за 5 лет).
      Учитывается только дивидендная и купонная доходность" position="top">
        <div class="capital-values">
          {{ formattedReturnPercent }}
        </div>
      </Tooltip>
    </div>

    <p>
      <Tooltip content="Средневзвешенная годовая доходность на основе средней цены покупки активов" position="top">
        <span>{{ formattedReturnOnInvestedPercent }}</span>
      </Tooltip>
      на вложенный капитал
    </p>
  </Widget>
</template>

<style scoped>

.capital-value-with-change {
  margin: 15px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.value-change.positive {
  color: var(--positiveColor);
}
.value-change.negative {
  color: var(--negativeColor);
}

.capital-values {
  cursor: help;
}

</style>
