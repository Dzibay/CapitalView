<script setup>
import { ref, computed, onMounted, watch } from "vue";
import { useDashboardStore } from '../stores/dashboard.store';
import { useUIStore } from '../stores/ui.store';
import { useAssetsStore } from '../stores/assets.store';
import { usePortfoliosStore } from '../stores/portfolios.store';
import { useTransactionsStore } from '../stores/transactions.store';
import { useImportTasksStore } from '../stores/importTasks.store';
import { Plus, FolderPlus, Upload, RefreshCw } from 'lucide-vue-next';
import AddAssetModal from "../components/modals/AddAssetModal.vue";
import AddTransactionModal from "../components/modals/AddTransactionModal.vue";
import AddPriceModal from "../components/modals/AddPriceModal.vue";
import MoveAssetModal from "../components/modals/MoveAssetModal.vue";
import ImportPortfolioModal from "../components/modals/ImportPortfolioModal.vue";
import ImportStatusModal from "../components/modals/ImportStatusModal.vue";
import AddPortfolioModal from "../components/modals/AddPortfolioModal.vue";
import PortfolioTree from '../components/PortfolioTree.vue';
import ContextMenu from '../components/ContextMenu.vue';
import { useExpandedState } from '../composables/useExpandedState';
import { useModals } from '../composables/useModal';
import { usePortfolio } from '../composables/usePortfolio';
import { Button, ToggleSwitch } from '../components/base';
import LoadingState from '../components/base/LoadingState.vue';
import PageLayout from '../components/PageLayout.vue';
import PageHeader from '../components/PageHeader.vue';

const selectedAsset = ref(null);

// Используем stores вместо inject
const dashboardStore = useDashboardStore();
const uiStore = useUIStore();
const assetsStore = useAssetsStore();
const portfoliosStore = usePortfoliosStore();
const transactionsStore = useTransactionsStore();
const importTasksStore = useImportTasksStore();

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

const importPortfolio = async (data, showStatusModal = true) => {
  const result = await portfoliosStore.importPortfolio(data);
  // Если создана задача, добавляем её в store
  if (result.success && result.task_id) {
    importTasksStore.addTask(
      result.task_id,
      data.portfolioId,
      data.portfolio_name
    );
    
    // Если нужно показать модалку статуса, открываем её
    if (showStatusModal) {
      currentImportTaskId.value = result.task_id;
      closeModal('import');
      openModal('importStatus');
    }
  }
  return result;
};

// Обработчики для модалки статуса
const handleImportComplete = async (result) => {
  // Обновляем данные после успешного импорта
  await reloadDashboard();
  // Модалка закроется автоматически через 2 секунды (в компоненте)
};

const handleImportError = (errorMessage) => {
  console.error('Ошибка импорта:', errorMessage);
  // Модалка останется открытой, показывая ошибку
};

// Открытие модалки для задачи
const openTaskModal = (taskId) => {
  currentImportTaskId.value = taskId;
  importTasksStore.openModal(taskId);
  openModal('importStatus');
};

// Закрытие модалки задачи
const closeTaskModal = () => {
  if (currentImportTaskId.value) {
    importTasksStore.closeModal(currentImportTaskId.value);
  }
  currentImportTaskId.value = null;
  closeModal('importStatus');
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
  'import',
  'importStatus'
]);

// ID текущей задачи импорта
const currentImportTaskId = ref(null);

// Фильтр для показа проданных активов (с сохранением в localStorage)
const SHOW_SOLD_ASSETS_KEY = 'showSoldAssets';
const showSoldAssets = ref(false);

onMounted(() => {
  try {
    const stored = localStorage.getItem(SHOW_SOLD_ASSETS_KEY);
    if (stored !== null) {
      showSoldAssets.value = stored === '1' || stored === 'true';
    }
  } catch (e) {
    // localStorage может быть недоступен, просто игнорируем
  }
});

watch(showSoldAssets, (value) => {
  try {
    localStorage.setItem(SHOW_SOLD_ASSETS_KEY, value ? '1' : '0');
  } catch (e) {
    // игнорируем ошибки записи в localStorage
  }
});


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
        // При автоматическом обновлении показываем модалку статуса
        await importPortfolio({
          broker_id: p.connection.broker_id,
          token: p.connection.api_key,
          portfolioId: p.id,
          portfolio_name: null
        }, true); // showStatusModal = true - показываем модалку
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
  <PageLayout>
    <PageHeader 
      title="Мои Активы"
      subtitle="Управление портфелями и активами"
    >
      <template #actions>
        <ToggleSwitch 
          v-model="showSoldAssets" 
          label="Показать проданные активы"
        />
      </template>
      <template #menu>
        <div class="buttons-group">
          <Button variant="primary" @click="openModal('addAsset')">
            <template #icon>
              <Plus :size="16" />
            </template>
            Добавить актив
          </Button>
          <Button variant="secondary" @click="openModal('addPortfolio')">
            <template #icon>
              <FolderPlus :size="16" />
            </template>
            Создать портфель
          </Button>
          <div class="divider-vertical"></div>
          <div class="button-group-unified">
            <Button variant="outline" @click="openModal('import')" class="btn-group-left">
              <template #icon>
                <Upload :size="16" />
              </template>
              Импорт
            </Button>
            <Button variant="outline" @click="refreshPortfolios" icon-only title="Обновить портфели" class="btn-group-right btn-refresh">
              <template #icon>
                <RefreshCw :size="16" />
              </template>
            </Button>
          </div>
        </div>
      </template>
    </PageHeader>

      <AddAssetModal v-if="modals.addAsset" @close="closeModal('addAsset')" :onSave="addAsset" :referenceData="parsedDashboard.reference" :portfolios="parsedDashboard.portfolios"/>
      <AddPortfolioModal v-if="modals.addPortfolio" @close="closeModal('addPortfolio')" :onSave="addPortfolio" :portfolios="parsedDashboard.portfolios"/>
      <AddTransactionModal v-if="modals.addTransaction" :asset="selectedAsset" :onSubmit="addTransaction" @close="closeModal('addTransaction')"/>
      <AddPriceModal v-if="modals.addPrice" :asset="selectedAsset" :onSubmit="addPrice" @close="closeModal('addPrice')"/>
      <MoveAssetModal v-if="modals.moveAsset" :asset="selectedAsset" :portfolios="parsedDashboard.portfolios" :onSubmit="moveAsset" @close="closeModal('moveAsset')"/>
      <ImportPortfolioModal 
        v-if="modals.import" 
        @close="closeModal('import')" 
        :onImport="importPortfolio" 
        :portfolios="parsedDashboard.portfolios"
      />
      <ImportStatusModal 
        v-if="modals.importStatus && currentImportTaskId" 
        :taskId="currentImportTaskId"
        @close="closeTaskModal"
        :onComplete="handleImportComplete"
        :onError="handleImportError"
      />
      
      <!-- Индикатор активных задач импорта -->
      <div v-if="importTasksStore.getActiveTasks().length > 0" class="active-tasks-indicator">
        <div class="tasks-badge">
          <span class="tasks-icon">📥</span>
          <span class="tasks-count">{{ importTasksStore.getActiveTasks().length }}</span>
          <span class="tasks-text">активных импортов</span>
        </div>
        <div class="tasks-list">
          <button
            v-for="taskId in importTasksStore.getActiveTasks()"
            :key="taskId"
            class="task-item"
            @click="openTaskModal(taskId)"
            :class="{ active: currentImportTaskId === taskId }"
          >
            <span class="task-icon">📊</span>
            <span class="task-info">
              {{ importTasksStore.getTaskInfo(taskId)?.portfolioName || `Задача #${taskId}` }}
            </span>
            <span v-if="!importTasksStore.isModalOpen(taskId)" class="task-status-badge">Скрыто</span>
          </button>
        </div>
      </div>

      <LoadingState v-if="uiStore.loading" />
      
      <div v-else-if="parsedDashboard.portfolios.length === 0" class="empty-placeholder">
        <div class="empty-icon">📂</div>
        <h3>У вас пока нет портфелей</h3>
        <p>Создайте первый портфель, чтобы начать отслеживать активы</p>
        <Button variant="primary" @click="openModal('addPortfolio')" class="empty-btn">
          <template #icon>
            <FolderPlus :size="16" />
          </template>
          Создать портфель
        </Button>
      </div>

      <div v-else class="assets-content">
        <PortfolioTree
          :portfolios="parsedDashboard.portfolioTree"
          :expandedPortfolios="expandedPortfolios"
          :updatingPortfolios="updatingPortfolios"
          :showSoldAssets="showSoldAssets"
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
  </PageLayout>
</template>

<style scoped>

.buttons-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  padding: 0;
  flex-wrap: wrap;
}

.divider-vertical {
  width: 1px;
  height: 24px;
  background: #e5e7eb;
  margin: 0 2px;
  flex-shrink: 0;
}

/* Button groups */
.button-group-unified {
  display: flex;
  gap: 0;
}

.button-group-unified :deep(.btn-group-left) {
  border-top-right-radius: 0;
  border-bottom-right-radius: 0;
  border-right: none;
}

.button-group-unified :deep(.btn-group-right) {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
  border-left: 1px solid #e5e7eb;
}

.button-group-unified :deep(.btn-group-left:hover) {
  border-right-color: #527de5;
}

.button-group-unified :deep(.btn-group-right:hover) {
  border-left-color: #527de5;
}

.btn-refresh :deep(.btn-icon svg) {
  transition: transform 0.2s ease;
}

.btn-refresh:hover :deep(.btn-icon svg) {
  transform: rotate(180deg);
}

/* Индикатор активных задач импорта */
.active-tasks-indicator {
  position: fixed;
  bottom: 20px;
  right: 20px;
  z-index: 999;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  padding: 12px;
  min-width: 200px;
  max-width: 300px;
  border: 1px solid #e5e7eb;
}

.tasks-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #eff6ff;
  border-radius: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #1e40af;
}

.tasks-icon {
  font-size: 16px;
}

.tasks-count {
  background: #3b82f6;
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 700;
}

.tasks-text {
  flex: 1;
}

.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 12px;
  text-align: left;
  width: 100%;
}

.task-item:hover {
  background: #f3f4f6;
  border-color: #3b82f6;
  transform: translateX(-2px);
}

.task-item.active {
  background: #eff6ff;
  border-color: #3b82f6;
  color: #1e40af;
}

.task-icon {
  font-size: 14px;
}

.task-info {
  flex: 1;
  font-weight: 500;
  color: #374151;
}

.task-item.active .task-info {
  color: #1e40af;
  font-weight: 600;
}

.task-status-badge {
  font-size: 10px;
  padding: 2px 6px;
  background: #f3f4f6;
  color: #6b7280;
  border-radius: 4px;
  font-weight: 500;
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

.empty-btn {
  margin-top: 8px;
}

.assets-content {
  margin-top: 0;
}

</style>