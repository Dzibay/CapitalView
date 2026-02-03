<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <h2>Добавить актив</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div v-if="saving" class="modal-loading">
        <div class="spinner"></div>
        <span>Сохраняем...</span>
      </div>

      <form v-else @submit.prevent="submitForm" class="form-content">
        <!-- Портфель -->
        <div class="form-section">
          <CustomSelect
            v-model="form.portfolio_id"
            :options="portfolios"
            label="Портфель"
            placeholder="Выберите портфель"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <!-- Тип актива -->
        <div class="form-section">
          <label class="form-label">
            <span class="label-icon">📊</span>
            Тип актива
          </label>
          <div class="asset-choice">
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'system' }"
              @click="setAssetTypeChoice('system')"
            >
              <span class="choice-icon">🔍</span>
              Системный
            </button>
            <button
              type="button"
              :class="{ active: assetTypeChoice === 'custom' }"
              @click="setAssetTypeChoice('custom')"
            >
              <span class="choice-icon">✨</span>
              Кастомный
            </button>
          </div>
        </div>

        <!-- Информация об активе -->
        <div class="form-section">
          <div class="section-divider"></div>
          <div v-if="assetTypeChoice === 'system'" class="asset-search-block">
            <label class="form-label">
              <span class="label-icon">📈</span>
              Актив
            </label>
            <div class="search-wrapper">
              <span class="search-icon">🔍</span>
              <input
                type="text"
                v-model="searchQuery"
                placeholder="Поиск по названию или тикеру..."
                @input="form.asset_id = null"
                required
                class="form-input search-input"
              />
              <ul v-if="searchQuery && !form.asset_id" class="dropdown">
                <li
                  v-for="a in filteredAssets"
                  :key="a.id"
                  @click="selectAsset(a)"
                >
                  <span class="asset-name">{{ a.name }}</span>
                  <span class="asset-ticker">{{ a.ticker || '—' }}</span>
                </li>
                <li class="create-new" v-if="filteredAssets.length === 0">
                  <span class="empty-icon">🔍</span>
                  Актив не найден. Выберите "Кастомный" для создания нового.
                </li>
              </ul>
            </div>
            <div v-if="form.asset_id" class="selected-asset">
              <span class="check-icon">✓</span>
              <span>Выбран: <strong>{{ searchQuery }}</strong></span>
            </div>
          </div>

          <div v-if="assetTypeChoice === 'custom'" class="custom-asset-fields">
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📝</span>
                  Название
                </label>
                <input v-model="form.name" type="text" required class="form-input" />
              </div>
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">🏷️</span>
                  Тикер
                </label>
                <input v-model="form.ticker" type="text" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-field">
                <CustomSelect
                  v-model="form.asset_type_id"
                  :options="referenceData.asset_types.filter(t => t.is_custom)"
                  label="Тип"
                  placeholder="Выберите тип"
                  :show-empty-option="false"
                  option-label="name"
                  option-value="id"
                  :min-width="'100%'"
                  :flex="'none'"
                />
              </div>
              <div class="form-field">
                <CustomSelect
                  v-model="form.currency"
                  :options="referenceData.currencies"
                  label="Валюта"
                  placeholder="Выберите валюту"
                  :show-empty-option="false"
                  option-label="ticker"
                  option-value="id"
                  :min-width="'100%'"
                  :flex="'none'"
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Параметры покупки -->
        <div class="form-section">
          <div class="section-divider"></div>
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">🔢</span>
                Количество
              </label>
              <input v-model.number="form.quantity" type="number" min="0" step="0.0001" required class="form-input" />
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">💰</span>
                Средняя цена
              </label>
              <input v-model.number="form.average_price" type="number" min="0" step="0.01" required class="form-input" />
            </div>
          </div>
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">📅</span>
              Дата добавления
            </label>
            <input v-model="form.date" type="date" required class="form-input" />
          </div>
        </div>

        <div class="form-actions">
          <button type="button" class="btn btn-secondary" @click="$emit('close')">
            Отмена
          </button>
          <button type="submit" class="btn btn-primary">
            <span class="btn-icon">✓</span>
            Добавить актив
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'
import CustomSelect from '../CustomSelect.vue'

const props = defineProps({
  onSave: Function, // функция сохранения из родителя
  referenceData: Object,
  portfolios: Object
})

const emit = defineEmits(['close'])

const initialFormState = {
  portfolio_id: null,
  asset_id: null,
  asset_type_id: null,
  name: '',
  ticker: '',
  currency: null,
  quantity: 0,
  average_price: 0,
  date: new Date().toISOString().slice(0, 10)
}

const form = reactive({ ...initialFormState })
const saving = ref(false)           // индикатор сохранения
const searchQuery = ref("")
const assetTypeChoice = ref("system") // 'system' или 'custom' - по умолчанию системный


const resetAssetFields = () => {
    form.asset_id = null
    form.name = ''
    form.ticker = ''
    form.asset_type_id = null
    form.currency = null
    searchQuery.value = ''
}

const setAssetTypeChoice = (choice) => {
    assetTypeChoice.value = choice
    resetAssetFields() // Сбрасываем все поля актива при переключении
    
    // Устанавливаем обязательные значения по умолчанию для кастомного, если это 'custom'
    if (choice === 'custom') {
        // Устанавливаем первый кастомный тип и первую валюту, если они есть
        const firstCustomType = props.referenceData.asset_types.find(t => t.is_custom)
        if (firstCustomType) {
            form.asset_type_id = firstCustomType.id
        }
        if (props.referenceData.currencies.length > 0) {
            form.currency = props.referenceData.currencies[0].id
        }
    }
}


const submitForm = async () => {
  // Проверка для системного актива: должен быть выбран
  if (assetTypeChoice.value === 'system' && !form.asset_id) {
    alert('Пожалуйста, выберите системный актив из списка.');
    return;
  }
  
  // Для кастомного актива: заполняем asset_id как null, чтобы backend знал, что это новый
  if (assetTypeChoice.value === 'custom') {
      form.asset_id = null; 
  }
  
  if (!props.onSave) return
  saving.value = true
  try {
    await props.onSave({ ...form })  // ждём промис от родителя
    emit('close')
  } catch (err) {
    console.error(err)
    alert('Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}

const filteredAssets = computed(() => {
  if (!searchQuery.value) return props.referenceData.assets
  const q = searchQuery.value.toLowerCase()

  return props.referenceData.assets.filter(a =>
    a.name.toLowerCase().includes(q) ||
    (a.ticker || "").toLowerCase().includes(q)
  )
})

const selectAsset = (asset) => {
  form.asset_id = asset.id
  // Устанавливаем name, ticker и currency для системного актива, 
  // чтобы передать их на backend (если это требуется) и для отображения в поле поиска
  form.name = asset.name
  form.ticker = asset.ticker
  form.currency = asset.currency
  // Отображаем выбранное значение в поле поиска
  searchQuery.value = `${asset.name} (${asset.ticker || '—'})`
}

// Установка начального portfolio_id при загрузке
if (props.portfolios.length > 0) {
    form.portfolio_id = props.portfolios[0].id
}

// Инициализация выбора типа актива для полей кастомного актива
setAssetTypeChoice('system') 
</script>

<style scoped>
.modal-overlay {
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

.modal-content {
  background: white;
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  border-radius: 20px;
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
  padding: 18px 20px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.01em;
}

.close-btn {
  background: #f3f4f6;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
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
  width: 16px;
  height: 16px;
}

.form-content {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.form-content::-webkit-scrollbar {
  width: 6px;
}

.form-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.form-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.form-content::-webkit-scrollbar-thumb:hover {
  background: #9ca3af;
}

.form-section {
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 16px 0;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  font-size: 14px;
  opacity: 0.8;
}

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 12px;
  font-weight: 500;
  font-size: 14px;
  color: #6b7280;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.asset-search-block {
  position: relative;
}

.search-wrapper {
  position: relative;
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  font-size: 14px;
  color: #9ca3af;
  z-index: 1;
}

.search-input {
  padding-left: 36px !important;
}

.dropdown {
  position: absolute;
  background: white;
  border: 1px solid #e5e7eb;
  width: 100%;
  max-height: 180px;
  overflow-y: auto;
  z-index: 10;
  margin-top: 4px;
  padding: 4px 0;
  list-style: none;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.12), 0 4px 10px rgba(0,0,0,0.08);
  animation: slideDown 0.2s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dropdown li {
  padding: 10px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-left: 3px solid transparent;
}

.dropdown li:hover {
  background: #f3f4f6;
  border-left-color: #3b82f6;
  padding-left: 11px;
}

.asset-name {
  font-weight: 500;
  color: #111827;
  font-size: 13px;
}

.asset-ticker {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.dropdown .create-new {
  color: #9ca3af;
  padding: 12px 14px;
  cursor: default;
  text-align: center;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  flex-direction: column;
}

.empty-icon {
  font-size: 20px;
  opacity: 0.5;
}

.selected-asset {
  margin-top: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: #166534;
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.check-icon {
  width: 16px;
  height: 16px;
  background: #10b981;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  flex-shrink: 0;
}

.asset-choice {
  display: flex;
  gap: 8px;
  background: #f9fafb;
  padding: 4px;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
}

.asset-choice button {
  flex: 1;
  padding: 10px 14px;
  background: transparent;
  border: none;
  cursor: pointer;
  font-weight: 600;
  font-size: 13px;
  color: #6b7280;
  transition: all 0.2s ease;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.choice-icon {
  font-size: 14px;
}

.asset-choice button.active {
  background: white;
  color: #2563eb;
  box-shadow: 0 2px 4px rgba(0,0,0,0.08), 0 0 0 1px rgba(59,130,246,0.1);
  transform: translateY(-1px);
}

.asset-choice button:not(.active):hover {
  background: #f3f4f6;
  color: #374151;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
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
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.custom-asset-fields {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.btn {
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  display: flex;
  align-items: center;
  gap: 6px;
  letter-spacing: -0.01em;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  box-shadow: 0 2px 4px rgba(59,130,246,0.2);
}

.btn-primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(59,130,246,0.3);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
  transform: translateY(-1px);
}

.btn-secondary:active {
  transform: translateY(0);
}

.btn-icon {
  font-size: 14px;
  font-weight: 700;
}
</style>
