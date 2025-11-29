<script setup>
import { ref, onMounted, provide, watch } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'
import { fetchDashboardData } from '../services/dashboardService.js'
import assetsService from "../services/assetsService";
import portfolioService from '../services/portfolioService'
import transactionsService from '../services/transactionsService.js';
import analyticsService from '../services/analyticsService.js';

import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const dashboardData = ref(null)
const loading = ref(true)
const router = useRouter()

// 🔹 Универсальная перезагрузка Dashboard
const reloadDashboard = async () => {
  try {
    loading.value = true
    dashboardData.value = await fetchDashboardData()
    console.log(dashboardData.value)
  } catch (err) {
    console.error('Ошибка получения данных Dashboard:', err)
    // Показываем пользователю понятное сообщение об ошибке
    if (err.code === 'ERR_NETWORK' || err.message?.includes('Network Error')) {
      console.error('Не удалось подключиться к серверу. Убедитесь, что backend запущен на http://localhost:5000')
    }
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

// 🔹 Активы
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

      reloadDashboard().catch(err => console.error('Ошибка фоновой перезагрузки:', err))
    }
  } catch (err) {
    console.error('Ошибка добавления актива:', err)
  }
}

// 🔹 Портфели
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
const deletePortfolio = async ( portfolioId ) => {
  try {
    const res = await portfolioService.deletePortfolio(portfolioId)
    if (!res.success) throw new Error(res.error || 'Ошибка удаления портфеля')
    dashboardData.value.data.portfolios = dashboardData.value.data.portfolios.filter(p => p.id !== portfolioId)

  } catch (err) {
    console.error('Ошибка удаления портфеля:', err)
  }
}
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

const analyticsLoaded = ref(false)
const loadAnalytics = async () => {
  if (analyticsLoaded.value) return

  try {
    const res = await analyticsService.getAnalytics()

    // ✅ Безопасно достаём массив из res.analytics
    const analyticsArray = Array.isArray(res?.analytics) ? res.analytics : []

    if (!dashboardData.value?.data) {
      dashboardData.value = { data: {} }
    }

    dashboardData.value.data.analytics = [
      ...(dashboardData.value.data.analytics || []),
      ...analyticsArray
    ]

    analyticsLoaded.value = true

  } catch (err) {
    console.error("❌ Ошибка загрузки аналитики:", err)
  }
}


// Добавление изменения цены актива
const addPrice = async ({ asset_id, price, date }) => {
  try {
    await assetsService.addPrice(asset_id, price, date)
    loading.value = true
    await reloadDashboard()
  } catch (err) {
    console.error('Ошибка добавления цены:', err)
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

  } catch (err) {
    console.error('Ошибка обновления цели портфеля:', err);
  }
}


// 🔹 Инициализация при загрузке
// Router guard уже проверил токен, поэтому здесь просто загружаем данные пользователя
onMounted(async () => {
  try {
    // Получаем данные пользователя из токена (router guard уже проверил валидность)
    const u = await authService.checkToken();
    if (u && u.user) {
      user.value = u.user;
    } else {
      // Если по какой-то причине пользователь не найден, перенаправляем на логин
      authService.logout();
      router.push('/login');
      return;
    }
    
    loading.value = true;
    await reloadDashboard();
  } catch (err) {
    console.error('Ошибка при загрузке данных:', err);
    // При ошибке сети не перенаправляем на логин, просто показываем ошибку
    if (err.code !== 'ERR_NETWORK') {
      authService.logout();
      router.push('/login');
    }
  } finally {
    loading.value = false;
  }
})


// === Управление выбранным портфелем ===
// 1. Пытаемся считать из localStorage сохраненный ID
const storedPortfolioId = localStorage.getItem('selectedPortfolioId')
const globalSelectedPortfolioId = ref(storedPortfolioId ? Number(storedPortfolioId) : null)

// 2. Функция для обновления выбора
const setPortfolioId = (id) => {
  globalSelectedPortfolioId.value = id
  localStorage.setItem('selectedPortfolioId', id)
}

// 3. Следим за данными: если выбранного портфеля нет (или он удален), выбираем первый доступный
watch(() => dashboardData.value, (newData) => {
  const portfolios = newData?.data?.portfolios || []
  if (portfolios.length > 0) {
    // Если ничего не выбрано ИЛИ выбранный ID не найден в списке (например, был удален)
    const exists = portfolios.find(p => p.id === globalSelectedPortfolioId.value)
    if (!globalSelectedPortfolioId.value || !exists) {
      setPortfolioId(portfolios[0].id)
    }
  }
}, { immediate: true })


// 👇 передаём всё дочерним страницам
provide('user', user)
provide('dashboardData', dashboardData)
provide('loading', loading)
provide('reloadDashboard', reloadDashboard)
provide('addAsset', addAsset)
provide('addTransaction', addTransaction)
provide('editTransaction', editTransaction)
provide('deleteTransactions', deleteTransactions)
provide('addPrice', addPrice)
provide('removeAsset', removeAsset)
provide('addPortfolio', addPortfolio)
provide('deletePortfolio', deletePortfolio)
provide('clearPortfolio', clearPortfolio)
provide('importPortfolio', importPortfolio)
provide('updatePortfolioGoal', updatePortfolioGoal)
provide("preloadTransactions", preloadTransactions)
provide('loadAnalytics', loadAnalytics)

provide('globalSelectedPortfolioId', globalSelectedPortfolioId)
provide('setPortfolioId', setPortfolioId)


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
