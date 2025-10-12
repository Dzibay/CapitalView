<script setup>
import { ref } from 'vue'

const props = defineProps({
  asset: Object,
  onSell: Function
})

const emit = defineEmits(['close'])

const quantity = ref(0)
const price = ref(0)
const error = ref('')

const handleSell = async () => {
  if (!quantity.value || quantity.value <= 0) {
    error.value = 'Введите количество для продажи'
    return
  }
  if (!price.value || price.value <= 0) {
    error.value = 'Введите цену продажи'
    return
  }

  try {
    await props.onSell({
      portfolio_asset_id: props.asset.portfolio_asset_id,
      quantity: quantity.value,
      price: price.value,
      date: date.value
    })
    emit('close')
  } catch (e) {
    error.value = 'Ошибка при продаже: ' + e.message
  }
}

const date = ref(new Date().toISOString().slice(0, 10))
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <h3>Продажа актива</h3>
      <p><strong>{{ asset.name }}</strong> ({{ asset.ticker }})</p>
      <p>Доступно: {{ asset.quantity }}</p>

      <label>Количество:</label>
      <input type="number" v-model.number="quantity" min="0" :max="asset.quantity" />

      <label>Цена продажи (₽):</label>
      <input type="number" v-model.number="price" min="0" />

      <label>Дата продажи:</label>
      <input type="date" v-model="date" required />

      <p v-if="error" class="error">{{ error }}</p>

      <div class="buttons">
        <button @click="handleSell">Продать</button>
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
  width: 300px;
}
label {
  display: block;
  margin-top: 10px;
}
input {
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
