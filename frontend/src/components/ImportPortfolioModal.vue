<script setup>
import { ref, inject } from 'vue'

const props = defineProps({
  onImport: Function,
  portfolios: Array
})
const emit = defineEmits(['close'])

const token = ref('t.Wwc9-ETWh-SiWqphi_F3TQ-U7TZNsuhUryWHiDWu1vqvq19ypX7I9il3E9PlfZgKyt4gPiHrXD4RjyNiVUHzzA')
const portfolioId = ref(null)
const portfolioName = ref('Акции-Тинькофф')
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
        <option v-for="p in portfolios" :key="p.portfolio_id" :value="p.portfolio_id">
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
