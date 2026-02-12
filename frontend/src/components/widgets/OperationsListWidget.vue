<script setup>
import { computed } from 'vue'
import Widget from './Widget.vue'
import { formatCurrency } from '../../utils/formatCurrency'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  title: {
    type: String,
    default: 'Операции'
  },
  operations: {
    type: Array,
    default: () => []
  },
  columns: {
    type: Array,
    default: () => ['date', 'type', 'quantity', 'price', 'amount']
  },
  // Функция для получения типа операции
  getOperationType: {
    type: Function,
    default: (op) => op.operationType || op.type || 'other'
  },
  // Функция для получения метки типа операции
  getOperationTypeLabel: {
    type: Function,
    default: (op) => {
      const type = op.operationType || op.type || ''
      if (typeof type === 'number') {
        if (type === 1) return 'Покупка'
        if (type === 2) return 'Продажа'
        if (type === 3) return 'Дивиденды'
        if (type === 4) return 'Купоны'
      }
      if (typeof type === 'string') {
        const t = type.toLowerCase()
        if (t.includes('покуп') || t.includes('buy')) return 'Покупка'
        if (t.includes('прод') || t.includes('sell')) return 'Продажа'
        if (t.includes('див') || t.includes('div')) return 'Дивиденды'
        if (t.includes('купон') || t.includes('coupon')) return 'Купоны'
      }
      return 'Операция'
    }
  },
  // Функция для получения класса типа операции
  getOperationTypeClass: {
    type: Function,
    default: (op) => {
      const type = op.operationType || op.type || ''
      if (typeof type === 'number') {
        if (type === 1) return 'buy'
        if (type === 2) return 'sell'
        if (type === 3) return 'dividend'
        if (type === 4) return 'coupon'
      }
      if (typeof type === 'string') {
        const t = type.toLowerCase()
        if (t.includes('покуп') || t.includes('buy')) return 'buy'
        if (t.includes('прод') || t.includes('sell')) return 'sell'
        if (t.includes('див') || t.includes('div')) return 'dividend'
        if (t.includes('купон') || t.includes('coupon')) return 'coupon'
      }
      return 'other'
    }
  },
  // Функция для форматирования даты
  formatDate: {
    type: Function,
    default: (date) => {
      if (!date) return '-'
      return new Date(date).toLocaleDateString('ru-RU')
    }
  }
})

const sortedOperations = computed(() => {
  return [...props.operations].sort((a, b) => {
    const dateA = new Date(a.date || 0)
    const dateB = new Date(b.date || 0)
    return dateB - dateA
  })
})
</script>

<template>
  <Widget :title="title">
    <div v-if="sortedOperations.length > 0" class="operations-table">
      <table>
        <thead>
          <tr>
            <th v-if="columns.includes('date')">Дата</th>
            <th v-if="columns.includes('type')">Тип</th>
            <th v-if="columns.includes('quantity')">Количество</th>
            <th v-if="columns.includes('price')">Цена</th>
            <th v-if="columns.includes('amount')">Сумма</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="op in sortedOperations" :key="op.id">
            <td v-if="columns.includes('date')">{{ formatDate(op.date) }}</td>
            <td v-if="columns.includes('type')">
              <span :class="['badge', 'badge-' + getOperationTypeClass(op)]">
                {{ getOperationTypeLabel(op) }}
              </span>
            </td>
            <td v-if="columns.includes('quantity')">
              {{ op.quantity !== null && op.quantity !== undefined ? op.quantity : '-' }}
            </td>
            <td v-if="columns.includes('price')">
              {{ op.price !== null && op.price !== undefined ? op.price.toFixed(2) : '-' }}
            </td>
            <td v-if="columns.includes('amount')">{{ formatCurrency(op.amount || 0) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <EmptyState v-else message="Нет операций" />
  </Widget>
</template>

<style scoped>
.operations-table {
  width: 100%;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f9fafb;
}

th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.75rem;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e5e7eb;
}

tbody tr {
  border-bottom: 1px solid #f3f4f6;
  transition: background-color 0.15s;
}

tbody tr:hover {
  background-color: #f9fafb;
}

td {
  padding: 0.75rem 1rem;
  font-size: 0.875rem;
  color: #111827;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge-buy {
  background: #dcfce7;
  color: #16a34a;
}

.badge-sell {
  background: #fee2e2;
  color: #ef4444;
}

.badge-dividend {
  background: #dbeafe;
  color: #2563eb;
}

.badge-coupon {
  background: #cffafe;
  color: #0891b2;
}

.badge-other {
  background: #f3f4f6;
  color: #6b7280;
}
</style>
