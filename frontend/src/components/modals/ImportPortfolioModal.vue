<script setup>
import { ref } from 'vue'

const props = defineProps({
  onImport: Function,
  portfolios: Array
})
const emit = defineEmits(['close'])

const token = ref('t.b7cVknEoyjXW6FG39o4woo12yzoCAKsTwYgT0LqYFvNEH0hC5IGSMtLxVEwGfwXOv048FR5kGmxMeFpEM-GCRQ')
const portfolioId = ref(null)
const portfolioName = ref('Тинькофф')
const loading = ref(false)
const error = ref('')

const handleImport = async () => {
  if (!token.value) {
    error.value = 'Введите токен'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await props.onImport({
      broker_id: 1,
      token: token.value,
      portfolioId: portfolioId.value,
      portfolio_name: portfolioName.value
    })
    emit('close')
  } catch (e) {
    error.value = e.message || 'Ошибка импорта'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="modal-overlay">
    <div class="modal-content">
      <h3>Импорт портфеля из Tinkoff</h3>
      
      <label>Токен API:</label>
      <input v-model="token" type="text" placeholder="Введите токен" />

      <label>Портфель:</label>
      <select v-model="portfolioId" required>
        <option value="">Создать новый</option>
        <option v-for="p in portfolios" :key="p.id" :value="p.id">
            {{ p.name }}
        </option>
      </select>

      <input v-if="!portfolioId" v-model="portfolioName" type="text" placeholder="Название нового портфеля" /><br>

      <div v-if="error" class="error">{{ error }}</div>

      <button @click="handleImport" :disabled="loading">
        {{ loading ? 'Импортируем...' : 'Импортировать' }}
      </button>
      <button @click="$emit('close')" :disabled="loading">Отмена</button>
    </div>
  </div>
</template>

<style>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  padding: 20px;
  border-radius: 8px;
  min-width: 300px;
}
.error {
  color: red;
  margin-top: 8px;
}
input {
  width: 100%;
  margin-bottom: 8px;
  padding: 4px 8px;
}
button {
  margin-right: 8px;
  padding: 6px 12px;
}
</style>
