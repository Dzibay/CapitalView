<script setup>
import { computed, ref } from 'vue'
import { getCurrencySymbol } from '../../../utils/currencySymbols.js'
import Widget from '../base/Widget.vue'
import ValueChange from '../base/ValueChange.vue'
import DisplayModeToggle from '../base/DisplayModeToggle.vue'
import { ArrowUp, ArrowDown } from 'lucide-vue-next'

const props = defineProps({
  assets: { type: Array, required: true },
  direction: { type: String, default: 'up' }, // 'up' или 'down'
  title: { type: String, required: true }
})

const displayMode = ref('percent')

// 🔹 Считаем изменение в % и в валюте, фильтруем по направлению, сортируем и берём топ-4
// Сортировка зависит от выбранного режима (проценты или валюта)
const topAssets = computed(() => {
  if (!props.assets?.length) return []

  // Обрабатываем активы - вычисляем проценты и валюту для каждого
  const processed = props.assets
    .filter(a => {
      // Базовые проверки
      if (!a.last_price || a.daily_change === undefined || a.quantity <= 0) {
        return false
      }
      
      // Фильтруем по направлению изменения
      // Для 'up' - только активы с ростом (daily_change > 0)
      // Для 'down' - только активы с падением (daily_change < 0)
      if (props.direction === 'up') {
        return a.daily_change > 0
      } else {
        return a.daily_change < 0
      }
    })
    .map(a => {
      const total_value = a.last_price * a.quantity
      const change_percent = (a.daily_change / a.last_price) * 100
      const change_value = a.daily_change * a.quantity
      return { ...a, total_value, change_percent, change_value }
    })

  // Если после фильтрации нет активов нужного направления, возвращаем пустой массив
  if (processed.length === 0) {
    return []
  }

  // Сортируем в зависимости от выбранного режима отображения
  // Для 'up' - сортируем по убыванию (самые большие изменения сверху)
  // Для 'down' - сортируем по возрастанию (самые большие падения сверху, т.е. самые отрицательные)
  const sorted = props.direction === 'up'
    ? processed.sort((a, b) => {
        // Если режим процентов - сортируем по процентам
        if (displayMode.value === 'percent') {
          return b.change_percent - a.change_percent
        } else {
          // Если режим валюты - сортируем по валюте
          return b.change_value - a.change_value
        }
      })
    : processed.sort((a, b) => {
        // Для падений сортируем по возрастанию (самые отрицательные сверху)
        // Если режим процентов - сортируем по процентам
        if (displayMode.value === 'percent') {
          return a.change_percent - b.change_percent
        } else {
          // Если режим валюты - сортируем по валюте
          return a.change_value - b.change_value
        }
      })

  // Берем топ-4 после сортировки по выбранному критерию
  return sorted.slice(0, 4)
})
</script>

<template>
  <Widget :title="title" :icon="direction === 'up' ? ArrowUp : ArrowDown">
    <template #header>
      <DisplayModeToggle v-model="displayMode" />
    </template>
    
    <!-- Показываем пустое состояние, если нет активов нужного направления -->
    <div v-if="topAssets.length === 0" class="empty-state">
      <p class="empty-message">
        {{ direction === 'up' ? 'Нет активов с ростом за день' : 'Нет активов с падением за день' }}
      </p>
    </div>
    
    <!-- Показываем список активов, если они есть -->
    <ul v-else class="assets-list">
      <li v-for="asset in topAssets" :key="asset.asset_id" class="asset-item">
        <div class="asset-info">
          <span class="asset-name">{{ asset.name }}</span>
          <span class="asset-ticker">{{ asset.ticker }}</span>
        </div>

        <div class="asset-value">
          <span class="value">
            {{ asset.total_value.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            {{ getCurrencySymbol(asset.currency_ticker) }}
          </span>
          <div class="value-change-wrapper">
            <ValueChange 
              :value="asset.change_percent" 
              format="percent"
            />
            <span class="value-change-currency">
              ({{ asset.change_value >= 0 ? '+' : '' }}
              {{ asset.change_value.toFixed(2) }}
              {{ getCurrencySymbol(asset.currency_ticker) }})
            </span>
          </div>
        </div>
      </li>
    </ul>
  </Widget>
</template>

<style scoped>
.assets-list { 
  list-style: none;
}
.asset-item { 
  display: flex; 
  justify-content: space-between; 
  align-items: center; 
  padding: 0.75rem 0; 
}
.asset-item:not(:last-child) { 
  border-bottom: 1px solid #e5e7eb; 
}
.asset-name { 
  display: block; 
  font-weight: 500; 
  color: #1f2937; 
}
.asset-ticker { 
  font-size: 0.875rem; 
  color: #6b7280; 
}
.asset-value { 
  text-align: right; 
}
.value { 
  display: block; 
  font-weight: 400; 
}
.value-change-wrapper {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  justify-content: flex-end;
  margin-top: 0.25rem;
}
.value-change-currency {
  font-size: 0.875rem;
  color: #6b7280;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  min-height: 150px;
}

.empty-message {
  color: #6b7280;
  font-size: 0.875rem;
  text-align: center;
  margin: 0;
}

</style>
