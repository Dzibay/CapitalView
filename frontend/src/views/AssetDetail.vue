<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { inject } from 'vue'
import MultiLineChart from '../components/MultiLineChart.vue'
import ChartControls from '../components/ChartControls.vue'
import assetsService from '../services/assetsService'

const route = useRoute()
const router = useRouter()

const dashboardData = inject('dashboardData')
const loading = inject('loading')

const portfolioAssetId = computed(() => parseInt(route.params.id))
const isLoading = ref(false)
const assetInfo = ref(null)
const priceHistory = ref([])
const selectedPeriod = ref('All')
const selectedChartType = ref('position') // 'position' | 'quantity' | 'price'

// Получаем информацию о портфеле из dashboardData для расчета вклада
const portfolios = computed(() => dashboardData.value?.data?.portfolios ?? [])

// Поиск портфеля и актива в нем
const portfolioAsset = computed(() => {
  if (!assetInfo.value || !portfolios.value.length) return null
  
  for (const portfolio of portfolios.value) {
    if (portfolio.assets) {
      const asset = portfolio.assets.find(a => a.portfolio_asset_id === portfolioAssetId.value)
      if (asset) {
        return { asset, portfolio }
      }
    }
  }
  return null
})

// Загрузка информации о портфельном активе
async function loadAssetInfo() {
  if (!portfolioAssetId.value) return
  
  isLoading.value = true
  try {
    const result = await assetsService.getPortfolioAssetInfo(portfolioAssetId.value)
    if (result.success && result.portfolio_asset) {
      assetInfo.value = result.portfolio_asset
      
      // Загружаем историю цен, если есть asset_id
      if (result.portfolio_asset.asset_id) {
        await loadPriceHistory(result.portfolio_asset.asset_id)
      }
    }
  } catch (error) {
    console.error('Ошибка при загрузке информации об активе:', error)
  } finally {
    isLoading.value = false
  }
}

// Загрузка истории цен
async function loadPriceHistory(assetId) {
  try {
    const result = await assetsService.getAssetPriceHistory(assetId)
    if (result.success && result.prices) {
      priceHistory.value = result.prices
    }
  } catch (error) {
    console.error('Ошибка при загрузке истории цен:', error)
  }
}

// Находим первую дату транзакции
const firstTransactionDate = computed(() => {
  if (!assetInfo.value?.transactions || !assetInfo.value.transactions.length) {
    return null
  }
  
  const dates = assetInfo.value.transactions
    .map(tx => new Date(tx.transaction_date))
    .filter(d => !isNaN(d.getTime()))
  
  if (!dates.length) return null
  
  // Находим самую раннюю дату
  const firstDate = new Date(Math.min(...dates))
  firstDate.setHours(0, 0, 0, 0)
  return firstDate.toISOString().split('T')[0]
})

// Вычисляем накопленное количество на каждую дату
const quantityByDate = computed(() => {
  if (!assetInfo.value?.transactions || !priceHistory.value?.length) {
    return {}
  }
  
  const transactions = [...assetInfo.value.transactions]
    .map(tx => ({
      ...tx,
      date: new Date(tx.transaction_date).toISOString().split('T')[0]
    }))
    .sort((a, b) => a.date.localeCompare(b.date))
  
  const quantityMap = {}
  let cumulativeQuantity = 0
  
  // Вычисляем накопленное количество для каждой даты из истории цен
  const priceDates = [...new Set(priceHistory.value.map(p => p.trade_date))].sort()
  
  let txIndex = 0
  for (const priceDate of priceDates) {
    const priceDateObj = new Date(priceDate)
    priceDateObj.setHours(0, 0, 0, 0)
    const priceDateStr = priceDateObj.toISOString().split('T')[0]
    
    // Применяем все транзакции до и включая эту дату
    while (txIndex < transactions.length) {
      const tx = transactions[txIndex]
      const txDateStr = tx.date
      
      // Сравниваем даты как строки
      if (txDateStr > priceDateStr) break
      
      // transaction_type: 1 = buy (плюс), 2 = sell (минус)
      const txQuantity = Number(tx.quantity) || 0
      if (tx.transaction_type === 1 || (typeof tx.transaction_type === 'string' && tx.transaction_type.toLowerCase() === 'buy')) {
        cumulativeQuantity += txQuantity
      } else if (tx.transaction_type === 2 || (typeof tx.transaction_type === 'string' && tx.transaction_type.toLowerCase() === 'sell')) {
        cumulativeQuantity -= txQuantity
      }
      
      txIndex++
    }
    
    quantityMap[priceDate] = Math.max(0, cumulativeQuantity) // Не даем уйти в минус
  }
  
  return quantityMap
})

// Формирование данных для графика
const chartData = computed(() => {
  if (!priceHistory.value || !priceHistory.value.length || !portfolioAsset.value) {
    return { labels: [], datasets: [] }
  }

  const asset = portfolioAsset.value.asset
  const leverage = asset.leverage || 1
  const currencyRate = asset.currency_rate_to_rub || 1

  // Фильтруем историю цен с первой транзакции только для графиков стоимости позиции и количества
  // Для графика цены единицы актива показываем полную историю
  let filteredPrices = [...priceHistory.value]
  if (firstTransactionDate.value && selectedChartType.value !== 'price') {
    filteredPrices = filteredPrices.filter(p => {
      const priceDate = new Date(p.trade_date)
      priceDate.setHours(0, 0, 0, 0)
      const firstDate = new Date(firstTransactionDate.value)
      firstDate.setHours(0, 0, 0, 0)
      return priceDate >= firstDate
    })
  }

  if (!filteredPrices.length) {
    return { labels: [], datasets: [] }
  }

  // Преобразуем историю цен в формат для графика
  const labels = filteredPrices.map(p => p.trade_date).sort()
  
  let datasets = []
  
  if (selectedChartType.value === 'position') {
    // График стоимости позиции
    const quantities = quantityByDate.value
    const data = labels.map(date => {
      const qty = quantities[date] || 0
      const price = filteredPrices.find(p => p.trade_date === date)?.price || 0
      return (qty * price / leverage) * currencyRate
    })
    
    datasets = [{
      label: 'Стоимость позиции',
      data,
      color: '#3b82f6',
      fill: true
    }]
  } else if (selectedChartType.value === 'quantity') {
    // График количества актива
    const data = labels.map(date => quantityByDate.value[date] || 0)
    
    datasets = [{
      label: 'Количество актива',
      data,
      color: '#10b981',
      fill: true
    }]
  } else if (selectedChartType.value === 'price') {
    // График цены единицы актива
    const data = labels.map(date => {
      const price = filteredPrices.find(p => p.trade_date === date)?.price || 0
      return price * currencyRate
    })
    
    datasets = [{
      label: 'Цена единицы актива',
      data,
      color: '#f59e0b',
      fill: true
    }]
  }

  return {
    labels,
    datasets
  }
})

// Форматирование для графика количества (без валюты)
const formatQuantity = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    maximumFractionDigits: 2
  })
}

// Выбираем форматтер в зависимости от типа графика
const chartFormatter = computed(() => {
  if (selectedChartType.value === 'quantity') {
    return formatQuantity
  }
  return formatCurrency
})

// Поиск корневого портфеля "Все активы" (портфель без parent_portfolio_id)
const rootPortfolio = computed(() => {
  if (!portfolios.value || !portfolios.value.length) return null
  
  // Ищем портфель без parent_portfolio_id (корневой)
  return portfolios.value.find(p => !p.parent_portfolio_id) || null
})

// Расчет вклада в портфель
const portfolioContribution = computed(() => {
  if (!portfolioAsset.value) return null
  
  const { asset, portfolio } = portfolioAsset.value
  const assetValue = (asset.quantity * (asset.last_price || 0) / (asset.leverage || 1)) * (asset.currency_rate_to_rub || 1)
  const portfolioValue = portfolio.total_value || 0
  
  if (portfolioValue === 0) return null
  
  // Расчет доли в корневом портфеле "Все активы"
  const rootValue = rootPortfolio.value?.total_value || 0
  const percentageInRoot = rootValue > 0 ? (assetValue / rootValue) * 100 : null
  
  return {
    percentage: (assetValue / portfolioValue) * 100,
    assetValue,
    portfolioValue,
    rootPortfolioValue: rootValue,
    percentageInRoot
  }
})

// Расчет прибыли/убытка
const profitLoss = computed(() => {
  if (!portfolioAsset.value) return null
  
  const asset = portfolioAsset.value.asset
  const currentPrice = asset.last_price || 0
  const averagePrice = asset.average_price || 0
  const quantity = asset.quantity || 0
  const leverage = asset.leverage || 1
  const currencyRate = asset.currency_rate_to_rub || 1

  const invested = (quantity * averagePrice / leverage) * currencyRate
  const currentValue = (quantity * currentPrice / leverage) * currencyRate
  const profit = currentValue - invested
  const profitPercent = averagePrice > 0 ? ((currentPrice - averagePrice) / averagePrice) * 100 : 0

  return {
    invested,
    currentValue,
    profit,
    profitPercent,
    isProfit: profit >= 0
  }
})

// Расчет выплат (дивиденды + купоны) из cash_operations
const payouts = computed(() => {
  if (!assetInfo.value) return null
  
  // Получаем историю выплат из cash_operations (типы 3 = дивиденды, 4 = купоны)
  // assetInfo.value уже является portfolio_asset после loadAssetInfo()
  const payoutHistory = assetInfo.value.payouts || []
  
  let dividends = 0
  let coupons = 0
  
  // Суммируем выплаты по типам
  payoutHistory.forEach(payout => {
    const payoutType = payout.type // 3 = дивиденды, 4 = купоны
    const amount = Number(payout.amount || 0)
    
    if (payoutType === 3) {
      // Дивиденды
      dividends += amount
    } else if (payoutType === 4) {
      // Купоны
      coupons += amount
    }
  })
  
  const totalPayouts = dividends + coupons
  
  return {
    history: payoutHistory,
    dividends,
    coupons,
    total: totalPayouts
  }
})

// Расчет прибыли от продаж (realized P&L)
const realizedProfit = computed(() => {
  if (!assetInfo.value?.transactions) return 0
  
  const transactions = assetInfo.value.transactions || []
  
  // Суммируем realized_pnl из транзакций продажи, если есть
  // Или вычисляем из разницы цен продажи и покупки
  let totalRealized = 0
  
  for (const tx of transactions) {
    const txType = typeof tx.transaction_type === 'number' 
      ? tx.transaction_type 
      : (tx.transaction_type?.toLowerCase() === 'sell' ? 2 : 1)
    
    // Если это продажа и есть realized_pnl
    if (txType === 2 && tx.realized_pnl) {
      totalRealized += Number(tx.realized_pnl) || 0
    }
  }
  
  // Если в данных актива есть realized_pl, используем его
  if (portfolioAsset.value?.asset?.realized_pl !== undefined) {
    return Number(portfolioAsset.value.asset.realized_pl) || 0
  }
  
  return totalRealized
})

// Рост цены (в процентах)
const priceGrowth = computed(() => {
  if (!portfolioAsset.value) return null
  
  const asset = portfolioAsset.value.asset
  const currentPrice = asset.last_price || 0
  const averagePrice = asset.average_price || 0
  
  if (averagePrice === 0) return null
  
  const growth = ((currentPrice - averagePrice) / averagePrice) * 100
  return {
    percent: growth,
    isPositive: growth >= 0
  }
})

// Общая прибыль (unrealized + realized + выплаты)
const totalProfit = computed(() => {
  if (!profitLoss.value || !payouts.value) return null
  
  const unrealizedProfit = profitLoss.value.profit || 0
  const realized = realizedProfit.value || 0
  const payoutAmount = payouts.value.total || 0
  
  const total = unrealizedProfit + realized + payoutAmount
  
  return {
    unrealized: unrealizedProfit,
    realized,
    payouts: payoutAmount,
    total,
    isProfit: total >= 0
  }
})

// Объединенный список операций (транзакции + выплаты)
const allOperations = computed(() => {
  const operations = []
  
  // Добавляем транзакции
  if (assetInfo.value?.transactions) {
    assetInfo.value.transactions.forEach(tx => {
      operations.push({
        id: `tx_${tx.id}`,
        type: 'transaction',
        date: tx.transaction_date,
        operationType: tx.transaction_type,
        quantity: tx.quantity,
        price: tx.price,
        amount: tx.price * tx.quantity || 0
      })
    })
  }
  
  // Добавляем выплаты
  if (payouts.value?.history) {
    payouts.value.history.forEach(payout => {
      operations.push({
        id: `payout_${payout.id}`,
        type: 'payout',
        date: payout.date,
        operationType: payout.type, // 3 = дивиденды, 4 = купоны
        quantity: null,
        price: null,
        amount: payout.amount || 0
      })
    })
  }
  
  // Сортируем по дате (от новых к старым)
  return operations.sort((a, b) => {
    const dateA = new Date(a.date)
    const dateB = new Date(b.date)
    return dateB - dateA
  })
})

// Форматирование валюты
const formatCurrency = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value || 0)
}

// Нормализация типа операции (как на странице Transactions)
const normalizeType = (type, opType = null) => {
  // Если это выплата (opType = 'payout'), то type это число 3 или 4
  if (opType === 'payout') {
    if (type === 3) return 'dividend'
    if (type === 4) return 'coupon'
  }
  
  // Для транзакций
  if (typeof type === 'number') {
    if (type === 1) return 'buy'
    if (type === 2) return 'sell'
  }
  
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('покуп') || t.includes('buy')) return 'buy'
    if (t.includes('прод') || t.includes('sell')) return 'sell'
    if (t.includes('див') || t.includes('div')) return 'dividend'
    if (t.includes('купон') || t.includes('coupon')) return 'coupon'
  }
  
  return 'other'
}

// Получение текстового названия типа операции для отображения
const getOperationTypeLabel = (op) => {
  if (op.type === 'payout') {
    // Для выплат: type 3 = дивиденды, 4 = купоны
    if (op.operationType === 3) return 'Дивиденды'
    if (op.operationType === 4) return 'Купоны'
    return 'Выплата'
  }
  
  // Для транзакций
  if (op.type === 'transaction') {
    if (op.operationType === 1) return 'Покупка'
    if (op.operationType === 2) return 'Продажа'
  }
  
  return String(op.operationType || '')
}

// Загрузка при монтировании
onMounted(() => {
  loadAssetInfo()
})

// Отслеживание изменений route.params.id
watch(() => route.params.id, () => {
  loadAssetInfo()
}, { immediate: false })
</script>

<template>
  <div class="asset-detail-page">
    <div v-if="isLoading || loading" class="loading-state">
      <div class="loader"></div>
      <span>Загрузка данных об активе...</span>
    </div>

    <div v-else-if="assetInfo && portfolioAsset" class="content-wrapper">
      <!-- Заголовок с кнопкой назад -->
      <div class="header-row">
        <div>
          <h1 class="page-title">{{ portfolioAsset.asset.name }}</h1>
          <div class="asset-meta-header">
            <span class="ticker">{{ portfolioAsset.asset.ticker }}</span>
            <span v-if="portfolioAsset.asset.leverage && portfolioAsset.asset.leverage > 1" class="badge-leverage">
              ×{{ portfolioAsset.asset.leverage }}
            </span>
            <span class="portfolio-name">Портфель: {{ portfolioAsset.portfolio.name }}</span>
          </div>
        </div>
        <button class="btn-back" @click="router.back()">
          ← Назад
        </button>
      </div>


      <!-- График -->
      <div class="chart-section">
        <div class="section-header">
          <h2>История актива</h2>
          <ChartControls
            :chartType="selectedChartType"
            :period="selectedPeriod"
            @update:chartType="selectedChartType = $event"
            @update:period="selectedPeriod = $event"
          />
        </div>
        <div class="chart-container">
          <MultiLineChart 
            v-if="chartData.labels.length" 
            :chartData="chartData" 
            :period="selectedPeriod"
            :formatCurrency="chartFormatter"
          />
          <div v-else class="no-chart-data">Нет данных для отображения графика</div>
        </div>
      </div>

      <!-- Статистика -->
      <div class="stats-section">
        <!-- Основная информация об активе -->
        <div class="stat-card">
          <h3>Основная информация</h3>
          <div class="stat-item">
            <span class="stat-label">Количество:</span>
            <span class="stat-value">{{ portfolioAsset.asset.quantity }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Средняя цена:</span>
            <span class="stat-value">{{ portfolioAsset.asset.average_price?.toFixed(2) || '-' }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Текущая цена:</span>
            <span class="stat-value">{{ portfolioAsset.asset.last_price?.toFixed(2) || '-' }}</span>
          </div>
          <div class="stat-item" v-if="priceGrowth">
            <span class="stat-label">Рост цены:</span>
            <span class="stat-value" :class="priceGrowth.isPositive ? 'profit' : 'loss'">
              {{ priceGrowth.isPositive ? '+' : '' }}{{ priceGrowth.percent.toFixed(2) }}%
            </span>
          </div>
        </div>

        <!-- Статистика портфеля -->
        <div class="stat-card">
          <h3>Вклад в портфель</h3>
          <div class="stat-item">
            <span class="stat-label">Общая стоимость портфеля:</span>
            <span class="stat-value">{{ formatCurrency(portfolioContribution?.portfolioValue || 0) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Стоимость актива:</span>
            <span class="stat-value">{{ formatCurrency(portfolioContribution?.assetValue || 0) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Доля в портфеле:</span>
            <span class="stat-value">{{ portfolioContribution?.percentage?.toFixed(2) || '0.00' }}%</span>
          </div>
          <div class="stat-item" v-if="portfolioContribution?.percentageInRoot !== null && portfolioContribution?.percentageInRoot !== undefined">
            <span class="stat-label">Доля в портфеле "Все активы":</span>
            <span class="stat-value">{{ portfolioContribution.percentageInRoot.toFixed(2) }}%</span>
          </div>
        </div>

        <!-- Прибыль и убытки -->
        <div class="stat-card">
          <h3>Прибыль и убытки</h3>
          <div class="stat-item">
            <span class="stat-label">Инвестировано:</span>
            <span class="stat-value">{{ formatCurrency(profitLoss?.invested || 0) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Текущая стоимость:</span>
            <span class="stat-value">{{ formatCurrency(profitLoss?.currentValue || 0) }}</span>
          </div>
          <div class="stat-item" :class="profitLoss?.isProfit ? 'profit' : 'loss'">
            <span class="stat-label">Нереализованная прибыль:</span>
            <span class="stat-value">
              {{ profitLoss?.isProfit ? '+' : '' }}{{ formatCurrency(profitLoss?.profit || 0) }}
            </span>
          </div>
          <div class="stat-item" v-if="realizedProfit !== 0" :class="realizedProfit >= 0 ? 'profit' : 'loss'">
            <span class="stat-label">Прибыль от продаж:</span>
            <span class="stat-value">
              {{ realizedProfit >= 0 ? '+' : '' }}{{ formatCurrency(realizedProfit) }}
            </span>
          </div>
          <div class="stat-item profit" v-if="payouts && payouts.total > 0">
            <span class="stat-label">Получено выплат:</span>
            <span class="stat-value">{{ formatCurrency(payouts.total || 0) }}</span>
          </div>
          <div class="stat-item" v-if="totalProfit" :class="totalProfit.isProfit ? 'profit' : 'loss'">
            <span class="stat-label">Общая прибыль:</span>
            <span class="stat-value">
              {{ totalProfit.isProfit ? '+' : '' }}{{ formatCurrency(totalProfit.total) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Транзакции и Выплаты -->
      <div v-if="allOperations.length > 0" class="transactions-section">
        <h2>Операции</h2>
        <div class="transactions-table">
          <table>
            <thead>
              <tr>
                <th>Дата</th>
                <th>Тип</th>
                <th>Количество</th>
                <th>Цена</th>
                <th>Сумма</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="op in allOperations" :key="op.id">
                <td>{{ new Date(op.date).toLocaleDateString('ru-RU') }}</td>
                <td>
                  <span :class="['badge', 'badge-' + normalizeType(op.operationType, op.type)]">
                    {{ getOperationTypeLabel(op) }}
                  </span>
                </td>
                <td>{{ op.quantity !== null && op.quantity !== undefined ? op.quantity : '-' }}</td>
                <td>{{ op.price !== null && op.price !== undefined ? op.price.toFixed(2) : '-' }}</td>
                <td>{{ formatCurrency(op.amount || 0) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-else class="error-state">
      <p>Актив не найден</p>
      <button class="btn-primary" @click="router.back()">Вернуться назад</button>
    </div>
  </div>
</template>

<style scoped>
.asset-detail-page {
  min-height: 100vh;
  background: #f8fafc;
}

.content-wrapper {
  max-width: 1200px;
  margin: 0 auto;
  padding: 32px 20px;
}

.loading-state,
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
}

.loader {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 8px 0;
}

.btn-back {
  padding: 0.5rem 1rem;
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.asset-meta-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ticker {
  font-size: 1.125rem;
  color: #6b7280;
  font-weight: 500;
}

.badge-leverage {
  padding: 0.25rem 0.5rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  font-weight: 600;
}

.portfolio-name {
  color: #6b7280;
  font-size: 0.875rem;
}

.info-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.info-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-card.profit .card-value {
  color: #10b981;
}

.info-card.loss .card-value {
  color: #ef4444;
}

.card-label {
  font-size: 0.875rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
}

.card-value {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
}

.card-value .percentage {
  font-size: 1rem;
  margin-left: 0.5rem;
}

.chart-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  margin-bottom: 2rem;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}


.chart-container {
  height: 400px;
  position: relative;
}

.no-chart-data {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #6b7280;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-card h3 {
  margin: 0 0 1rem 0;
  font-size: 1.125rem;
  font-weight: 600;
  color: #111827;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f3f4f6;
}

.stat-item:last-child {
  border-bottom: none;
}

.stat-item.profit .stat-value {
  color: var(--positiveColor, #1CBD88);
}

.stat-item.loss .stat-value {
  color: var(--negativeColor, #EF4444);
}

.stat-label {
  color: #6b7280;
  font-size: 0.875rem;
}

.stat-value {
  display: flex;
  font-weight: 600;
  color: #111827;
}

.transactions-section {
  background: white;
  padding: 1.5rem;
  border-radius: 0.75rem;
  border: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.transactions-section h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.transactions-table {
  overflow-x: auto;
}

.transactions-table table {
  width: 100%;
  border-collapse: collapse;
}

.transactions-table th {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
  color: #6b7280;
  font-weight: 600;
  font-size: 0.875rem;
}

.transactions-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #f3f4f6;
  color: #111827;
}

/* Badges для типов операций (как на странице Transactions) */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
}

.badge-buy {
  background: #dcfce7;
  color: #166534;
}

.badge-sell {
  background: #fee2e2;
  color: #991b1b;
}

.badge-dividend {
  background: #dbeafe;
  color: #1e40af;
}

.badge-coupon {
  background: #f3e8ff;
  color: #6b21a8;
}

.badge-other {
  background: #f3f4f6;
  color: #4b5563;
}

.btn-primary {
  padding: 0.75rem 1.5rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-weight: 600;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #2563eb;
}

@media (max-width: 768px) {
  .content-wrapper {
    padding: 1rem;
  }

  .info-cards {
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-container {
    height: 300px;
  }
}
</style>

