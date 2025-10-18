<script setup>
import { ref, inject, computed } from "vue";
import AddAssetModal from "../components/modals/AddAssetModal.vue";
import AddTransactionModal from "../components/modals/AddTransactionModal.vue";
import ImportPortfolioModal from "../components/modals/ImportPortfolioModal.vue";
import AddPortfolioModal from "../components/modals/AddPortfolioModal.vue";
import PortfolioTree from '../components/PortfolioTree.vue'

const showAddModal = ref(false);
const showAddPortfolioModal = ref(false);
const showAddTransactionModal = ref(false);
const showImportModal = ref(false);

const selectedAsset = ref(null);
const expandedPortfolios = ref([]);
const activeAssetMenu = ref(null);
const activePortfolioMenu = ref(null);

const loading = inject("loading");
const dashboardData = inject("dashboardData");
const addAsset = inject("addAsset");
const removeAsset = inject("removeAsset");
const clearPortfolio = inject("clearPortfolio");
const addPortfolio = inject("addPortfolio");
const addTransaction = inject("addTransaction")
const importPortfolio = inject("importPortfolio");

/* === 1️⃣ Построение иерархического дерева портфелей === */
function buildPortfolioTree(portfolios) {
  const map = {};
  const roots = [];

  portfolios.forEach((p) => {
    map[p.id] = { ...p, children: [] };
  });

  portfolios.forEach((p) => {
    if (p.parent_portfolio_id && map[p.parent_portfolio_id]) {
      map[p.parent_portfolio_id].children.push(map[p.id]);
    } else {
      roots.push(map[p.id]);
    }
  });

  return roots;
}

/* === 2️⃣ Парсинг данных === */
const parsedDashboard = computed(() => {
  const data = dashboardData.value?.data;
  if (!data) return { portfolios: [], reference: [] };

  const portfolios = data.portfolios ?? [];
  const portfolioTree = buildPortfolioTree(data.portfolios ?? []);
  return {
    portfolios,
    portfolioTree,
    reference: data.referenceData ?? [],
  };
});

/* === 3️⃣ Поведение меню и раскрытия === */
const togglePortfolio = (id) => {
  if (expandedPortfolios.value.includes(id))
    expandedPortfolios.value = expandedPortfolios.value.filter((i) => i !== id);
  else expandedPortfolios.value.push(id);
};

const toggleAssetMenu = (id) => {
  activeAssetMenu.value = activeAssetMenu.value === id ? null : id;
  activePortfolioMenu.value = null;
};

const togglePortfolioMenu = (id) => {
  activePortfolioMenu.value = activePortfolioMenu.value === id ? null : id;
  activeAssetMenu.value = null;
};
</script>

<template>
  <div class="dashboard">
    <!-- Верхняя панель -->
    <div class="toolbar">
      <button class="btn" @click="showAddModal = true">➕ Добавить актив</button>
      <button class="btn" @click="showAddPortfolioModal = true">📁 Создать портфель</button>
      <button class="btn" @click="showImportModal = true">📥 Импорт портфеля</button>
    </div>

    <!-- Модалки -->
    <AddAssetModal
      v-if="showAddModal"
      @close="showAddModal = false"
      :onSave="addAsset"
      :referenceData="parsedDashboard.reference"
      :portfolios="parsedDashboard.portfolios"
    />
    <AddPortfolioModal
      v-if="showAddPortfolioModal"
      @close="showAddPortfolioModal = false"
      :onSave="addPortfolio"
      :portfolios="parsedDashboard.portfolios"
    />
    <AddTransactionModal
      v-if="showAddTransactionModal"
      :asset="selectedAsset"
      :onSubmit="addTransaction"
      @close="showAddTransactionModal = false"
    />
    <ImportPortfolioModal
      v-if="showImportModal"
      @close="showImportModal = false"
      :onImport="importPortfolio"
      :portfolios="parsedDashboard.portfolios"
    />

    <!-- Загрузка -->
    <div v-if="loading" class="status">Загрузка...</div>
    <div v-else-if="parsedDashboard.portfolios.length === 0" class="status">
      У вас пока нет портфелей
    </div>

    <!-- Основной список -->
    <div v-else>
      <PortfolioTree
        :portfolios="parsedDashboard.portfolioTree"
        :expandedPortfolios="expandedPortfolios"
        :activePortfolioMenu="activePortfolioMenu"
        :activeAssetMenu="activeAssetMenu"
        @togglePortfolio="togglePortfolio"
        @toggleAssetMenu="toggleAssetMenu"
        @togglePortfolioMenu="togglePortfolioMenu"
        @removeAsset="removeAsset"
        @clearPortfolio="clearPortfolio"
        @selectAsset="(asset) => { selectedAsset = asset; showAddTransactionModal = true }"
      />
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 20px;
  font-family: Arial, sans-serif;
  color: #222;
}
.toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}
.btn {
  background: #7c858c;
  color: white;
  border: none;
  padding: 8px 14px;
  border-radius: 4px;
  cursor: pointer;
}
.btn:hover {
  background: #005ea3;
}

</style>