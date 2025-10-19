<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'
import { fetchDashboardData } from '../services/dashboardService.js'
import assetsService from "../services/assetsService";
import portfolioService from '../services/portfolioService'
import transactionService from '../services/transactionService.js';

import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const dashboardData = ref(null)
const loading = ref(true)
const isSidebarVisible = ref(true)
const router = useRouter()

// 🔹 Универсальная перезагрузка Dashboard
const reloadDashboard = async () => {
  try {
    dashboardData.value = await fetchDashboardData()
  } catch (err) {
    console.error('Ошибка получения данных Dashboard:', err)
  } finally {
    loading.value = false
  }
}

// 🔹 Добавление/обновление актива
const addAsset = async (assetData) => {
  try {
    const res = await assetsService.addAsset(assetData)
    if (res.success && res.asset) {
      const newAsset = res.asset

      // Находим нужный портфель
      const portfolio = dashboardData.value.data.portfolios.find(
        p => p.id === assetData.portfolio_id
      )

      if (portfolio) {
        // Если у портфеля нет assets, создаём пустой массив
        if (!portfolio.assets) portfolio.assets = []

        // Ищем, есть ли уже этот актив в портфеле
        const existingAsset = portfolio.assets.find(a => a.portfolio_asset_id === newAsset.portfolio_asset_id)

        if (existingAsset) {
          // Обновляем количество, среднюю цену и суммарную стоимость
          existingAsset.quantity = newAsset.quantity
          existingAsset.average_price = newAsset.average_price
          existingAsset.last_price = newAsset.last_price
          existingAsset.total_value = Math.round(newAsset.quantity * newAsset.last_price * 100) / 100
        } else {
          // Добавляем новый актив
          portfolio.assets.push({
            ...newAsset,
            total_value: Math.round(newAsset.quantity * newAsset.last_price * 100) / 100
          })
        }
      } else {
        console.warn("Портфель не найден для добавления актива")
      }

      console.log("Актив обновлён/добавлен локально:", newAsset)
      reloadDashboard().catch(err => console.error('Ошибка фоновой перезагрузки:', err))
    }
  } catch (err) {
    console.error('Ошибка добавления актива:', err)
  }
}

// 🔹 Добавление портфеля
const addPortfolio = async (portfolioData) => {
  try {
    const res = await portfolioService.addPortfolio(portfolioData)
    if (res.success) {
      // добавляем новый портфель напрямую в локальный стейт
      dashboardData.value.data.portfolios.push(res.portfolio)
    }
  } catch (err) {
    console.error('Ошибка создания портфеля:', err)
  }
}

// 🔹 Очистка портфеля
const deletePortfolio = async ( portfolioId ) => {
  try {
    const res = await portfolioService.deletePortfolio(portfolioId)
    if (!res.success) throw new Error(res.error || 'Ошибка удаления портфеля')
    dashboardData.value.data.portfolios = dashboardData.value.data.portfolios.filter(p => p.id !== portfolioId)

  } catch (err) {
    console.error('Ошибка удаления портфеля:', err)
  }
}

// 🔹 Очистка портфеля
const clearPortfolio = async ( portfolioId ) => {
  try {
    loading.value = true
    const res = await portfolioService.clearPortfolio(portfolioId)
    if (!res.success) throw new Error(res.error || 'Ошибка очистки портфеля')
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка очистки портфеля:', err)
  }
}

// 🔹 Продажа актива
const addTransaction = async ({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date }) => {
  console.log(asset_id, portfolio_asset_id, transaction_type, quantity, price, date)
  try {
    await transactionService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, date)
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка добавления транзакции:', err)
  }
}

// 🔹 Удаление актива
const removeAsset = async (portfolioAssetId) => {
  if (!confirm("Удалить актив?")) return
  try {
    const res = await assetsService.deleteAsset(portfolioAssetId)
    if (!res.success) throw new Error(res.error || 'Ошибка удаления актива')
    
    // --- Локальное удаление ---
    dashboardData.value.data.portfolios.forEach(portfolio => {
      if (portfolio.assets) {
        portfolio.assets = portfolio.assets.filter(
          asset => asset.portfolio_asset_id !== portfolioAssetId
        )
      }
    })

    console.log("Актив удалён локально:", portfolioAssetId)
    await reloadDashboard()
    
  } catch (err) {
    console.error('Ошибка удаления актива:', err)
  }
}

// 🔹 Импорт портфеля из Tinkoff
const importPortfolio = async ({ token, portfolioId, portfolio_name }) => {
  try {
    const res = await portfolioService.importPortfolio(token, portfolioId, portfolio_name)
    if (!res.success) throw new Error(res.error || 'Ошибка импорта портфеля')
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка импорта портфеля:', err)
  }
}

// 🔹 Обновление цели портфеля
const updatePortfolioGoal = async ({ portfolioId, title, targetAmount }) => {
  try {
    const res = await portfolioService.updatePortfolioGoal(portfolioId, { title, targetAmount });
    if (!res) throw new Error('Ошибка при обновлении цели');
    dashboardData.value.data.main_portfolio_description = res[0]["description"]
    // Перезагружаем дашборд, чтобы отобразить новые данные
    
  } catch (err) {
    console.error('Ошибка обновления цели портфеля:', err);
  }
}


// 🔹 Инициализация при загрузке
onMounted(async () => {
  try {
    const u = await authService.checkToken()
    if (!u) {
      router.push('/login')
      return
    }
    user.value = u.user
    loading.value = true
    await reloadDashboard()
    console.log('✅ Dashboard данные загружены', dashboardData.value)
  } catch (err) {
    console.error('Ошибка при авторизации:', err)
    authService.logout()
    router.push('/login')
  } finally {
    loading.value = false
  }
})

// 👇 передаём всё дочерним страницам
provide('user', user)
provide('dashboardData', dashboardData)
provide('loading', loading)
provide('reloadDashboard', reloadDashboard)
provide('addAsset', addAsset)
provide('addTransaction', addTransaction)
provide('removeAsset', removeAsset)
provide('addPortfolio', addPortfolio)
provide('deletePortfolio', deletePortfolio)
provide('clearPortfolio', clearPortfolio)
provide('importPortfolio', importPortfolio)
provide('updatePortfolioGoal', updatePortfolioGoal)

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
