<template>
  <div class="modal-overlay">
    <div class="modal-content">
      <h2>Добавить актив</h2>

      <!-- Загрузка справочников -->
      <div v-if="loadingReference" class="modal-loading">Загрузка данных...</div>

      <!-- Сохраняем актив -->
      <div v-else-if="saving" class="modal-loading">Сохраняем...</div>

      <!-- Форма добавления -->
      <form v-else @submit.prevent="submitForm">
        <div>
          <label>Портфель:</label>
          <select v-model="form.portfolio_id" required>
            <option v-for="p in portfolios" :key="p.id" :value="p.id">
              {{ p.name }}
            </option>
          </select>
        </div>

        <div>
          <label>Актив:</label>
          <select v-model="form.asset_id">
            <option value="">Создать новый</option>
            <option v-for="a in referenceData.assets" :key="a.id" :value="a.id">
              {{ a.name }} ({{ a.ticker || '—' }})
            </option>
          </select>
        </div>

        <!-- Поля для нового актива -->
        <div v-if="!form.asset_id">
          <label>Название:</label>
          <input v-model="form.name" type="text" required />

          <label>Тикер:</label>
          <input v-model="form.ticker" type="text" />

          <label>Тип:</label>
          <select v-model="form.asset_type_id" required>
            <option v-for="t in referenceData.asset_types" :key="t.id" :value="t.id">
              {{ t.name }}
            </option>
          </select>

          <label>Валюта:</label>
          <select v-model="form.currency" required>
            <option v-for="c in referenceData.currencies" :key="c.id" :value="c.id">
              {{ c.code }}
            </option>
          </select>
        </div>

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
import { reactive, ref, onMounted, inject } from 'vue'
import assetsService from '../services/assetsService.js'

const props = defineProps({
  onSave: Function // функция сохранения из родителя
})

const portfolios = inject('portfolios')
const emit = defineEmits(['close'])

const form = reactive({
  portfolio_id: null,
  asset_id: null,
  asset_type_id: null,
  name: '',
  ticker: '',
  quantity: 0,
  average_price: 0,
  currency: null,
  date: new Date().toISOString().slice(0, 10)
})

const referenceData = ref({ asset_types: [], currencies: [], assets: [] })
const loadingReference = ref(true) // индикатор загрузки справочников
const saving = ref(false)           // индикатор сохранения

onMounted(async () => {
  try {
    const res = await assetsService.getReferenceData()
    referenceData.value = res
  } catch (err) {
    console.error('Ошибка загрузки справочников:', err)
  } finally {
    loadingReference.value = false
  }
})

const submitForm = async () => {
  if (!props.onSave) return
  saving.value = true
  try {
    await props.onSave({ ...form })  // ждём промис от родителя
    emit('close')
  } catch (err) {
    console.error(err)
    alert('Ошибка при сохранении')
  } finally {
    saving.value = false
  }
}
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
</style>
