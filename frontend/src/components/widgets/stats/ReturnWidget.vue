<script setup>
import { Percent } from 'lucide-vue-next'
import StatCardWidget from '../base/StatCardWidget.vue'

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
</script>

<template>
  <StatCardWidget
    title="Доходность"
    :icon="Percent"
    :main-value="returnPercent"
    main-value-format="percent"
    main-value-tooltip="Средневзвешенная годовая доходность всех активов в портфеле (на основе текущей стоимости активов и средней дивидендной доходности за 5 лет). Учитывается только дивидендная и купонная доходность"
    :secondary-value="returnPercentOnInvested"
    secondary-format="percent"
    secondary-text=" на вложенный капитал"
    secondary-tooltip="Средневзвешенная годовая доходность на основе средней цены покупки активов"
  />
</template>
