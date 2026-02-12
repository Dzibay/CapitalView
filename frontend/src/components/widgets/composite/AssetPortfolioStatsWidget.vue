<script setup>
import { computed } from 'vue'
import Widget from '../base/Widget.vue'
import CustomSelect from '../../base/CustomSelect.vue'
import { formatCurrency } from '../../../utils/formatCurrency'
import ValueChange from '../base/ValueChange.vue'

const props = defineProps({
  portfolios: {
    type: Array,
    required: true
  },
  selectedPortfolioId: {
    type: Number,
    default: null
  }
})

const emit = defineEmits(['update:selectedPortfolioId'])

const selectedPortfolio = computed(() => {
  if (!props.selectedPortfolioId) return props.portfolios[0] || null
  return props.portfolios.find(p => p.portfolio_id === props.selectedPortfolioId) || props.portfolios[0] || null
})

const portfolioOptions = computed(() => {
  return props.portfolios.map(p => ({
    value: p.portfolio_id,
    label: p.portfolio_name
  }))
})

const handlePortfolioChange = (value) => {
  emit('update:selectedPortfolioId', value)
}
</script>

<template>
  <Widget title="Показатели в портфеле">
    <template #header>
      <CustomSelect
        v-if="portfolioOptions.length > 1"
        :modelValue="selectedPortfolioId || (portfolios[0]?.portfolio_id)"
        :options="portfolioOptions"
        label=""
        placeholder="Выберите портфель"
        :show-empty-option="false"
        option-label="label"
        option-value="value"
        :min-width="'180px'"
        :flex="'none'"
        @update:modelValue="handlePortfolioChange"
      />
    </template>

    <div v-if="selectedPortfolio" class="portfolio-stats">
      <div class="stat-item">
        <span class="stat-label">Портфель:</span>
        <span class="stat-value">{{ selectedPortfolio.portfolio_name }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Количество:</span>
        <span class="stat-value">{{ selectedPortfolio.quantity || 0 }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Средняя цена:</span>
        <span class="stat-value">{{ selectedPortfolio.average_price?.toFixed(2) || '-' }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Текущая цена:</span>
        <span class="stat-value">{{ selectedPortfolio.last_price?.toFixed(2) || '-' }}</span>
        <div v-if="selectedPortfolio.daily_change !== 0" class="stat-change">
          <ValueChange 
            :value="selectedPortfolio.daily_change" 
            :isPositive="selectedPortfolio.daily_change >= 0"
            format="currency"
          />
        </div>
      </div>

      <div class="stat-item">
        <span class="stat-label">Стоимость актива:</span>
        <span class="stat-value">{{ formatCurrency(selectedPortfolio.asset_value || 0) }}</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Инвестировано:</span>
        <span class="stat-value">{{ formatCurrency(selectedPortfolio.invested_value || 0) }}</span>
      </div>

      <div class="stat-item" :class="selectedPortfolio.profit_rub >= 0 ? 'profit' : 'loss'">
        <span class="stat-label">Прибыль/убыток:</span>
        <span class="stat-value">
          {{ selectedPortfolio.profit_rub >= 0 ? '+' : '' }}{{ formatCurrency(selectedPortfolio.profit_rub || 0) }}
        </span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Доля в портфеле:</span>
        <span class="stat-value">{{ selectedPortfolio.percentage_in_portfolio?.toFixed(2) || '0.00' }}%</span>
      </div>

      <div class="stat-item">
        <span class="stat-label">Общая стоимость портфеля:</span>
        <span class="stat-value">{{ formatCurrency(selectedPortfolio.portfolio_total_value || 0) }}</span>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>Нет данных о портфелях</p>
    </div>
  </Widget>
</template>

<style scoped>
.portfolio-stats {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f3f4f6;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-item.profit .stat-value {
  color: var(--positiveColor, #1CBD88);
}

.stat-item.loss .stat-value {
  color: var(--negativeColor, #EF4444);
}

.stat-label {
  color: #6b7280;
  font-size: 0.875rem;
  flex: 1;
}

.stat-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #111827;
  text-align: right;
}

.stat-change {
  font-size: 0.75rem;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  color: #6b7280;
  font-size: 0.875rem;
}
</style>
