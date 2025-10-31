<script setup>
import { ref } from 'vue'

const props = defineProps({
  asset: Object,
  onSubmit: Function // универсальный обработчик добавления транзакции
})

const emit = defineEmits(['close'])

const price = ref(0)
const date = ref(new Date().toISOString().slice(0, 10))
const error = ref('')

const handleSubmit = async () => {
  if (!price.value || price.value <= 0) {
    error.value = 'Введите цену'
    return
  }

  try {
    await props.onSubmit({
      asset_id: props.asset.asset_id,
      price: price.value,
      date: date.value
    })
    emit('close')
  } catch (e) {
    error.value = 'Ошибка при добавлении цены актива: ' + e.message
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <h3>Добавление цены актива</h3>
      <p><strong>{{ asset.name }}</strong> ({{ asset.ticker }})</p>

      <label>Цена (₽):</label>
      <input type="number" v-model.number="price" min="0" />

      <label>Дата:</label>
      <input type="date" v-model="date" required />

      <p v-if="error" class="error">{{ error }}</p>

      <div class="buttons">
        <button @click="handleSubmit">Добавить</button>
        <button @click="emit('close')">Отмена</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 999;
}
.modal {
  background: white;
  border-radius: 10px;
  padding: 20px;
  width: 320px;
}
label {
  display: block;
  margin-top: 10px;
}
input, select {
  width: 100%;
  margin-top: 4px;
  padding: 6px;
  border-radius: 4px;
  border: 1px solid #ccc;
}
.error {
  color: red;
  margin-top: 10px;
}
.buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 16px;
}
</style>
