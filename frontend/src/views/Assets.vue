<script setup>
import { ref, onMounted, inject } from 'vue'
import AddAssetModal from '../components/AddAssetModal.vue'

const showModal = ref(false);

const user = inject('user')
const portfolios = inject('portfolios')
const loading = inject('loading')
const reloadAssets = inject('reloadAssets')
const addAsset = inject('addAsset')
const removeAsset = inject('removeAsset')

</script>


<template>
  <div>
    <button @click="showModal = true">➕ Добавить актив</button>
    <AddAssetModal 
      v-if="showModal" 
      @close="showModal = false" 
      :onSave="addAsset" 
    />
    <div v-if="loading">Загрузка...</div>

    <div v-else-if="portfolios.length === 0">
      У вас пока нет портфелей
    </div>

    <div v-else>
      <div v-for="portfolio in portfolios" :key="portfolio.id" class="portfolio-block">

        <h2>{{ portfolio.name }}</h2>
        <p v-if="!portfolio.assets || portfolio.assets.length === 0">
          Активов нет
        </p>

        <ul v-else>
          <li v-for="asset in portfolio.assets" :key="asset.portfolio_asset_id" class="asset-item">
            <strong>{{ asset.name }}</strong> ({{ asset.ticker }}) — 
            {{ asset.quantity }} шт × {{ asset.average_price.toFixed(2) }} ₽  
            <span v-if="asset.current_price">
              (текущая: {{ asset.current_price.toFixed(2) }} ₽)
            </span>
            <button @click="removeAsset(asset.portfolio_asset_id)">❌</button>
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
  border-radius: 8px;
}

.asset-item {
  margin: 4px 0;
}
</style>