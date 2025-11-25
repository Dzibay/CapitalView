<script setup>
import { ref, inject, computed, onMounted, watch } from "vue";
import AddAssetModal from "../components/modals/AddAssetModal.vue";
import AddTransactionModal from "../components/modals/AddTransactionModal.vue";
import AddPriceModal from "../components/modals/AddPriceModal.vue";
import ImportPortfolioModal from "../components/modals/ImportPortfolioModal.vue";
import AddPortfolioModal from "../components/modals/AddPortfolioModal.vue";
import PortfolioTree from '../components/PortfolioTree.vue'

const showAddModal = ref(false);
const showAddPortfolioModal = ref(false);
const showAddTransactionModal = ref(false);
const showAddPriceModal = ref(false);
const showImportModal = ref(false);

const selectedAsset = ref(null);
const activeAssetMenu = ref(null);
const activePortfolioMenu = ref(null);

const loading = inject("loading");
const dashboardData = inject("dashboardData");
const reloadDashboard = inject('reloadDashboard')
const addAsset = inject("addAsset");
const removeAsset = inject("removeAsset");
const deletePortfolio = inject("deletePortfolio")
const clearPortfolio = inject("clearPortfolio");
const addPortfolio = inject("addPortfolio");
const addTransaction = inject("addTransaction")
const addPrice = inject('addPrice');
const importPortfolio = inject("importPortfolio");


// === localStorage для раскрытых портфелей ===
const STORAGE_KEY = 'expandedPortfolios';
const expandedPortfolios = ref([]);
onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) expandedPortfolios.value = JSON.parse(saved);
});

// Автоматическое сохранение при изменении
watch(expandedPortfolios, (val) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(val));
}, { deep: true });


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

// Функция обновления всех портфелей с подключением
const updatingPortfolios = ref(new Set());

const refreshPortfolios = async () => {
  const portfolios = dashboardData.value?.data?.portfolios ?? [];
  
  // Создаем массив промисов для асинхронных вызовов
  const importPromises = portfolios.map(async (p) => {
  if (p.connection?.api_key) {
    updatingPortfolios.value.add(p.id)
    try {
      await importPortfolio({
          broker_id: p.connection.broker_id,
          token: p.connection.api_key,
          portfolioId: p.id,
          portfolio_name: null
        });
      } finally {
        updatingPortfolios.value.delete(p.id)
      }
  }
});

  // Ждем завершения всех промисов
  console.log(updatingPortfolios.value)
  await Promise.all(importPromises);

  await reloadDashboard();
  console.log("Обновление портфелей завершено");
};

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
  <div class="dashboard-container">
    <div class="content-wrapper">
      
      <div class="action-bar">
        <h1 class="page-title">Мои Активы</h1>
        <div class="buttons-group">
          <button class="btn btn-primary" @click="showAddModal = true">
            <span class="icon">➕</span> Актив
          </button>
          <button class="btn btn-secondary" @click="showAddPortfolioModal = true">
            <span class="icon">📁</span> Портфель
          </button>
          <div class="divider-vertical"></div>
          <button class="btn btn-outline" @click="showImportModal = true">
            📥 Импорт
          </button>
          <button class="btn btn-ghost" @click="refreshPortfolios" title="Обновить портфели">
            🔄
          </button>
        </div>
      </div>

      <AddAssetModal v-if="showAddModal" @close="showAddModal = false" :onSave="addAsset" :referenceData="parsedDashboard.reference" :portfolios="parsedDashboard.portfolios"/>
      <AddPortfolioModal v-if="showAddPortfolioModal" @close="showAddPortfolioModal = false" :onSave="addPortfolio" :portfolios="parsedDashboard.portfolios"/>
      <AddTransactionModal v-if="showAddTransactionModal" :asset="selectedAsset" :onSubmit="addTransaction" @close="showAddTransactionModal = false"/>
      <AddPriceModal v-if="showAddPriceModal" :asset="selectedAsset" :onSubmit="addPrice" @close="showAddPriceModal = false"/>
      <ImportPortfolioModal v-if="showImportModal" @close="showImportModal = false" :onImport="importPortfolio" :portfolios="parsedDashboard.portfolios"/>

      <div v-if="loading" class="status-block">
        <div class="loader"></div>
        <span>Загрузка данных...</span>
      </div>
      
      <div v-else-if="parsedDashboard.portfolios.length === 0" class="empty-placeholder">
        <div class="empty-icon">📂</div>
        <h3>У вас пока нет портфелей</h3>
        <p>Создайте первый портфель, чтобы начать отслеживать активы</p>
        <button class="btn btn-primary" @click="showAddPortfolioModal = true">Создать портфель</button>
      </div>

      <div v-else class="tree-wrapper">
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
          @deletePortfolio="deletePortfolio"
          @addTransaction="(asset) => { selectedAsset = asset; showAddTransactionModal = true }"
          @addPrice="(asset) => { selectedAsset = asset; showAddPriceModal = true }"
          :updatingPortfolios="updatingPortfolios"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Base Layout */
.dashboard-container {
  min-height: 100vh;
  padding: 32px 20px;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1f2937;
}

.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
}

/* Action Bar */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  background: transparent;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin: 0;
}

.buttons-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  padding: 6px;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

.divider-vertical {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
  margin: 0 4px;
}

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  border-radius: 6px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background-color: #2563eb;
  color: white;
}
.btn-primary:hover {
  background-color: #1d4ed8;
}

.btn-secondary {
  background-color: #f3f4f6;
  color: #374151;
}
.btn-secondary:hover {
  background-color: #e5e7eb;
}

.btn-outline {
  background: transparent;
  border: 1px solid #d1d5db;
  color: #374151;
}
.btn-outline:hover {
  border-color: #9ca3af;
  background: #f9fafb;
}

.btn-ghost {
  background: transparent;
  color: #6b7280;
  padding: 0 10px;
}
.btn-ghost:hover {
  background: #f3f4f6;
  color: #2563eb;
}

.icon {
  font-size: 14px;
}

/* Empty State & Status */
.status-block {
  text-align: center;
  padding: 40px;
  color: #6b7280;
}

.empty-placeholder {
  text-align: center;
  padding: 60px 20px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}
.empty-placeholder h3 {
  margin: 0 0 8px;
  color: #374151;
}
.empty-placeholder p {
  color: #6b7280;
  margin-bottom: 24px;
}
</style>