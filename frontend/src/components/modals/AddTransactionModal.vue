<script setup>
import { ref } from 'vue'

const props = defineProps({
  asset: Object,
  onSubmit: Function // универсальный обработчик добавления транзакции
})

const emit = defineEmits(['close'])

const transactionType = ref('buy') // buy / sell
const quantity = ref(0)
const price = ref(0)
const date = ref(new Date().toISOString().slice(0, 10))
const error = ref('')

const handleSubmit = async () => {
  if (!quantity.value || quantity.value <= 0) {
    error.value = 'Введите количество'
    return
  }
  if (!price.value || price.value <= 0) {
    error.value = 'Введите цену'
    return
  }

  try {
    await props.onSubmit({
      asset_id: props.asset.asset_id,
      portfolio_asset_id: props.asset.portfolio_asset_id,
      transaction_type: transactionType.value === 'buy' ? 1 : 2,
      quantity: quantity.value,
      price: price.value,
      transaction_date: date.value,  // Используем transaction_date вместо date
      date: date.value  // Оставляем для обратной совместимости
    })
    emit('close')
  } catch (e) {
    error.value = 'Ошибка при добавлении транзакции: ' + e.message
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <h3>Добавление транзакции</h3>
      <p><strong>{{ asset.name }}</strong> ({{ asset.ticker }})</p>

      <label>Тип операции:</label>
      <select v-model="transactionType">
        <option value="buy">Покупка</option>
        <option value="sell">Продажа</option>
      </select>

      <label>Количество:</label>
      <input type="number" v-model.number="quantity" min="0" />

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
