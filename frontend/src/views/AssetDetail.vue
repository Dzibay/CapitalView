<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import MultiLineChart from '../components/MultiLineChart.vue'
import PeriodFilters from '../components/widgets/PeriodFilters.vue'
import CustomSelect from '../components/CustomSelect.vue'
import LoadingState from '../components/LoadingState.vue'
import assetsService from '../services/assetsService'
import operationsService from '../services/operationsService'
import PageLayout from '../components/PageLayout.vue'
import WidgetContainer from '../components/widgets/WidgetContainer.vue'
import AssetPortfolioStatsWidget from '../components/widgets/AssetPortfolioStatsWidget.vue'
import AssetBasicInfoWidget from '../components/widgets/AssetBasicInfoWidget.vue'
import AssetPortfolioContributionWidget from '../components/widgets/AssetPortfolioContributionWidget.vue'
import AssetProfitLossWidget from '../components/widgets/AssetProfitLossWidget.vue'
import ValueChange from '../components/widgets/ValueChange.vue'
import Widget from '../components/widgets/Widget.vue'
import OperationsListWidget from '../components/widgets/OperationsListWidget.vue'
import AssetPayoutsListWidget from '../components/widgets/AssetPayoutsListWidget.vue'

const route = useRoute()
const router = useRouter()

// Используем stores вместо inject
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const portfolioAssetId = computed(() => parseInt(route.params.id))
const isLoading = ref(false)
const assetInfo = ref(null)
const priceHistory = ref([])
const assetInAllPortfolios = ref([])
const selectedPortfolioId = ref(null)
const selectedPeriod = ref('All')
const selectedChartType = ref('position') // 'position' | 'quantity' | 'price'
const cashOperations = ref([]) // Полученные выплаты из cash_operations
const portfolioTransactions = ref({}) // Транзакции для каждого portfolio_asset_id

const chartTypeOptions = [
  { value: 'position', label: 'Стоимость позиции' },
  { value: 'quantity', label: 'Количество' },
  { value: 'price', label: 'Цена единицы' }
]

// Получаем информацию о портфеле из dashboardStore для расчета вклада
const portfolios = computed(() => dashboardStore.portfolios ?? [])

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

// Опции для выбора портфеля
const portfolioOptions = computed(() => {
  return assetInAllPortfolios.value.map(p => ({
    value: p.portfolio_id,
    label: p.portfolio_name
  }))
})

// Выбранный портфель из списка всех портфелей
const selectedPortfolioAsset = computed(() => {
  if (!selectedPortfolioId.value) return assetInAllPortfolios.value[0] || null
  return assetInAllPortfolios.value.find(p => p.portfolio_id === selectedPortfolioId.value) || assetInAllPortfolios.value[0] || null
})

// Загрузка информации о портфельном активе (оптимизированная версия)
async function loadAssetInfo() {
  if (!portfolioAssetId.value) return
  
  isLoading.value = true
  try {
    const result = await assetsService.getPortfolioAssetInfo(portfolioAssetId.value)
    if (result.success && result.portfolio_asset) {
      assetInfo.value = result.portfolio_asset
      
      // Получаем информацию о портфелях из того же запроса
      if (result.portfolios) {
        assetInAllPortfolios.value = result.portfolios
        // Устанавливаем первый портфель как выбранный по умолчанию
        if (result.portfolios.length > 0 && !selectedPortfolioId.value) {
          selectedPortfolioId.value = result.portfolios[0].portfolio_id
        }
        
        // Сохраняем транзакции для текущего portfolio_asset_id
        if (result.portfolio_asset.transactions) {
          portfolioTransactions.value[portfolioAssetId.value] = result.portfolio_asset.transactions
        }
        
        // Загружаем транзакции для всех портфелей
        await loadTransactionsForAllPortfolios(result.portfolios)
      }
      
      // Используем историю цен из основного запроса (если есть)
      if (result.portfolio_asset.price_history && result.portfolio_asset.price_history.length > 0) {
        priceHistory.value = result.portfolio_asset.price_history
      } else if (result.portfolio_asset.asset_id) {
        // Если истории нет в основном запросе, загружаем отдельно (для больших объемов данных)
        await loadPriceHistory(result.portfolio_asset.asset_id)
      }
      
      // Загружаем полученные выплаты из cash_operations
      await loadReceivedPayouts()
    }
  } catch (error) {
    console.error('Ошибка при загрузке информации об активе:', error)
  } finally {
    isLoading.value = false
  }
}

// Загрузка транзакций для всех портфелей
async function loadTransactionsForAllPortfolios(portfolios) {
  // Транзакции уже загружены для текущего portfolio_asset_id
  // Для других портфелей нужно загружать отдельно, но это требует дополнительных запросов
  // Пока используем транзакции из основного запроса
  // Для каждого портфеля загружаем транзакции, если они еще не загружены
  for (const portfolio of portfolios) {
    const portfolioAssetId = portfolio.portfolio_asset_id
    if (portfolioAssetId && !portfolioTransactions.value[portfolioAssetId]) {
      // Загружаем транзакции для этого portfolio_asset_id
      try {
        const result = await assetsService.getPortfolioAssetInfo(portfolioAssetId)
        if (result.success && result.portfolio_asset?.transactions) {
          portfolioTransactions.value[portfolioAssetId] = result.portfolio_asset.transactions
        }
      } catch (error) {
        console.error(`Ошибка при загрузке транзакций для portfolio_asset_id ${portfolioAssetId}:`, error)
      }
    }
  }
}

// Загрузка полученных выплат из cash_operations
async function loadReceivedPayouts() {
  if (!selectedPortfolioId.value || !assetInfo.value?.asset_id) return
  
  try {
    const response = await operationsService.getOperations({
      portfolio_id: selectedPortfolioId.value,
      limit: 1000
    })
    
    // API возвращает { success: true, data: { operations: [...] } }
    // operationsService.getOperations уже обрабатывает это и возвращает массив
    const operations = Array.isArray(response) ? response : []
    
    if (operations && Array.isArray(operations)) {
      // Фильтруем только выплаты (Dividend, Coupon) для данного актива
      const assetId = assetInfo.value.asset_id
      cashOperations.value = operations.filter(op => {
        const opType = op.operation_type || op.type || ''
        const isPayout = opType === 'Дивиденды' || opType === 'Купоны' || 
                        opType === 'Dividend' || opType === 'Coupon' ||
                        opType.toLowerCase().includes('dividend') || 
                        opType.toLowerCase().includes('coupon') ||
                        opType.toLowerCase().includes('дивиденд') || 
                        opType.toLowerCase().includes('купон')
        return isPayout && op.asset_id === assetId
      })
    } else {
      cashOperations.value = []
    }
  } catch (error) {
    console.error('Ошибка при загрузке полученных выплат:', error)
    cashOperations.value = []
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

// Транзакции для выбранного портфеля
const selectedPortfolioTransactions = computed(() => {
  if (!selectedPortfolioAsset.value) {
    return assetInfo.value?.transactions || []
  }
  
  const selectedPortfolioAssetId = selectedPortfolioAsset.value.portfolio_asset_id
  
  // Используем транзакции из кэша, если они есть
  if (portfolioTransactions.value[selectedPortfolioAssetId]) {
    return portfolioTransactions.value[selectedPortfolioAssetId]
  }
  
  // Если выбранный портфель совпадает с текущим, используем транзакции из запроса
  if (selectedPortfolioAssetId === portfolioAssetId.value) {
    return assetInfo.value?.transactions || []
  }
  
  // Для других портфелей возвращаем пустой массив
  // TODO: добавить загрузку транзакций для выбранного portfolio_asset_id
  return []
})

// Находим первую дату транзакции для выбранного портфеля
const firstTransactionDate = computed(() => {
  const transactions = selectedPortfolioTransactions.value
  if (!transactions || !transactions.length) {
    return null
  }
  
  const dates = transactions
    .map(tx => new Date(tx.transaction_date))
    .filter(d => !isNaN(d.getTime()))
  
  if (!dates.length) return null
  
  // Находим самую раннюю дату
  const firstDate = new Date(Math.min(...dates))
  firstDate.setHours(0, 0, 0, 0)
  return firstDate.toISOString().split('T')[0]
})

// Вычисляем накопленное количество на каждую дату для выбранного портфеля
const quantityByDate = computed(() => {
  const transactions = selectedPortfolioTransactions.value
  if (!transactions || !priceHistory.value?.length) {
    return {}
  }
  
  const txList = [...transactions]
    .map(tx => ({
      ...tx,
      date: new Date(tx.transaction_date).toISOString().split('T')[0]
    }))
    .sort((a, b) => a.date.localeCompare(b.date))
  
  const quantityMap = {}
  let cumulativeQuantity = 0
  
  // Вычисляем накопленное количество для каждой даты из истории цен
  // Нормализуем даты из истории цен
  const priceDates = [...new Set(priceHistory.value.map(p => {
    const date = new Date(p.trade_date)
    date.setHours(0, 0, 0, 0)
    return date.toISOString().split('T')[0]
  }))].sort()
  
  let txIndex = 0
  for (const priceDateStr of priceDates) {
    // Применяем все транзакции до и включая эту дату
    while (txIndex < txList.length) {
      const tx = txList[txIndex]
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
    
    quantityMap[priceDateStr] = Math.max(0, cumulativeQuantity) // Не даем уйти в минус
  }
  
  return quantityMap
})

// Формирование данных для графика (зависит от выбранного портфеля)
const chartData = computed(() => {
  if (!priceHistory.value || !priceHistory.value.length || !selectedPortfolioAsset.value) {
    return { labels: [], datasets: [] }
  }

  const asset = selectedPortfolioAsset.value
  const leverage = asset.leverage || 1
  const currencyRate = asset.currency_rate_to_rub || portfolioAsset.value?.asset.currency_rate_to_rub || 1

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
      // Нормализуем дату для поиска в quantityMap
      const dateObj = new Date(date)
      dateObj.setHours(0, 0, 0, 0)
      const normalizedDate = dateObj.toISOString().split('T')[0]
      
      const qty = quantities[normalizedDate] || 0
      const price = filteredPrices.find(p => {
        const pDate = new Date(p.trade_date)
        pDate.setHours(0, 0, 0, 0)
        return pDate.toISOString().split('T')[0] === normalizedDate
      })?.price || 0
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
    const quantities = quantityByDate.value
    const data = labels.map(date => {
      // Нормализуем дату для поиска в quantityMap
      const dateObj = new Date(date)
      dateObj.setHours(0, 0, 0, 0)
      const normalizedDate = dateObj.toISOString().split('T')[0]
      return quantities[normalizedDate] || 0
    })
    
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

// Расчет роста цены для выбранного портфеля
const selectedPriceGrowth = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const asset = selectedPortfolioAsset.value
  const currentPrice = asset.last_price || 0
  const averagePrice = asset.average_price || 0
  
  if (averagePrice === 0) return null
  
  const percent = ((currentPrice - averagePrice) / averagePrice) * 100
  
  return {
    percent,
    isPositive: percent >= 0
  }
})

// Расчет общей прибыли для выбранного портфеля
const selectedTotalProfit = computed(() => {
  if (!selectedProfitLoss.value) return null
  
  const unrealized = selectedProfitLoss.value.profit
  const realized = realizedProfit.value
  const payoutAmount = receivedPayouts.value
  const total = unrealized + realized + payoutAmount
  
  return {
    unrealized,
    realized,
    payouts: payoutAmount,
    total,
    isProfit: total >= 0
  }
})

// Полученные выплаты (из cash_operations)
const receivedPayouts = computed(() => {
  return receivedPayoutsTotal.value
})

// Расчет доли в корневом портфеле для выбранного портфеля
const selectedPortfolioPercentageInRoot = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const rootValue = rootPortfolio.value?.total_value || 0
  const assetValue = selectedPortfolioAsset.value.asset_value || 0
  
  if (rootValue === 0) return null
  
  return (assetValue / rootValue) * 100
})

// Изменение цены за день в процентах для выбранного портфеля
const selectedPriceChangePercent = computed(() => {
  if (!selectedPortfolioAsset.value || !selectedPortfolioAsset.value.last_price) return 0
  
  const lastPrice = selectedPortfolioAsset.value.last_price
  const dailyChange = selectedPortfolioAsset.value.daily_change || 0
  
  if (lastPrice === 0) return 0
  
  // Вычисляем процент изменения
  const previousPrice = lastPrice - dailyChange
  if (previousPrice === 0) return 0
  
  return (dailyChange / previousPrice) * 100
})

// Расчет прибыли/убытка для выбранного портфеля
const selectedProfitLoss = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const asset = selectedPortfolioAsset.value
  const currentPrice = asset.last_price || 0
  const averagePrice = asset.average_price || 0
  const quantity = asset.quantity || 0
  const leverage = asset.leverage || 1
  // Используем курс из данных портфеля или из основного актива
  const currencyRate = asset.currency_rate_to_rub || portfolioAsset.value?.asset.currency_rate_to_rub || 1

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

// Расчет прибыли/убытка (для обратной совместимости)
const profitLoss = computed(() => {
  return selectedProfitLoss.value
})

// Расчет выплат (дивиденды + купоны) из asset_payouts (все выплаты актива)
const payouts = computed(() => {
  if (!assetInfo.value) return null
  
  // Получаем все выплаты из asset_payouts (не только полученные)
  // Данные приходят из бэкенда как 'payouts' (преобразовано из 'all_payouts')
  const payoutHistory = assetInfo.value.payouts || []
  
  let dividends = 0
  let coupons = 0
  
  // Суммируем выплаты по типам
  payoutHistory.forEach(payout => {
    const payoutType = payout.type // 'dividend' или 'coupon' (строка)
    const value = Number(payout.value || 0)
    
    // Определяем тип выплаты
    const typeLower = (payoutType || '').toLowerCase()
    if (typeLower.includes('dividend') || typeLower.includes('дивиденд')) {
      dividends += value
    } else if (typeLower.includes('coupon') || typeLower.includes('купон')) {
      coupons += value
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

// Расчет прибыли от продаж (realized P&L) для выбранного портфеля
const realizedProfit = computed(() => {
  const transactions = selectedPortfolioTransactions.value || []
  
  // Суммируем realized_pnl из транзакций продажи, если есть
  let totalRealized = 0
  
  for (const tx of transactions) {
    const txType = typeof tx.transaction_type === 'number' 
      ? tx.transaction_type 
      : (tx.transaction_type?.toLowerCase() === 'sell' ? 2 : 1)
    
    // Если это продажа и есть realized_pnl
    if (txType === 2 && tx.realized_pnl !== undefined && tx.realized_pnl !== null) {
      totalRealized += Number(tx.realized_pnl) || 0
    }
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

// Полученные выплаты из cash_operations
const receivedPayoutsList = computed(() => {
  return cashOperations.value || []
})

// Сумма полученных выплат
const receivedPayoutsTotal = computed(() => {
  return receivedPayoutsList.value.reduce((sum, op) => {
    return sum + (Number(op.amount) || 0)
  }, 0)
})

// Список операций (транзакции + полученные выплаты) для выбранного портфеля
const allOperations = computed(() => {
  const operations = []
  
  // Добавляем транзакции для выбранного портфеля
  const transactions = selectedPortfolioTransactions.value
  if (transactions && transactions.length > 0) {
    transactions.forEach(tx => {
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
  
  // Добавляем полученные выплаты из cash_operations для выбранного портфеля
  receivedPayoutsList.value.forEach(op => {
    // Определяем тип операции для выплаты
    let operationType = 0
    const opType = (op.operation_type || '').toLowerCase()
    if (opType.includes('dividend') || opType.includes('дивиденд')) {
      operationType = 3 // Дивиденды
    } else if (opType.includes('coupon') || opType.includes('купон')) {
      operationType = 4 // Купоны
    }
    
    operations.push({
      id: `payout_${op.cash_operation_id || op.id}`,
      type: 'payout',
      date: op.operation_date || op.date,
      operationType: operationType,
      quantity: null,
      price: null,
      amount: Number(op.amount) || 0
    })
  })
  
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

// Сортировка выплат
const sortedPayouts = computed(() => {
  if (!payouts.value?.history) return []
  return [...payouts.value.history].sort((a, b) => {
    const dateA = new Date(a.payment_date || 0)
    const dateB = new Date(b.payment_date || 0)
    return dateB - dateA
  })
})

// Функции для выплат
const getPayoutTypeLabel = (type) => {
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('див') || t.includes('dividend')) return 'Дивиденды'
    if (t.includes('купон') || t.includes('coupon')) return 'Купоны'
    if (t.includes('аморт') || t.includes('amortization')) return 'Амортизация'
  }
  return 'Выплата'
}

const getPayoutTypeClass = (type) => {
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('див') || t.includes('dividend')) return 'dividend'
    if (t.includes('купон') || t.includes('coupon')) return 'coupon'
    if (t.includes('аморт') || t.includes('amortization')) return 'amortization'
  }
  return 'other'
}

const formatPayoutDate = (date) => {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('ru-RU')
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

// Отслеживание изменений выбранного портфеля
watch(selectedPortfolioId, async (newPortfolioId) => {
  if (newPortfolioId && assetInfo.value?.asset_id) {
    await loadReceivedPayouts()
  }
})

// Обработчик изменения портфеля
async function handlePortfolioChange(portfolioId) {
  selectedPortfolioId.value = portfolioId
  // Загружаем выплаты для нового портфеля
  await loadReceivedPayouts()
}
</script>

<template>
  <div class="asset-detail-page">
    <LoadingState v-if="isLoading || uiStore.loading" message="Загрузка данных об активе..." />

    <PageLayout v-else-if="assetInfo && portfolioAsset">
      <!-- Заголовок: кнопка назад слева, выбор портфеля справа -->
      <div class="asset-header">
        <button class="btn-back" @click="router.back()">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          Назад
        </button>
        <div class="header-portfolio-selector">
          <CustomSelect
            :modelValue="selectedPortfolioId || (assetInAllPortfolios[0]?.portfolio_id)"
            :options="portfolioOptions"
            label=""
            placeholder="Выберите портфель"
            :show-empty-option="false"
            option-label="label"
            option-value="value"
            :min-width="'200px'"
            :flex="'none'"
            @update:modelValue="handlePortfolioChange"
          />
        </div>
      </div>

      <!-- Длинный блок: название актива, тикер, стоимость и изменение -->
      <div class="asset-overview-block">
        <div class="asset-main-info">
          <h1 class="asset-name">{{ portfolioAsset.asset.name }}</h1>
          <div class="asset-meta">
            <span class="meta-item">{{ portfolioAsset.asset.ticker }}</span>
            <span v-if="portfolioAsset.asset.leverage && portfolioAsset.asset.leverage > 1" class="meta-item">
              ×{{ portfolioAsset.asset.leverage }}
            </span>
          </div>
        </div>
        <div class="asset-price-info">
          <div class="price-main">{{ selectedPortfolioAsset?.last_price?.toFixed(2) || portfolioAsset.asset.last_price?.toFixed(2) || '-' }}</div>
          <div v-if="selectedPortfolioAsset?.daily_change !== undefined && selectedPortfolioAsset.daily_change !== 0" class="price-change">
            <ValueChange 
              :value="selectedPriceChangePercent" 
              :isPositive="selectedPortfolioAsset.daily_change >= 0"
              format="percent"
            />
            <span class="price-change-currency">
              ({{ selectedPortfolioAsset.daily_change >= 0 ? '+' : '' }}{{ formatCurrency(selectedPortfolioAsset.daily_change) }})
            </span>
          </div>
        </div>
      </div>

      <!-- График и описание актива -->
      <div class="widgets-grid">
        <!-- График -->
        <WidgetContainer :gridColumn="8" minHeight="var(--widget-height-large)">
          <div class="chart-widget">
            <div class="section-header">
              <h2 class="section-title">История актива</h2>
              <div class="chart-controls">
                <CustomSelect
                  :modelValue="selectedChartType"
                  :options="chartTypeOptions"
                  label="ТИП ГРАФИКА"
                  placeholder="Выберите тип графика"
                  :show-empty-option="false"
                  option-label="label"
                  option-value="value"
                  :min-width="'200px'"
                  :flex="'none'"
                  @update:modelValue="selectedChartType = $event"
                />
                <PeriodFilters 
                  :modelValue="selectedPeriod" 
                  @update:modelValue="selectedPeriod = $event"
                />
              </div>
            </div>
            <div class="chart-container">
              <MultiLineChart 
                v-if="chartData.labels.length" 
                :chartData="chartData" 
                :period="selectedPeriod"
                :chartType="selectedChartType"
                :formatCurrency="chartFormatter"
              />
              <div v-else class="no-chart-data">Нет данных для отображения графика</div>
            </div>
          </div>
        </WidgetContainer>

        <!-- Описание актива (заглушка) -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-large)">
          <Widget title="Описание актива">
            <div class="asset-description-placeholder">
              <p>Описание актива будет здесь</p>
            </div>
          </Widget>
        </WidgetContainer>
      </div>

      <!-- Блоки показателей (три отдельных виджета) -->
      <div class="widgets-grid">
        <!-- Основная информация -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
          <AssetBasicInfoWidget
            :quantity="selectedPortfolioAsset?.quantity || 0"
            :averagePrice="selectedPortfolioAsset?.average_price || 0"
            :lastPrice="selectedPortfolioAsset?.last_price || 0"
            :priceGrowth="selectedPriceGrowth"
          />
        </WidgetContainer>

        <!-- Вклад в портфель -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
          <AssetPortfolioContributionWidget
            :portfolioValue="selectedPortfolioAsset?.portfolio_total_value || 0"
            :assetValue="selectedPortfolioAsset?.asset_value || 0"
            :percentageInPortfolio="selectedPortfolioAsset?.percentage_in_portfolio || 0"
            :percentageInRoot="selectedPortfolioPercentageInRoot"
          />
        </WidgetContainer>

        <!-- Прибыль и убытки -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
          <AssetProfitLossWidget
            :invested="selectedProfitLoss?.invested || 0"
            :currentValue="selectedProfitLoss?.currentValue || 0"
            :profit="selectedProfitLoss?.profit || 0"
            :isProfit="selectedProfitLoss?.isProfit || false"
            :realizedProfit="realizedProfit"
            :receivedPayouts="receivedPayouts"
            :totalProfit="selectedTotalProfit?.total || 0"
            :isTotalProfit="selectedTotalProfit?.isProfit || false"
          />
        </WidgetContainer>
      </div>

      <!-- Операции (транзакции + полученные выплаты) -->
      <div class="widgets-grid">
        <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
          <OperationsListWidget
            title="Операции"
            :operations="allOperations"
            :get-operation-type-label="getOperationTypeLabel"
            :get-operation-type-class="(op) => normalizeType(op.operationType, op.type)"
          />
        </WidgetContainer>
      </div>

      <!-- Полная история выплат -->
      <div class="widgets-grid">
        <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
          <AssetPayoutsListWidget :payouts="payouts?.history || []" />
        </WidgetContainer>
      </div>

    </PageLayout>

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

.widgets-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  grid-auto-rows: min-content;
  margin-top: 2rem;
}

@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

@media (max-width: 768px) {
  .widgets-grid {
    grid-template-columns: 1fr;
  }
}

.chart-widget {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
}

.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
}


/* Заголовок */
.asset-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.header-portfolio-selector {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-back {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem;
  background: transparent;
  border: none;
  border-radius: 0.375rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #6b7280;
  transition: all 0.2s;
}

.btn-back:hover {
  background: #f3f4f6;
  color: #111827;
}

/* Длинный блок: название актива, тикер, стоимость и изменение */
.asset-overview-block {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 2rem;
  flex-wrap: wrap;
}

.asset-main-info {
  flex: 1;
  min-width: 200px;
}

.asset-name {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.5rem 0;
  line-height: 1.3;
}

.asset-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 400;
}

.asset-price-info {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.price-main {
  font-size: 1.75rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.price-change {
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.price-change-currency {
  color: #6b7280;
  font-size: 0.75rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
  margin: 0;
}

.metrics-section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  height: 100%;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 0.5rem 0;
  gap: 0.5rem;
  flex-wrap: wrap;
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
  flex: 1;
}

.stat-value {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  color: #111827;
  text-align: right;
}

.portfolio-name {
  font-size: 0.875rem;
  color: #6b7280;
  font-weight: 500;
}

.asset-description-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 200px;
  color: #9ca3af;
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
  margin-top: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.section-header h2,
.section-header .section-title {
  margin: 0;
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
}

.transactions-section h2,
.payouts-section h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
}

.chart-controls {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
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


.transactions-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  margin-top: 2rem;
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

/* История выплат (в стиле таблицы операций) */
.payouts-section {
  background: white;
  padding: 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  margin-top: 2rem;
}

.payouts-section h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #111827;
}

.payouts-table {
  overflow-x: auto;
}

.payouts-table table {
  width: 100%;
  border-collapse: collapse;
}

.payouts-table th {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 2px solid #e5e7eb;
  color: #6b7280;
  font-weight: 600;
  font-size: 0.875rem;
}

.payouts-table td {
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
  background: rgba(37, 99, 235, 0.1);
  color: var(--payout-dividends, #2563eb);
}

.badge-coupon {
  background: rgba(6, 182, 212, 0.1);
  color: var(--payout-coupons, #06b6d4);
}

.badge-amortization {
  background: rgba(251, 146, 60, 0.1);
  color: var(--payout-amortizations, #fb923c);
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

@media (max-width: 1200px) {
  .widgets-grid {
    grid-template-columns: repeat(6, 1fr);
  }
}

@media (max-width: 768px) {
  .content-wrapper {
    padding: 1rem;
  }

  .asset-name {
    font-size: 1.5rem;
  }

  .widgets-grid {
    grid-template-columns: 1fr;
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

