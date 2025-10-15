<script setup>
import { ref, inject, computed } from 'vue'
import AddAssetModal from '../components/AddAssetModal.vue'
import SellAssetModal from '../components/SellAssetModal.vue'
import ImportPortfolioModal from '../components/ImportPortfolioModal.vue'

const showAddModal = ref(false)
const showSellModal = ref(false)
const showImportModal = ref(false)
const selectedAsset = ref(null)

const user = inject('user')
const loading = inject('loading')
const dashboardData = inject('dashboardData')
const reloadDasboard = inject('reloadDashboard')

const addAsset = inject('addAsset')
const removeAsset = inject('removeAsset')
const clearPortfolio = inject('clearPortfolio')
// const sellAsset = inject('sellAsset')
const importPortfolio = inject('importPortfolio')

const parsedDashboard = computed(() => {
  const data = dashboardData.value?.data
  if (!data) return null

  return {
    portfolios: data.portfolios ?? [],
    reference: data.referenceData ?? []
  }
})
</script>

<template>
  <div>
    <button @click="showAddModal = true">➕ Добавить актив</button>
    <button @click="showImportModal = true">📥 Импорт портфеля</button>

    <AddAssetModal 
      v-if="showAddModal" 
      @close="showAddModal = false" 
      :onSave="addAsset" 
      :referenceData="parsedDashboard.reference" 
      :portfolios="parsedDashboard.portfolios" 
    />

    <SellAssetModal
      v-if="showSellModal"
      :asset="selectedAsset"
      @close="showSellModal = false"
      :onSell="sellAsset"
    />

    <ImportPortfolioModal
      v-if="showImportModal"
      @close="showImportModal = false"
      :onImport="importPortfolio"
      :portfolios="parsedDashboard.portfolios"
    />

    <div v-if="loading">Загрузка...</div>

    <div v-else-if="parsedDashboard.portfolios.length === 0">
      У вас пока нет портфелей
    </div>

    <div v-else>
      <div
        v-for="portfolio in parsedDashboard.portfolios"
        :key="portfolio.id"
        class="portfolio-block"
      >
        <h2>{{ portfolio.name }}</h2>
        <button @click="clearPortfolio(portfolio.id)">Очистить портфель</button>
        <p v-if="!portfolio.assets || portfolio.assets.length === 0">
          Активов нет
        </p>

        <ul v-else>
          <li
            v-for="asset in portfolio.assets"
            :key="asset.portfolio_asset_id"
            class="asset-item"
          >
            <strong>{{ asset.name }}</strong> ({{ asset.ticker }}) — 
            {{ asset.quantity }} шт × {{ asset.average_price.toFixed(2) }} ₽  
            <span v-if="asset.last_price">
              (текущая: {{ asset.last_price.toFixed(2) }} ₽) (стоимость: {{ asset.quantity * asset.last_price.toFixed(2) }} ₽)
            </span>

            <button @click="removeAsset(asset.portfolio_asset_id)">❌</button>
            <button @click="() => { selectedAsset = asset; showSellModal = true }">💰 Продать</button>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>
