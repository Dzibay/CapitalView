<template>
  <div class="assets-page">
    <h1>Мои активы</h1>

    <button @click="showModal = true">Добавить актив</button>
    <!-- Модальное окно -->
    <AddAssetModal v-if="showModal" @close="showModal = false" @added="handleAssetAdded" />

    <div v-if="loading">Загрузка...</div>
    <div v-else-if="assets.length === 0">Активов нет</div>
    <ul v-else>
      <li v-for="asset in assets" :key="asset.id">
        {{ asset.count }} {{ asset.name }} — {{ asset.price }} {{ asset.currency }}
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import AddAssetModal from '../components/AddAssetModal.vue'
import assetsService from "../services/assetsService";

const assets = ref([]);
const loading = ref(true);
const showModal = ref(false);

const loadAssets = async () => {
  try {
    loading.value = true;
    const res = await assetsService.getAssets();
    assets.value = res || [];
  } catch (err) {
    console.error("Ошибка получения активов:", err);
  } finally {
    loading.value = false;
  }
};

onMounted(loadAssets);

// 👇 вызывается после добавления актива в модалке
const handleAssetAdded = async () => {
  showModal.value = false;
  await loadAssets(); // 🔄 обновляем список
};
</script>
