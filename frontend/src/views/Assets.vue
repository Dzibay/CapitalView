<script setup>
import { ref, computed } from "vue";
import { useDashboardStore } from '../stores/dashboard.store';
import { useUIStore } from '../stores/ui.store';
import { useAssetsStore } from '../stores/assets.store';
import { usePortfoliosStore } from '../stores/portfolios.store';
import { useTransactionsStore } from '../stores/transactions.store';
import AddAssetModal from "../components/modals/AddAssetModal.vue";
import AddTransactionModal from "../components/modals/AddTransactionModal.vue";
import AddPriceModal from "../components/modals/AddPriceModal.vue";
import MoveAssetModal from "../components/modals/MoveAssetModal.vue";
import ImportPortfolioModal from "../components/modals/ImportPortfolioModal.vue";
import AddPortfolioModal from "../components/modals/AddPortfolioModal.vue";
import PortfolioTree from '../components/PortfolioTree.vue';
import ContextMenu from '../components/ContextMenu.vue';
import { useExpandedState } from '../composables/useExpandedState';
import { useModals } from '../composables/useModal';
import { usePortfolio } from '../composables/usePortfolio';
import LoadingState from '../components/LoadingState.vue';

const selectedAsset = ref(null);

// Используем stores вместо inject
const dashboardStore = useDashboardStore();
const uiStore = useUIStore();
const assetsStore = useAssetsStore();
const portfoliosStore = usePortfoliosStore();
const transactionsStore = useTransactionsStore();

// Обертки для совместимости с модальными окнами
const addAsset = async (assetData) => {
  await assetsStore.addAsset(assetData);
};

const removeAsset = async (portfolioAssetId) => {
  await assetsStore.removeAsset(portfolioAssetId);
};

const moveAsset = async ({ portfolio_asset_id, target_portfolio_id }) => {
  await assetsStore.moveAsset({ portfolio_asset_id, target_portfolio_id });
};

const deletePortfolio = async (portfolioId) => {
  await portfoliosStore.deletePortfolio(portfolioId);
};

const clearPortfolio = async (portfolioId) => {
  await portfoliosStore.clearPortfolio(portfolioId);
};

const addPortfolio = async (portfolioData) => {
  await portfoliosStore.addPortfolio(portfolioData);
};

const addTransaction = async (data) => {
  await transactionsStore.addTransaction(data);
};

const addPrice = async (data) => {
  await assetsStore.addPrice(data);
};

const importPortfolio = async (data) => {
  await portfoliosStore.importPortfolio(data);
};

const reloadDashboard = async () => {
  await dashboardStore.reloadDashboard();
};

// Используем композабл для управления раскрытыми портфелями
const { expanded: expandedPortfolios, toggle: togglePortfolio } = useExpandedState('expandedPortfolios');

// Используем композабл для управления модалками
const { modals, open: openModal, close: closeModal } = useModals([
  'addAsset',
  'addPortfolio',
  'addTransaction',
  'addPrice',
  'moveAsset',
  'import'
]);


// Используем композабл для работы с портфелями
// Передаем computed ref для dashboardData из store
const dashboardDataComputed = computed(() => ({
  value: {
    data: {
      portfolios: dashboardStore.portfolios,
      referenceData: dashboardStore.referenceData
    }
  }
}));
const { portfolios: portfolioList, buildPortfolioTree } = usePortfolio(dashboardDataComputed, null);

/* === Парсинг данных === */
const parsedDashboard = computed(() => {
  const portfolios = dashboardStore.portfolios ?? [];
  const portfolioTree = buildPortfolioTree(portfolios);
  return {
    portfolios,
    portfolioTree,
    reference: dashboardStore.referenceData ?? [],
  };
});

// Функция обновления всех портфелей с подключением
const updatingPortfolios = ref(new Set());

const refreshPortfolios = async () => {
  const portfolios = dashboardStore.portfolios ?? [];
  
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
  await Promise.all(importPromises);
  await reloadDashboard();
};

// togglePortfolio уже определен в useExpandedState

// Обработчики для контекстного меню
const handleAddTransaction = (asset) => {
  selectedAsset.value = asset;
  openModal('addTransaction');
};

const handleAddPrice = (asset) => {
  selectedAsset.value = asset;
  openModal('addPrice');
};

const handleMoveAsset = (asset) => {
  // Убеждаемся, что у актива есть portfolio_id
  // Если его нет, пытаемся найти портфель по portfolio_asset_id
  if (!asset.portfolio_id && asset.portfolio_asset_id) {
    // Ищем портфель, содержащий этот актив
    const portfolio = parsedDashboard.value.portfolios.find(p => 
      p.assets && p.assets.some(a => a.portfolio_asset_id === asset.portfolio_asset_id)
    )
    if (portfolio) {
      asset.portfolio_id = portfolio.id
    }
  }
  selectedAsset.value = asset;
  openModal('moveAsset');
};
</script>

<template>
  <div class="dashboard-container">
    <div class="content-wrapper">
      
      <div class="action-bar">
        <h1 class="page-title">Мои Активы</h1>
        <div class="buttons-group">
          <button class="btn btn-primary" @click="openModal('addAsset')">
            <span class="icon">➕</span> Актив
          </button>
          <button class="btn btn-secondary" @click="openModal('addPortfolio')">
            <span class="icon">📁</span> Портфель
          </button>
          <div class="divider-vertical"></div>
          <button class="btn btn-outline" @click="openModal('import')">
            📥 Импорт
          </button>
          <button class="btn btn-ghost" @click="refreshPortfolios" title="Обновить портфели">
            🔄
          </button>
        </div>
      </div>

      <AddAssetModal v-if="modals.addAsset" @close="closeModal('addAsset')" :onSave="addAsset" :referenceData="parsedDashboard.reference" :portfolios="parsedDashboard.portfolios"/>
      <AddPortfolioModal v-if="modals.addPortfolio" @close="closeModal('addPortfolio')" :onSave="addPortfolio" :portfolios="parsedDashboard.portfolios"/>
      <AddTransactionModal v-if="modals.addTransaction" :asset="selectedAsset" :onSubmit="addTransaction" @close="closeModal('addTransaction')"/>
      <AddPriceModal v-if="modals.addPrice" :asset="selectedAsset" :onSubmit="addPrice" @close="closeModal('addPrice')"/>
      <MoveAssetModal v-if="modals.moveAsset" :asset="selectedAsset" :portfolios="parsedDashboard.portfolios" :onSubmit="moveAsset" @close="closeModal('moveAsset')"/>
      <ImportPortfolioModal v-if="modals.import" @close="closeModal('import')" :onImport="importPortfolio" :portfolios="parsedDashboard.portfolios"/>

      <LoadingState v-if="uiStore.loading" />
      
      <div v-else-if="parsedDashboard.portfolios.length === 0" class="empty-placeholder">
        <div class="empty-icon">📂</div>
        <h3>У вас пока нет портфелей</h3>
        <p>Создайте первый портфель, чтобы начать отслеживать активы</p>
        <button class="btn btn-primary" @click="openModal('addPortfolio')">Создать портфель</button>
      </div>

      <div v-else class="tree-wrapper">
        <PortfolioTree
          :portfolios="parsedDashboard.portfolioTree"
          :expandedPortfolios="expandedPortfolios"
          :updatingPortfolios="updatingPortfolios"
          @togglePortfolio="togglePortfolio"
          @clearPortfolio="clearPortfolio"
          @deletePortfolio="deletePortfolio"
          @removeAsset="removeAsset"
          @addTransaction="addTransaction"
          @addPrice="addPrice"
          @moveAsset="handleMoveAsset"
        />

        <ContextMenu
          @clearPortfolio="clearPortfolio"
          @deletePortfolio="deletePortfolio"
          @removeAsset="removeAsset"
          @addTransaction="handleAddTransaction"
          @addPrice="handleAddPrice"
          @moveAsset="handleMoveAsset"
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

/* Empty State */

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