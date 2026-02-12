<script setup>
import { computed } from 'vue'
import Widget from './Widget.vue'
import ValueChange from './ValueChange.vue'
import { formatCurrency } from '../../utils/formatCurrency'

const props = defineProps({
  asset: {
    type: Object,
    required: true
  },
  profitLoss: {
    type: Object,
    default: null
  },
  priceGrowth: {
    type: Object,
    default: null
  },
  totalProfit: {
    type: Object,
    default: null
  }
})
</script>

<template>
  <Widget title="Общая информация">
    <div class="asset-overview">
      <div class="overview-grid">
        <!-- Основные метрики -->
        <div class="metric-row">
          <div class="metric-item">
            <div class="metric-label">Текущая стоимость</div>
            <div class="metric-value primary">
              {{ formatCurrency(profitLoss?.currentValue || 0) }}
            </div>
            <div v-if="priceGrowth" class="metric-change">
              <ValueChange 
                :value="priceGrowth.percent" 
                :isPositive="priceGrowth.isPositive"
                format="percent"
              />
            </div>
          </div>

          <div class="metric-item" :class="profitLoss?.isProfit ? 'profit' : 'loss'">
            <div class="metric-label">Прибыль/убыток</div>
            <div class="metric-value">
              {{ profitLoss?.isProfit ? '+' : '' }}{{ formatCurrency(profitLoss?.profit || 0) }}
            </div>
            <div v-if="profitLoss" class="metric-change">
              <ValueChange 
                :value="profitLoss.profitPercent" 
                :isPositive="profitLoss.isProfit"
                format="percent"
              />
            </div>
          </div>
        </div>

        <div class="metric-row">
          <div class="metric-item">
            <div class="metric-label">Инвестировано</div>
            <div class="metric-value">{{ formatCurrency(profitLoss?.invested || 0) }}</div>
            <div class="metric-subtitle">Средняя цена: {{ asset.average_price?.toFixed(2) || '-' }}</div>
          </div>

          <div class="metric-item" v-if="totalProfit">
            <div class="metric-label">Общая прибыль</div>
            <div class="metric-value" :class="totalProfit.isProfit ? 'profit' : 'loss'">
              {{ totalProfit.isProfit ? '+' : '' }}{{ formatCurrency(totalProfit.total) }}
            </div>
            <div class="metric-subtitle">
              Нереализ.: {{ formatCurrency(totalProfit.unrealized) }} | 
              Реализ.: {{ formatCurrency(totalProfit.realized) }} | 
              Выплаты: {{ formatCurrency(totalProfit.payouts) }}
            </div>
          </div>
        </div>

        <!-- Детальная информация -->
        <div class="details-section">
          <div class="detail-item">
            <span class="detail-label">Количество:</span>
            <span class="detail-value">{{ asset.quantity || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Текущая цена:</span>
            <span class="detail-value">{{ asset.last_price?.toFixed(2) || '-' }}</span>
          </div>
          <div class="detail-item" v-if="asset.leverage && asset.leverage > 1">
            <span class="detail-label">Плечо:</span>
            <span class="detail-value">×{{ asset.leverage }}</span>
          </div>
        </div>
      </div>
    </div>
  </Widget>
</template>

<style scoped>
.asset-overview {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  height: 100%;
}

.overview-grid {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

.metric-item {
  padding: 1rem;
  background: transparent;
  border-radius: 0;
  border-bottom: 1px solid #f3f4f6;
}

.metric-item.profit {
  border-left: 4px solid var(--positiveColor, #1CBD88);
}

.metric-item.loss {
  border-left: 4px solid var(--negativeColor, #EF4444);
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.metric-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin-bottom: 0.5rem;
  line-height: 1.2;
}

.metric-value.primary {
  color: #3b82f6;
}

.metric-value.profit {
  color: var(--positiveColor, #1CBD88);
}

.metric-value.loss {
  color: var(--negativeColor, #EF4444);
}

.metric-change {
  font-size: 0.875rem;
  font-weight: 500;
}

.metric-subtitle {
  font-size: 0.75rem;
  color: #9ca3af;
  margin-top: 0.5rem;
  line-height: 1.4;
}

.details-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-label {
  font-size: 0.75rem;
  color: #6b7280;
  font-weight: 500;
}

.detail-value {
  font-size: 1rem;
  font-weight: 600;
  color: #111827;
}

@media (max-width: 768px) {
  .metric-row {
    grid-template-columns: 1fr;
  }
}
</style>
