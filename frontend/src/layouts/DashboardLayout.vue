<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'
import assetsService from "../services/assetsService";
import { fetchDashboardData } from '../services/dashboardService.js';

// Компоненты макета
import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const portfolios = ref([])
const dashboardData = ref(null)
const loading = ref(true)
const isSidebarVisible = ref(true)
const router = useRouter()

// 🔹 Загрузка активов
const loadAssets = async () => {
  try {
    const res = await assetsService.getAssets()
    portfolios.value = res || []
  } catch (err) {
    console.error('Ошибка получения активов:', err)
  }
}

// 🔹 Загрузка данных дашборда
const loadDashboard = async (user) => {
  try {
    dashboardData.value = await fetchDashboardData(user)
  } catch (err) {
    console.error('Ошибка получения данных дашборда:', err)
  }
}

// 🔹 Добавление актива
const addAsset = async (assetData) => {
  try {
    await assetsService.addAsset(assetData)
    await loadAssets()
  } catch (err) {
    console.error('Ошибка добавления актива:', err)
  }
}

// 🔹 Удаление актива
const removeAsset = async (assetId) => {
  if (!confirm("Удалить актив?")) return
  try {
    await assetsService.deleteAsset(assetId)
    await loadAssets()
  } catch (err) {
    console.error('Ошибка удаления актива:', err)
  }
}

onMounted(async () => {
  try {
    const u = await authService.checkToken()
    if (!u) {
      router.push('/login')
    } else {
      user.value = u['user']
      await loadAssets()
      await loadDashboard(user.value)
      console.log('Ураааа')
      console.log(dashboardData.value)
    }
  } catch (err) {
    console.error('Ошибка проверки токена:', err)
    authService.logout()
    router.push('/login')
  } finally {
    loading.value = false
  }
})

// 👇 передаём все реактивные данные и функции дочерним страницам
provide('user', user)
provide('portfolios', portfolios)
provide('dashboardData', dashboardData)
provide('loading', loading)
provide('reloadAssets', loadAssets)
provide('addAsset', addAsset)
provide('removeAsset', removeAsset)

function toggleSidebar() {
  isSidebarVisible.value = !isSidebarVisible.value
}

</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :class="{ 'sidebar-hidden': !isSidebarVisible }" />
    <main class="main-content" :class="{ 'full-width': !isSidebarVisible }">
      <AppHeader :user="user" @toggle-sidebar="toggleSidebar" />
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.sidebar-hidden {
  transform: translateX(-100%);
}

.main-content {
  flex-grow: 1;
  margin-left: var(--sidebarWidth);
  transition: margin-left 0.3s ease-in-out;
  min-height: 100vh;
}

.main-content.full-width {
  margin-left: 0;
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
}
</style>
