<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router';
import { Bell } from 'lucide-vue-next'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import PortfolioSelector from '../components/PortfolioSelector.vue'
import MissedPayoutsModal from '../components/modals/MissedPayoutsModal.vue'
import ReferenceAssetSearch from '../components/ReferenceAssetSearch.vue'

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

const headerSearchQuery = ref('')

function onSelectHeaderAsset(asset) {
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
      <ReferenceAssetSearch
        v-model="headerSearchQuery"
        variant="header"
        input-type="search"
        @select="onSelectHeaderAsset"
      />
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

.header-asset-search > :deep(.ref-asset-search) {
  width: 100%;
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

  .header-asset-search :deep(.ref-asset-search__input--header) {
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
