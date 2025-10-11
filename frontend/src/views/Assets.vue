<script setup>
import { ref, onMounted } from 'vue'
import AddAssetModal from '../components/AddAssetModal.vue'
import assetsService from "../services/assetsService";

const portfolios = ref([]);
const loading = ref(true);
const showModal = ref(false);

const loadAssets = async () => {
  try {
    loading.value = true;
    const res = await assetsService.getAssets();
    portfolios.value = res || [];
    console.log(portfolios)
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

const removeAsset = async (id) => {
  try {
    await assetsService.deleteAsset(id)
    assets.value = assets.value.filter(a => a.id !== id) // убираем локально
  } catch (err) {
    console.error("Ошибка удаления актива:", err)
  }
}

</script>


<template>
  <div>
    <div v-if="loading">Загрузка...</div>

    <div v-else-if="portfolios.length === 0">
      У вас пока нет портфелей
    </div>

    <div v-else>
      <div 
        v-for="portfolio in portfolios" 
        :key="portfolio.id" 
        class="portfolio-block"
      >
        <h2>{{ portfolio.name }}</h2>
        <p v-if="!portfolio.assets || portfolio.assets.length === 0">
          Активов нет
        </p>

        <ul v-else>
          <li 
            v-for="asset in portfolio.assets" 
            :key="asset.id"
            class="asset-item"
          >
            <strong>{{ asset.name }}</strong> ({{ asset.ticker }}) — 
            {{ asset.quantity }} шт × {{ asset.average_price.toFixed(2) }} ₽  
            <span v-if="asset.current_price">
              (текущая: {{ asset.current_price.toFixed(2) }} ₽)
            </span>
            <button @click="removeAsset(asset.id)">❌</button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<style>
.portfolio-block {
  margin-bottom: 24px;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.asset-item {
  margin: 4px 0;
}
</style>