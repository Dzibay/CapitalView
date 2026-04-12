<script setup>
import { ref, computed, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router';
import { Bell, Search, Loader2 } from 'lucide-vue-next'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import MissedPayoutsModal from '../components/modals/MissedPayoutsModal.vue'
import { searchReferenceAssets } from '../services/referenceService'

defineProps({
  user: {
    type: Object,
    required: true,
  },
  sidebarCollapsed: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(['toggle-sidebar'])
const router = useRouter();
const showMissedPayoutsModal = ref(false)
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()
const missedPayoutsCount = computed(() => dashboardStore.missedPayoutsCount || 0)
const headerPortfolios = computed(() => dashboardStore.portfolios ?? [])

const handleToggle = () => {
  emit('toggle-sidebar');
};

// Открываем модалку
const openMissedPayoutsModal = () => {
  showMissedPayoutsModal.value = true
}

const closeMissedPayoutsModal = () => {
  showMissedPayoutsModal.value = false
  // Обновляем dashboard для обновления счетчика неполученных выплат
  dashboardStore.fetchDashboard(true, false)
}

// Обработчики событий от модалки
const handlePayoutsAdded = () => {
  // Обновляем dashboard для обновления счетчика неполученных выплат
  dashboardStore.fetchDashboard(true, false)
}

const handlePayoutsIgnored = () => {
  // Обновляем dashboard для обновления счетчика неполученных выплат
  dashboardStore.fetchDashboard(true, false)
}

const hasNotifications = computed(() => missedPayoutsCount.value > 0)

/** Поиск актива (та же логика, что в AddAssetModal: debounce 280ms, от 2 символов, searchReferenceAssets) */
const headerSearchQuery = ref('')
const headerSearchResults = ref([])
const headerSearchLoading = ref(false)
const headerSearchPanelOpen = ref(false)
let headerSearchDebounceTimer = null
let headerSearchRequestSeq = 0

watch(headerSearchQuery, () => {
  clearTimeout(headerSearchDebounceTimer)
  const q = headerSearchQuery.value.trim()
  if (q.length < 2) {
    headerSearchResults.value = []
    headerSearchLoading.value = false
    return
  }
  headerSearchLoading.value = true
  headerSearchDebounceTimer = setTimeout(async () => {
    const seq = ++headerSearchRequestSeq
    try {
      const items = await searchReferenceAssets(q, 25)
      if (seq === headerSearchRequestSeq) headerSearchResults.value = items
    } catch (e) {
      console.error(e)
      if (seq === headerSearchRequestSeq) headerSearchResults.value = []
    } finally {
      if (seq === headerSearchRequestSeq) headerSearchLoading.value = false
    }
  }, 280)
})

onUnmounted(() => {
  clearTimeout(headerSearchDebounceTimer)
})

function openHeaderSearchPanel() {
  headerSearchPanelOpen.value = true
}

function closeHeaderSearchPanelSoon() {
  setTimeout(() => {
    headerSearchPanelOpen.value = false
  }, 200)
}

function onSelectHeaderAsset(asset) {
  headerSearchQuery.value = ''
  headerSearchResults.value = []
  headerSearchLoading.value = false
  headerSearchPanelOpen.value = false
  router.push(`/assets/${asset.id}`)
}
</script>

<template>
  <header class="header" :class="{ 'header--sidebar-collapsed': sidebarCollapsed }">
    <div class="header-left">
      <button @click="handleToggle" class="burger-button">
        <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="none" viewBox="0 0 30 30">
          <path fill="#000" d="m5.861 2.79.247-.001h.673l.728-.001a516.191 516.191 0 0 1 2.582-.001h.502c1.047-.002 2.095-.001 3.142 0 .958 0 1.915 0 2.872-.002a1595.764 1595.764 0 0 1 4.608-.003h3.137c.857.006 1.493.29 2.118.87.608.642.744 1.35.74 2.21l.001.246v.673l.001.728c.001.475.002.95.001 1.424v1.66c.002 1.047.001 2.095 0 3.142 0 .958 0 1.915.002 2.872a1613.494 1613.494 0 0 1 .003 4.608v3.137c-.006.857-.29 1.493-.87 2.118-.642.608-1.35.744-2.21.74l-.246.001h-.673l-.728.001-1.424.001h-1.66c-1.047.002-2.095.001-3.142 0-.958 0-1.915 0-2.872.002a1613.494 1613.494 0 0 1-4.608.003H5.649c-.858-.006-1.494-.29-2.119-.87-.608-.642-.744-1.35-.74-2.21l-.001-.246v-.673l-.001-.728a520.183 520.183 0 0 1-.001-2.582v-.502c-.002-1.047-.001-2.095 0-3.142 0-.958 0-1.915-.002-2.872a1595.764 1595.764 0 0 1-.003-4.608V5.649c.006-.858.29-1.494.87-2.119.642-.608 1.35-.744 2.21-.74Zm-.935 2.234c-.276.434-.255.858-.254 1.359v.867l-.001.686a675.997 675.997 0 0 0-.001 2.436v3.435l-.002 2.708a1897.352 1897.352 0 0 0-.003 4.344 417.803 417.803 0 0 0 0 2.008v.951c.002.406.006.846.273 1.177.91.837 3.943.317 4.085.317V4.688c-1.728-.257-1.728-.257-4.097.337Zm6.031-.337v20.625l6.676.011 2.108.005a2590.23 2590.23 0 0 0 2.08.003 269.142 269.142 0 0 0 1.454.003h.527l.154.001c.359-.002.75-.041 1.04-.273.375-.412.333-.923.332-1.445v-.867l.002-.686a601.633 601.633 0 0 0 0-2.436v-3.435l.002-2.708a1984.922 1984.922 0 0 0 .003-4.344 392.776 392.776 0 0 0 0-2.008 112.746 112.746 0 0 0 0-.951c-.002-.406-.006-.846-.273-1.177-.356-.327-.79-.335-1.246-.332h-.166a122.771 122.771 0 0 0-.956.001c-.36 0-.72 0-1.08.002h-1.012l-2.962.004-6.683.008Z"/>
        </svg>
      </button>
    </div>

    <div v-if="user && !user?.is_admin" class="header-asset-search">
      <div class="header-search-wrapper">
        <Search :size="16" class="header-search-icon" />
        <input
          v-model="headerSearchQuery"
          type="search"
          class="header-search-input"
          placeholder="Поиск актива (от 2 символов)…"
          autocomplete="off"
          @focus="openHeaderSearchPanel"
          @blur="closeHeaderSearchPanelSoon"
        />
        <ul
          v-if="headerSearchPanelOpen && headerSearchQuery.trim().length >= 2"
          class="header-search-dropdown"
        >
          <li v-if="headerSearchLoading" class="header-search-dropdown-msg">
            <Loader2 :size="18" class="header-search-spinner" />
            <span>Поиск…</span>
          </li>
          <template v-else>
            <li
              v-for="a in headerSearchResults"
              :key="a.id"
              class="header-search-item"
              @mousedown.prevent="onSelectHeaderAsset(a)"
            >
              <div class="header-search-item-row">
                <span class="header-search-name">{{ a.name }}</span>
                <span class="header-search-ticker">{{ a.ticker || '—' }}</span>
              </div>
            </li>
            <li v-if="headerSearchResults.length === 0" class="header-search-dropdown-msg">
              <Search :size="18" class="header-search-empty-icon" />
              <span>Актив не найден</span>
            </li>
          </template>
        </ul>
      </div>
    </div>

    <div v-if="user" class="header-right">
      <!-- Мобильный Teleport-цель; селектор монтируется в обёртке ниже и всегда в дереве layout -->
      <div id="app-header-mobile-end" class="header-mobile-end" />
      <div
        v-if="!user?.is_admin && headerPortfolios.length > 0"
        class="header-portfolio-select-wrap"
      >
        <PortfolioSelector
          :portfolios="headerPortfolios"
          :model-value="uiStore.selectedPortfolioId"
          @update:model-value="uiStore.setSelectedPortfolioId"
        />
      </div>
      <div class="header-user-cluster">
        <button
          v-if="!user?.is_admin"
          type="button"
          @click="openMissedPayoutsModal"
          class="notifications-button"
          :class="{ 'has-notifications': hasNotifications }"
          title="Неполученные выплаты"
        >
          <Bell :size="20" />
          <span v-if="hasNotifications" class="notification-badge">
            {{ missedPayoutsCount > 99 ? '99+' : missedPayoutsCount }}
          </span>
        </button>

        <div class="user-profile">
          <img src="https://cdn-icons-png.flaticon.com/512/6998/6998058.png " alt="User Avatar" class="avatar">
        </div>
      </div>
    </div>

    <!-- Модальное окно неполученных выплат -->
    <MissedPayoutsModal 
      :show="showMissedPayoutsModal" 
      @close="closeMissedPayoutsModal"
      @payouts-added="handlePayoutsAdded"
      @payouts-ignored="handlePayoutsIgnored"
    />
  </header>
</template>

<style scoped>
.header {
  position: fixed;
  top: 0;
  left: var(--sidebarWidth);
  right: 0;
  height: var(--headerHeight);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px var(--spacing);
  background-color: #fff;
  transition: left 0.3s ease-in-out;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  z-index: 999;
  overflow: visible;
}

.header-left {
  flex-shrink: 0;
}

.header-right {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: calc(var(--spacing) / 2);
  margin-left: auto;
}

/* Десктоп: селектор в шапке; на ≤768px контент уезжает в Teleport — обёртку скрываем */
.header-portfolio-select-wrap {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.header-asset-search {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  justify-content: center;
  max-width: 440px;
}

.header-search-wrapper {
  position: relative;
  width: 100%;
}

.header-search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #9ca3af;
  z-index: 1;
}

.header-search-input {
  width: 100%;
  height: 40px;
  padding: 0 14px 0 38px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.header-search-input::placeholder {
  color: #9ca3af;
}

.header-search-input:hover {
  border-color: #d1d5db;
}

.header-search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.header-search-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  /* Правый край совпадает с полем — при min-width список расширяется влево, не наезжая на портфель */


  width: max(100%, 260px);
  max-width: min(400px, calc(100vw - 24px));
  box-sizing: border-box;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12), 0 4px 10px rgba(0, 0, 0, 0.08);
  max-height: min(280px, 50vh);
  overflow-y: auto;
  z-index: 1010;
}

.header-search-item {
  padding: 10px 14px;
  cursor: pointer;
  border-left: 3px solid transparent;
  transition: background 0.15s ease, border-color 0.15s ease, padding-left 0.15s ease;
}

.header-search-item:hover {
  background: #f3f4f6;
  border-left-color: #3b82f6;
  padding-left: 11px;
}

.header-search-item-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.header-search-name {
  font-weight: 500;
  font-size: 13px;
  color: #111827;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.header-search-ticker {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
}

.header-search-dropdown-msg {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px;
  color: #9ca3af;
  font-size: 12px;
  cursor: default;
}

.header-search-spinner {
  color: #3b82f6;
  animation: header-search-spin 1s linear infinite;
}

.header-search-empty-icon {
  color: #d1d5db;
  opacity: 0.7;
}

@keyframes header-search-spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.header.header--sidebar-collapsed {
  left: var(--sidebarWidthCollapsed);
}
.burger-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.burger-button:hover {
  background-color: #f3f4f6;
}
.header-user-cluster {
  display: flex;
  gap: calc(var(--spacing) / 2);
  align-items: center;
  min-width: 0;
}

.header-mobile-end {
  display: none;
  align-items: center;
  justify-content: stretch;
  flex-shrink: 0;
}

.notifications-button {
  position: relative;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6b7280;
  transition: all 0.2s ease;
}

.notifications-button:hover {
  background-color: #f3f4f6;
  color: #3b82f6;
}

.notifications-button.has-notifications {
  color: #3b82f6;
}

.notification-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  background-color: #ef4444;
  color: white;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  border: 2px solid white;
}

.user-profile {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

@media (max-width: 768px) {
  .header {
    left: 0;
    padding-left: 12px;
    padding-right: 12px;
    gap: 8px;
  }

  .header.header--sidebar-collapsed {
    left: 0;
  }

  .header-asset-search {
    flex: 1 1 0%;
    min-width: 0;
    max-width: none;
    justify-content: stretch;
    /* overflow нельзя hidden — список результатов absolute и обрезается */
    overflow: visible;
  }

  .header-search-input {
    font-size: 13px;
  }

  .burger-button {
    display: none;
  }

  .header-left {
    display: none;
  }

  .header-portfolio-select-wrap {
    display: none;
  }

  .header-right {
    flex: 0 0 auto;
    flex-shrink: 0;
    gap: 8px;
    margin-left: 0;
    min-width: 0;
  }

  /* Порядок: портфель | колокольчик | аватар */
  .header-user-cluster {
    flex-direction: row;
    flex-shrink: 0;
    gap: 4px;
  }

  /* Фиксированная колонка под портфель — поиск забирает остаток, отступ только через gap у .header */
  .header-mobile-end {
    display: flex;
    flex: 0 0 148px;
    width: 148px;
    min-width: 148px;
    max-width: 148px;
  }

  .header-mobile-end :deep(.custom-select-wrapper) {
    width: 100%;
    max-width: 100%;
  }

  .header-mobile-end :deep(.custom-select) {
    min-height: 40px;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    padding: 0 8px;
  }

  .header-mobile-end :deep(.custom-select-value) {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

@media (max-width: 480px) {
  .header {
    padding-left: 8px;
    padding-right: 8px;
  }

  .header-mobile-end {
    flex: 0 0 124px;
    width: 124px;
    min-width: 124px;
    max-width: 124px;
  }
}
</style>
