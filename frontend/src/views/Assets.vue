<script setup>
import { ref, computed, onMounted } from "vue";
import { storeToRefs } from 'pinia';
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
import ContextMenu from '../components/base/ContextMenu.vue';
import { useModals } from '../composables/useModal';
import portfolioService from '../services/portfolioService';
import CvPageHead from '../cabinet/ui/CvPageHead.vue';
import CvKpiStrip from '../cabinet/ui/CvKpiStrip.vue';
import DashboardSkeleton from '../cabinet/dashboard/DashboardSkeleton.vue';
import StructureBar from '../cabinet/assets/StructureBar.vue';
import HoldingsPanel from '../cabinet/assets/HoldingsPanel.vue';
import { toHolding } from '../cabinet/assets/holdings';
import { flattenPortfolioTree } from '../cabinet/portfolioTree';
import { money, pct, plural } from '../cabinet/format';

const selectedAsset = ref(null);

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

const refreshPortfolio = async (portfolioId) => {
  // Предотвращаем повторный запуск, если пользователь нажал несколько раз
  if (!portfolioId) return
  if (updatingPortfolios.value.has(portfolioId)) return

  updatingPortfolios.value.add(portfolioId)
  try {
    await portfoliosStore.refreshPortfolio(portfolioId)
    await reloadDashboard()
  } finally {
    updatingPortfolios.value.delete(portfolioId)
  }
}

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
const handleImportComplete = async () => {
  // Обновляем данные после успешного импорта; модалка закроется сама
  await reloadDashboard();
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

// showSoldAssets хранится в ui.store (с авто-persistence)
const { showSoldAssets } = storeToRefs(uiStore)

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

const portfolios = computed(() => dashboardStore.portfolios ?? []);
const reference = computed(() => dashboardStore.referenceData ?? {});

// Функция обновления всех портфелей с подключением
const updatingPortfolios = ref(new Set());
const refreshingAll = ref(false);

const refreshPortfolios = async () => {
  if (refreshingAll.value) return
  refreshingAll.value = true
  const importPromises = portfolios.value.map(async (p) => {
    if (!p.connection?.broker_id) return
    updatingPortfolios.value.add(p.id)
    try {
      const cred = await portfolioService.getBrokerCredentials(p.id)
      if (!cred?.api_key) return
      await importPortfolio({
        broker_id: cred.broker_id,
        token: cred.api_key,
        portfolioId: p.id,
        portfolio_name: null
      }, true)
    } catch {
      // Нет ключа или ошибка сети — пропускаем портфель
    } finally {
      updatingPortfolios.value.delete(p.id)
    }
  });

  try {
    await Promise.all(importPromises);
    await reloadDashboard();
  } finally {
    refreshingAll.value = false
  }
};

const hasBroker = computed(() => portfolios.value.some((p) => p.connection?.broker_id));

// Обработчики для контекстного меню
const handleAddTransaction = (asset) => {
  selectedAsset.value = asset;
  openModal('addTransaction');
};

const handleAddPrice = (asset) => {
  // Цену можно менять только у кастомного актива (is_custom === true)
  const assetData = asset?.asset || asset;
  if (assetData?.is_custom === false || asset?.is_custom === false) {
    console.warn('Попытка изменить цену системного актива:', assetData)
    return;
  }
  selectedAsset.value = asset;
  openModal('addPrice');
};

const handleMoveAsset = (asset) => {
  // У актива должен быть portfolio_id — если его нет, ищем портфель по portfolio_asset_id
  if (!asset.portfolio_id && asset.portfolio_asset_id) {
    const portfolio = portfolios.value.find(p =>
      p.assets && p.assets.some(a => a.portfolio_asset_id === asset.portfolio_asset_id)
    )
    if (portfolio) {
      asset.portfolio_id = portfolio.id
    }
  }
  selectedAsset.value = asset;
  openModal('moveAsset');
};

// ── выбранная ветка дерева ────────────────────────────────────────────────
const nodes = computed(() => {
  const flat = flattenPortfolioTree(portfolios.value)
  const start = flat.findIndex((n) => n.portfolio.id === uiStore.selectedPortfolioId)
  if (start < 0) return flat
  const base = flat[start].depth
  const out = [flat[start]]
  for (let i = start + 1; i < flat.length && flat[i].depth > base; i++) out.push(flat[i])
  return out.map((n) => ({ ...n, depth: n.depth - base }))
})
const selectedPortfolio = computed(() => nodes.value[0]?.portfolio || null)

const holdings = computed(() =>
  nodes.value.flatMap(({ portfolio }) => (portfolio.assets || []).map((a) => toHolding(a, portfolio)).filter((r) => !r.sold)),
)
const cash = computed(() => nodes.value.reduce((s, n) => s + (Number(n.portfolio.balance) || 0), 0))

const kpis = computed(() => {
  const value = holdings.value.reduce((s, r) => s + r.value, 0)
  const profit = holdings.value.reduce((s, r) => s + r.profit, 0)
  const day = holdings.value.reduce((s, r) => s + r.day, 0)
  const invested = value - profit
  const prev = value - day
  return [
    { key: 'value', label: 'Стоимость позиций', value, format: (v) => money(v), note: `${holdings.value.length} ${plural(holdings.value.length, 'позиция', 'позиции', 'позиций')}` },
    { key: 'cash', label: 'Свободные деньги', value: cash.value, format: (v) => money(v), note: value + cash.value > 0 ? `${pct((cash.value / (value + cash.value)) * 100, { sign: false })} капитала` : '' },
    { key: 'profit', label: 'Прибыль с покупки', value: profit, format: (v) => money(v, { sign: true }), tone: profit > 0 ? 'up' : profit < 0 ? 'down' : '', note: invested > 0 ? `${pct((profit / invested) * 100)} к вложенному` : '' },
    { key: 'day', label: 'За день', value: day, format: (v) => money(v, { sign: true }), tone: day > 0 ? 'up' : day < 0 ? 'down' : '', note: prev > 0 ? pct((day / prev) * 100, { digits: 2 }) : '' },
  ]
})

const meta = computed(() => {
  const n = nodes.value.length
  const list = [`${n} ${plural(n, 'портфель', 'портфеля', 'портфелей')}`]
  const types = new Set(holdings.value.map((r) => r.type)).size
  if (types) list.push(`${types} ${plural(types, 'тип активов', 'типа активов', 'типов активов')}`)
  return list
})

const activeTasks = computed(() => importTasksStore.getActiveTasks())

// каскадное появление — только при первом показе
const intro = ref(true)
onMounted(() => setTimeout(() => { intro.value = false }, 1600))
</script>

<template>
  <div class="as">
    <CvPageHead :eyebrow="selectedPortfolio?.name || 'Портфели'" title="Активы" :meta="portfolios.length ? meta : []">
      <template #actions>
        <button type="button" class="cv-btn" @click="openModal('import')">
          <Upload :size="15" /> Импорт
        </button>
        <button
          v-if="hasBroker"
          type="button"
          class="cv-btn cv-btn--icon as__refresh"
          :class="{ 'is-busy': refreshingAll }"
          title="Обновить портфели из брокеров"
          aria-label="Обновить портфели из брокеров"
          @click="refreshPortfolios"
        >
          <RefreshCw :size="15" />
        </button>
        <button type="button" class="cv-btn" @click="openModal('addPortfolio')">
          <FolderPlus :size="15" /> Портфель
        </button>
        <button type="button" class="cv-btn cv-btn--primary" @click="openModal('addAsset')">
          <Plus :size="15" /> Добавить актив
        </button>
      </template>
    </CvPageHead>

    <DashboardSkeleton v-if="uiStore.loading" />

    <div v-else-if="!portfolios.length" class="as__empty cv-card">
      <span class="as__empty-ic"><FolderPlus :size="22" /></span>
      <b>У вас пока нет портфелей</b>
      <p>Создайте первый портфель или импортируйте его из брокера, чтобы начать отслеживать активы.</p>
      <div class="as__empty-act">
        <button type="button" class="cv-btn" @click="openModal('import')"><Upload :size="15" /> Импорт</button>
        <button type="button" class="cv-btn cv-btn--primary" @click="openModal('addPortfolio')"><FolderPlus :size="15" /> Создать портфель</button>
      </div>
    </div>

    <div v-else class="cv-grid" :class="{ 'is-intro': intro }">
      <CvKpiStrip class="is-xl" :items="kpis" :style="{ '--i': 0 }" />
      <StructureBar v-if="holdings.length" class="is-xl" :rows="holdings" :cash="cash" :style="{ '--i': 1 }" />
      <HoldingsPanel
        v-model:show-sold="showSoldAssets"
        class="is-xl"
        :style="{ '--i': 2 }"
        :nodes="nodes"
        :updating="updatingPortfolios"
      />
    </div>

    <ContextMenu
      @clearPortfolio="clearPortfolio"
      @refreshPortfolio="refreshPortfolio"
      @deletePortfolio="deletePortfolio"
      @removeAsset="removeAsset"
      @addTransaction="handleAddTransaction"
      @addPrice="handleAddPrice"
      @moveAsset="handleMoveAsset"
    />

    <!-- активные задачи импорта -->
    <div v-if="activeTasks.length" class="as__tasks">
      <div class="as__tasks-head">
        <RefreshCw :size="14" class="as__tasks-spin" />
        <span>Импорт</span>
        <b>{{ activeTasks.length }}</b>
      </div>
      <button
        v-for="taskId in activeTasks"
        :key="taskId"
        type="button"
        class="as__task"
        :class="{ 'is-on': currentImportTaskId === taskId }"
        @click="openTaskModal(taskId)"
      >
        <span>{{ importTasksStore.getTaskInfo(taskId)?.portfolioName || `Задача #${taskId}` }}</span>
        <small v-if="!importTasksStore.isModalOpen(taskId)">свёрнуто</small>
      </button>
    </div>

    <AddAssetModal v-if="modals.addAsset" @close="closeModal('addAsset')" :onSave="addAsset" :referenceData="reference" :portfolios="portfolios"/>
    <AddPortfolioModal v-if="modals.addPortfolio" @close="closeModal('addPortfolio')" :onSave="addPortfolio" :portfolios="portfolios"/>
    <AddTransactionModal v-if="modals.addTransaction" :asset="selectedAsset" :onSubmit="addTransaction" @close="closeModal('addTransaction')"/>
    <AddPriceModal v-if="modals.addPrice" :asset="selectedAsset" :onSubmit="addPrice" @close="closeModal('addPrice')"/>
    <MoveAssetModal v-if="modals.moveAsset" :asset="selectedAsset" :portfolios="portfolios" :onSubmit="moveAsset" @close="closeModal('moveAsset')"/>
    <ImportPortfolioModal v-if="modals.import" @close="closeModal('import')" :onImport="importPortfolio" />
    <ImportStatusModal
      v-if="modals.importStatus && currentImportTaskId"
      :taskId="currentImportTaskId"
      @close="closeTaskModal"
      :onComplete="handleImportComplete"
      :onError="handleImportError"
    />
  </div>
</template>

<style scoped>
.as { padding-bottom: 8px; }
.as :deep(.cv-ph__actions .cv-btn) { gap: 7px; }
.as__refresh svg { transition: transform .5s var(--cv-ease); }
.as__refresh:hover svg { transform: rotate(180deg); }
.as__refresh.is-busy svg { animation: as-spin 1s linear infinite; }

.as__empty { display: flex; flex-direction: column; align-items: center; gap: 10px; padding: 56px 16px; text-align: center; }
.as__empty-ic { display: grid; place-items: center; width: 48px; height: 48px; margin-bottom: 4px; border-radius: 14px; color: var(--cv-accent-ink); background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line); }
.as__empty b { font-size: 15px; color: var(--cv-ink); }
.as__empty p { max-width: 420px; margin: 0; font-size: 13.5px; color: var(--cv-mut); }
.as__empty-act { display: flex; gap: 8px; margin-top: 8px; }
.as__empty-act .cv-btn { gap: 7px; }

.as__tasks {
  position: fixed; right: 20px; bottom: 20px; z-index: 50;
  display: flex; flex-direction: column; gap: 4px; width: 260px; padding: 10px;
  border-radius: 14px; background: #15161b; box-shadow: inset 0 0 0 1px var(--cv-line-2), var(--cv-pop-shadow);
}
.as__tasks-head { display: flex; align-items: center; gap: 8px; padding: 4px 6px 8px; font-size: 12.5px; font-weight: 600; color: var(--cv-ink); }
.as__tasks-head b { margin-left: auto; min-width: 20px; padding: 1px 6px; border-radius: 9px; background: var(--cv-accent); color: #fff; font-size: 11px; text-align: center; }
.as__tasks-spin { color: var(--cv-accent-ink); animation: as-spin 1.4s linear infinite; }
.as__task {
  display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%;
  padding: 8px 10px; border: 0; border-radius: 9px; background: rgba(255, 255, 255, .03);
  color: var(--cv-ink-2); font-size: 12.5px; text-align: left; cursor: pointer; transition: background .15s;
}
.as__task:hover { background: var(--cv-hover); color: var(--cv-ink); }
.as__task.is-on { background: var(--cv-accent-soft); color: var(--cv-accent-ink); }
.as__task span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.as__task small { flex: none; font-size: 11px; color: var(--cv-dim); }

@keyframes as-spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .as :deep(.cv-ph__actions) { width: 100%; }
  .as :deep(.cv-ph__actions .cv-btn--primary) { flex: 1; justify-content: center; }
  .as__tasks { left: 16px; right: 16px; bottom: calc(var(--cv-bottom-h) + 12px); width: auto; }
}
</style>
