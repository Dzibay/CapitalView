<script setup>
import { ref, onMounted, provide } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'
import { fetchDashboardData } from '../services/dashboardService.js'
import assetsService from "../services/assetsService";
import portfolioService from '../services/portfolioService'
import transactionsService from '../services/transactionsService.js';

import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const dashboardData = ref(null)
const loading = ref(true)
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

// 🔹 Фоновая подгрузка транзакций за последние 6 месяцев
const transactionsLoaded = ref(false)

const preloadTransactions = async () => {
  if (transactionsLoaded.value) return // уже загружали
  try {
    const data = await transactionsService.getTransactions({})
    dashboardData.value.data.transactions = [
      ...(dashboardData.value.data.transactions || []),
      ...data
    ]
    transactionsLoaded.value = true
  } catch (err) {
    console.error("Ошибка фоновой загрузки транзакций:", err)
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

// 🔹 Транзакции
const addTransaction = async ({ asset_id, portfolio_asset_id, transaction_type, quantity, price, date }) => {
  try {
    await transactionsService.addTransaction(asset_id, portfolio_asset_id, transaction_type, quantity, price, date)
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка добавления транзакции:', err)
  }
}
const editTransaction = async (updated_transaction) => {
  try {
    await transactionsService.editTransaction(updated_transaction)
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка редактирования транзакции:', err)
  }
}
const deleteTransactions = async (transaction_ids) => {
  try {
    await transactionsService.deleteTransactions(transaction_ids)
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка удаления транзакций:', err)
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
const importPortfolio = async ({ broker_id, token, portfolioId, portfolio_name }) => {
  try {
    const res = await portfolioService.importPortfolio(broker_id, token, portfolioId, portfolio_name)
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

    // Сохраняем объект из ответа
    const updated = res[0];

    // Получаем список портфелей
    const portfolios = dashboardData.value.data.portfolios;

    // Ищем нужный портфель по id
    const targetPortfolio = portfolios.find(p => p.id === portfolioId);
    if (!targetPortfolio) {
      console.warn(`Портфель с id=${portfolioId} не найден`);
      return;
    }

    // Обновляем реактивно поля
    Object.assign(targetPortfolio, {
      description: updated.description,
      capital_target_name: updated.capital_target_name,
      capital_target_value: updated.capital_target_value,
      capital_target_currency: updated.capital_target_currency
    });

    console.log('Цель обновлена для портфеля:', targetPortfolio);
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
provide('editTransaction', editTransaction)
provide('deleteTransactions', deleteTransactions)
provide('removeAsset', removeAsset)
provide('addPortfolio', addPortfolio)
provide('deletePortfolio', deletePortfolio)
provide('clearPortfolio', clearPortfolio)
provide('importPortfolio', importPortfolio)
provide('updatePortfolioGoal', updatePortfolioGoal)
provide("preloadTransactions", preloadTransactions)

const isSidebarCollapsed = ref(false)

function toggleSidebar() {
  isSidebarCollapsed.value = !isSidebarCollapsed.value
}

</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :user="user" :collapsed="isSidebarCollapsed" />
    <main class="main-content" :class="{ 'full-width': isSidebarCollapsed }">
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
  margin-left: var(--sidebarWidthCollapsed);
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
}
</style>
