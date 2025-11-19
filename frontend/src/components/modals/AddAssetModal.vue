<template>
  <div class="modal-overlay">
    <div class="modal-content">
      <h2>Добавить актив</h2>

      <div v-if="saving" class="modal-loading">Сохраняем...</div>

      <form v-else @submit.prevent="submitForm">
        <div>
          <label>Портфель:</label>
          <select v-model="form.portfolio_id" required>
            <option v-for="p in portfolios" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
        </div>

        <div class="asset-choice">
          <button
            type="button"
            :class="{ active: assetTypeChoice === 'system' }"
            @click="setAssetTypeChoice('system')"
          >
            Системный актив
          </button>
          <button
            type="button"
            :class="{ active: assetTypeChoice === 'custom' }"
            @click="setAssetTypeChoice('custom')"
          >
            Кастомный актив
          </button>
        </div>
        
        ---

        <div v-if="assetTypeChoice === 'system'">
          <div class="asset-search-block">
            <label>Актив:</label>

            <input
              type="text"
              v-model="searchQuery"
              placeholder="Введите название или тикер"
              @input="form.asset_id = null"
              required
            />

            <ul v-if="searchQuery && !form.asset_id" class="dropdown">
              <li
                v-for="a in filteredAssets"
                :key="a.id"
                @click="selectAsset(a)"
              >
                {{ a.name }} ({{ a.ticker || '—' }})
              </li>

              <li class="create-new" v-if="filteredAssets.length === 0">
                Актив не найден. Выберите "Кастомный актив" для создания нового.
              </li>
            </ul>

            <p v-if="form.asset_id" class="selected-asset">
                Выбран: <strong>{{ searchQuery }}</strong>
            </p>
          </div>
        </div>

        <div v-if="assetTypeChoice === 'custom'">
          <label>Название:</label>
          <input v-model="form.name" type="text" required />

          <label>Тикер:</label>
          <input v-model="form.ticker" type="text" />

          <label>Тип:</label>
          <select v-model="form.asset_type_id" required>
            <option
              v-for="t in referenceData.asset_types.filter(t => t.is_custom)"
              :key="t.id"
              :value="t.id"
            >
              {{ t.name }}
            </option>
          </select>

          <label>Валюта:</label>
          <select v-model="form.currency" required>
            <option v-for="c in referenceData.currencies" :key="c.id" :value="c.id">
              {{ c.ticker }}
            </option>
          </select>
        </div>
        
        ---

        <div>
          <label>Количество:</label>
          <input v-model.number="form.quantity" type="number" min="0" step="0.0001" required />
        </div>

        <div>
          <label>Средняя цена:</label>
          <input v-model.number="form.average_price" type="number" min="0" step="0.01" required />
        </div>
        <div>
          <label>Дата добавления:</label>
          <input v-model="form.date" type="date" required />
        </div>

        <div class="buttons">
          <button type="submit">Добавить</button>
          <button type="button" @click="$emit('close')">Закрыть</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed } from 'vue'

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
/* Ваши текущие стили */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  padding: 20px;
  width: 420px;
  border-radius: 8px;
  position: relative;
}
.modal-content form div {
  margin-bottom: 10px;
}
.buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
}
.modal-loading {
  text-align: center;
  padding: 40px 0;
  font-weight: bold;
  font-size: 16px;
}

.asset-search-block {
  position: relative;
}

.dropdown {
  position: absolute;
  background: white;
  border: 1px solid #ccc;
  width: 100%;
  max-height: 180px;
  overflow-y: auto;
  z-index: 10;
  margin-top: 2px;
  padding: 0;
  list-style: none;
  border-radius: 6px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); /* Добавляем тень */
}

.dropdown li {
  padding: 8px;
  cursor: pointer;
  border-bottom: 1px solid #eee; /* Разделитель */
}

.dropdown li:last-child {
    border-bottom: none;
}

.dropdown li:hover {
  background: #f0f0f0;
}

.dropdown .create-new {
  font-style: italic;
  color: #888;
  padding: 10px 8px;
  cursor: default;
}

.selected-asset {
    margin-top: 5px;
    padding: 5px 0;
    font-size: 14px;
    color: green;
}


/* Новые стили для переключателя */
.asset-choice {
  display: flex;
  margin-bottom: 15px;
  border: 1px solid #ccc;
  border-radius: 6px;
  overflow: hidden;
}

.asset-choice button {
  flex-grow: 1;
  padding: 10px;
  background: #f9f9f9;
  border: none;
  cursor: pointer;
  font-weight: bold;
  transition: background 0.3s, color 0.3s;
}

.asset-choice button:first-child {
  border-right: 1px solid #ccc;
}

.asset-choice button.active {
  background: #007bff; /* Основной цвет */
  color: white;
}

.asset-choice button:not(.active):hover {
    background: #e9ecef;
}

/* Стилизация input и select для лучшего вида */
.modal-content input[type="text"], 
.modal-content input[type="number"], 
.modal-content input[type="date"], 
.modal-content select {
    width: 100%;
    padding: 8px;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-sizing: border-box; /* Важно */
}

.modal-content label {
    display: block;
    margin-bottom: 4px;
    font-weight: 500;
}
</style>
