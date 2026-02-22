<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Button } from '../base'
import assetsService from '../../services/assetsService'

const props = defineProps({
  asset: Object,
  onSubmit: Function // универсальный обработчик добавления транзакции
})

const emit = defineEmits(['close'])

// Режим: 'single' - одна цена, 'dynamic' - динамика цены
const mode = ref('single')

// Поля для одиночной цены
const price = ref(0)
const date = ref(new Date().toISOString().slice(0, 10))

// Поля для динамики цены
// Инициализируем начальную цену из average_price актива, если доступна
const startPrice = ref(0)
const endPrice = ref(0)
const startDate = ref('')
const endDate = ref(new Date().toISOString().slice(0, 10))
const interval = ref('month') // 'day', 'week', 'month'

const error = ref('')
const saving = ref(false)

// Инициализация значений по умолчанию из данных актива
const initializeDefaults = () => {
  if (props.asset) {
    // Начальная цена = цена первой покупки (first_purchase_price) или средняя цена покупки (average_price)
    if (props.asset.first_purchase_price && props.asset.first_purchase_price > 0) {
      startPrice.value = props.asset.first_purchase_price
    } else if (props.asset.average_price && props.asset.average_price > 0) {
      startPrice.value = props.asset.average_price
    }
    
    // Начальная дата = дата первой покупки (first_purchase_date)
    if (props.asset.first_purchase_date) {
      const date = new Date(props.asset.first_purchase_date)
      if (!isNaN(date.getTime())) {
        startDate.value = date.toISOString().slice(0, 10)
      }
    }
  }
}

// Инициализируем при монтировании и при изменении asset
onMounted(() => {
  initializeDefaults()
})

watch(() => props.asset, () => {
  initializeDefaults()
}, { immediate: true, deep: true })

// Вычисляем количество точек для динамики
const pricePointsCount = computed(() => {
  if (mode.value !== 'dynamic' || !startDate.value || !endDate.value) return 0
  
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  if (end < start) return 0
  
  const diffTime = Math.abs(end - start)
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  
  switch (interval.value) {
    case 'day':
      return diffDays + 1
    case 'week':
      return Math.ceil(diffDays / 7) + 1
    case 'month':
      // Приблизительный расчет месяцев
      const months = (end.getFullYear() - start.getFullYear()) * 12 + (end.getMonth() - start.getMonth())
      return months + 1
    default:
      return 0
  }
})

// Генерируем список цен для динамики (линейная интерполяция)
const generatePricePoints = () => {
  if (!startDate.value || !endDate.value || startPrice.value <= 0 || endPrice.value <= 0) {
    return []
  }
  
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  if (end < start) return []
  
  const points = []
  const priceDiff = endPrice.value - startPrice.value
  
  // Определяем шаг даты в зависимости от интервала
  let dateStep = 1
  switch (interval.value) {
    case 'day':
      dateStep = 1
      break
    case 'week':
      dateStep = 7
      break
    case 'month':
      dateStep = 30 // Приблизительно
      break
  }
  
  let currentDate = new Date(start)
  let pointIndex = 0
  const totalDays = Math.ceil((end - start) / (1000 * 60 * 60 * 24))
  const totalPoints = pricePointsCount.value
  
  while (currentDate <= end && pointIndex < totalPoints) {
    // Линейная интерполяция
    const daysPassed = Math.ceil((currentDate - start) / (1000 * 60 * 60 * 24))
    const progress = totalDays > 0 ? daysPassed / totalDays : 0
    const interpolatedPrice = startPrice.value + (priceDiff * progress)
    
    points.push({
      date: currentDate.toISOString().slice(0, 10),
      price: Math.max(0.01, parseFloat(interpolatedPrice.toFixed(2))) // Минимум 0.01
    })
    
    // Переходим к следующей дате
    if (interval.value === 'month') {
      currentDate.setMonth(currentDate.getMonth() + 1)
    } else {
      currentDate.setDate(currentDate.getDate() + dateStep)
    }
    pointIndex++
  }
  
  // Убеждаемся, что последняя точка - это конечная дата и цена
  if (points.length > 0) {
    const lastPoint = points[points.length - 1]
    if (lastPoint.date !== endDate.value) {
      points.push({
        date: endDate.value,
        price: endPrice.value
      })
    } else {
      points[points.length - 1].price = endPrice.value
    }
  }
  
  return points
}

const handleSubmit = async () => {
  error.value = ''
  
  if (mode.value === 'single') {
    if (!price.value || price.value <= 0) {
      error.value = 'Введите цену'
      return
    }
    
    try {
      saving.value = true
      await props.onSubmit({
        asset_id: props.asset.asset_id,
        price: price.value,
        date: date.value
      })
      emit('close')
    } catch (e) {
      error.value = 'Ошибка при добавлении цены актива: ' + (e.message || e)
    } finally {
      saving.value = false
    }
  } else {
    // Режим динамики
    if (!startPrice.value || startPrice.value <= 0) {
      error.value = 'Введите начальную цену'
      return
    }
    if (!endPrice.value || endPrice.value <= 0) {
      error.value = 'Введите конечную цену'
      return
    }
    if (!startDate.value) {
      error.value = 'Выберите начальную дату'
      return
    }
    if (!endDate.value) {
      error.value = 'Выберите конечную дату'
      return
    }
    if (new Date(endDate.value) < new Date(startDate.value)) {
      error.value = 'Конечная дата должна быть позже начальной'
      return
    }
    
    try {
      saving.value = true
      const pricePoints = generatePricePoints()
      
      if (pricePoints.length === 0) {
        error.value = 'Не удалось сгенерировать точки цен'
        return
      }
      
      // Используем batch endpoint
      const response = await assetsService.addPricesBatch(props.asset.asset_id, pricePoints)
      
      if (response.success) {
        emit('close')
      } else {
        error.value = response.error || 'Ошибка при добавлении цен'
      }
    } catch (e) {
      error.value = 'Ошибка при добавлении цен: ' + (e.message || e)
    } finally {
      saving.value = false
    }
  }
}

// При переключении режима устанавливаем начальную дату, если она не установлена
const onModeChange = () => {
  if (mode.value === 'dynamic') {
    // Если дата не установлена, инициализируем значения по умолчанию
    if (!startDate.value) {
      initializeDefaults()
    }
    // Если начальная цена не установлена, используем first_purchase_price или average_price
    if (!startPrice.value) {
      if (props.asset?.first_purchase_price && props.asset.first_purchase_price > 0) {
        startPrice.value = props.asset.first_purchase_price
      } else if (props.asset?.average_price && props.asset.average_price > 0) {
        startPrice.value = props.asset.average_price
      }
    }
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Добавление цены актива</h2>
        <button class="close-btn" @click="emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <form @submit.prevent="handleSubmit" class="form-content">
        <div class="form-section">
          <div class="asset-info">
            <span class="asset-icon">📈</span>
            <div>
              <strong>{{ asset.name }}</strong>
              <span class="ticker">({{ asset.ticker }})</span>
            </div>
          </div>
        </div>

        <!-- Переключатель режима -->
        <div class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <span class="label-icon">⚙️</span>
            Режим добавления
          </label>
          <div class="mode-switch">
            <button
              type="button"
              :class="['mode-btn', { active: mode === 'single' }]"
              @click="mode = 'single'"
            >
              Одна цена
            </button>
            <button
              type="button"
              :class="['mode-btn', { active: mode === 'dynamic' }]"
              @click="mode = 'dynamic'; onModeChange()"
            >
              Динамика цены
            </button>
          </div>
        </div>

        <!-- Режим: одна цена -->
        <template v-if="mode === 'single'">
          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">💰</span>
                  Цена (₽)
                </label>
                <input type="number" v-model.number="price" min="0" step="0.01" class="form-input" required />
              </div>
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📅</span>
                  Дата
                </label>
                <input type="date" v-model="date" required class="form-input" />
              </div>
            </div>
          </div>
        </template>

        <!-- Режим: динамика цены -->
        <template v-else>
          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">💰</span>
                  Начальная цена (₽)
                </label>
                <input type="number" v-model.number="startPrice" min="0" step="0.01" class="form-input" required />
              </div>
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">💰</span>
                  Конечная цена (₽)
                </label>
                <input type="number" v-model.number="endPrice" min="0" step="0.01" class="form-input" required />
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📅</span>
                  Начальная дата
                </label>
                <input type="date" v-model="startDate" required class="form-input" />
              </div>
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📅</span>
                  Конечная дата
                </label>
                <input type="date" v-model="endDate" required class="form-input" />
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">🔄</span>
                Интервал
              </label>
              <select v-model="interval" class="form-input">
                <option value="day">Ежедневно</option>
                <option value="week">Еженедельно</option>
                <option value="month">Ежемесячно</option>
              </select>
            </div>
            <div v-if="pricePointsCount > 0" class="info-box">
              <span class="info-icon">ℹ️</span>
              <span>Будет создано <strong>{{ pricePointsCount }}</strong> записей цен</span>
            </div>
          </div>
        </template>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="emit('close')" :disabled="saving">
            Отмена
          </button>
          <button type="submit" class="btn btn-primary" :disabled="saving">
            <span class="btn-icon">✓</span>
            {{ saving ? 'Сохранение...' : (mode === 'single' ? 'Добавить' : 'Создать динамику') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
  padding: 16px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 600px;
  max-height: 90vh;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes slideUp {
  from {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  background: linear-gradient(to bottom, #ffffff, #fafafa);
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.02em;
}

.close-btn {
  background: #f3f4f6;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
  transform: scale(1.05);
}

.close-btn:active {
  transform: scale(0.95);
}

.close-btn svg {
  width: 18px;
  height: 18px;
}

.form-content {
  padding: 24px;
  overflow-y: auto;
  flex: 1;
}

.form-content::-webkit-scrollbar {
  width: 8px;
}

.form-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.form-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.form-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.form-section {
  margin-bottom: 24px;
}

.form-section:last-of-type {
  margin-bottom: 20px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 20px 0;
}

.asset-info {
  padding: 14px 18px;
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 15px;
}

.asset-icon {
  font-size: 20px;
  opacity: 0.9;
}

.asset-info strong {
  color: #111827;
  font-weight: 600;
}

.ticker {
  color: #6b7280;
  margin-left: 8px;
  font-size: 14px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 14px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  font-size: 16px;
  opacity: 0.85;
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 12px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: #fff;
}

.form-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.mode-switch {
  display: flex;
  gap: 8px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 12px;
}

.mode-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.5);
  color: #374151;
}

.mode-btn.active {
  background: white;
  color: #111827;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #1e40af;
}

.info-icon {
  font-size: 16px;
}

.info-box strong {
  color: #1e3a8a;
  font-weight: 600;
}

.error {
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.error::before {
  content: '⚠️';
  font-size: 16px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding-top: 20px;
  margin-top: 12px;
  border-top: 1px solid #f3f4f6;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover:not(:disabled) {
  background: #e5e7eb;
}

.btn-primary {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  box-shadow: 0 2px 4px rgba(59, 130, 246, 0.2);
}

.btn-primary:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
  box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-icon {
  font-size: 16px;
}
</style>
