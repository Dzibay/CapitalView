<template>
  <div class="modal-overlay">
    <div class="modal-content">
      <h2>Добавить актив</h2>

      <form @submit.prevent="submitForm">
        <div>
          <label for="name">Название:</label>
          <input type="text" id="name" v-model="form.name" required />
        </div>

        <div>
          <label for="count">Количество:</label>
          <input type="number" id="count" v-model.number="form.count" min="0" required />
        </div>

        <div>
          <label for="price">Цена:</label>
          <input type="number" id="price" v-model.number="form.price" min="0" step="0.01" required />
        </div>

        <div>
          <label for="currency">Валюта:</label>
          <select id="currency" v-model="form.currency" required>
            <option value="RUB">RUB</option>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
          </select>
        </div>

        <div>
          <label for="type">Тип актива:</label>
          <select id="type" v-model="form.type" required>
            <option value="Crypto">Крипта</option>
            <option value="RealEstate">Недвижимость</option>
            <option value="Cash">Валюта</option>
            <option value="Other">Другое</option>
          </select>
        </div>

        <button type="submit">Добавить</button>
        <button type="button" @click="$emit('close')">Закрыть</button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import assetsService from '../services/assetsService'

// форма реактивная
const form = reactive({
  name: '',
  count: 0,
  price: 0,
  currency: 'USD',
  type: 'RealEstate',
})

const emit = defineEmits(['close', 'added'])

const submitForm = async () => {
  try {
    await assetsService.addAsset({ ...form })
    // после успешного добавления вызываем событие close, родитель обновит список
    emit('added')
  } catch (err) {
    console.error('Ошибка добавления актива:', err)
  }
}
</script>

<style>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.5);
}
.modal-content {
  background: white;
  margin: 100px auto;
  padding: 20px;
  width: 400px;
  border-radius: 8px;
}
.modal-content form div {
  margin-bottom: 10px;
}
</style>
