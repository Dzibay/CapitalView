<template>
  <div>
    <h1>Мой инвестиционный портфель</h1>
    
    <input v-model="token" placeholder="Введите API токен" />
    <button @click="fetchPortfolio">Загрузить активы</button>

    <div v-if="loading">Загрузка...</div>
    <div v-if="error" style="color:red">{{ error }}</div>

    <ul v-if="assets.length">
      <li v-for="asset in assets" :key="asset.ticker">
        {{ asset.ticker }} ({{ asset.name }}) — {{ asset.quantity }} шт.
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'

const token = ref('')
const assets = ref([])
const loading = ref(false)
const error = ref(null)

async function fetchPortfolio() {
  if (!token.value) {
    error.value = 'Токен не введён'
    return
  }

  loading.value = true
  error.value = null
  assets.value = []

  try {
    const response = await axios.post('http://127.0.0.1:5000/portfolio')
    assets.value = response.data
  } catch (err) {
    error.value = err.response?.data?.error || err.message
  } finally {
    loading.value = false
  }
}
</script>

<style>
input {
  padding: 5px;
  margin-right: 5px;
}
button {
  padding: 5px 10px;
}
</style>
