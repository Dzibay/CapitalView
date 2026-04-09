<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Building2, PieChart, TrendingDown, Hash, History, LineChart, Coins } from 'lucide-vue-next'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import MultiLineChart from '../components/charts/MultiLineChart.vue'
import { 
  PeriodFilters, 
  WidgetContainer, 
  MetricsWidget, 
  ValueChangePill, 
  ChartPeriodSummary,
  Widget 
} from '../components/widgets/base'
import { AssetPortfolioStatsWidget } from '../components/widgets/composite'
import { OperationsListWidget } from '../components/widgets/lists'
import CustomSelect from '../components/base/CustomSelect.vue'
import ChartVariantSelect from '../components/base/ChartVariantSelect.vue'
import ChartOptionsMenu from '../components/base/ChartOptionsMenu.vue'
import LoadingState from '../components/base/LoadingState.vue'
import assetsService from '../services/assetsService'
import operationsService from '../services/operationsService'
import PageLayout from '../layouts/PageLayout.vue'
import { formatOperationAmount } from '../utils/formatCurrency'
import { normalizeDateToString, formatDateForDisplay } from '../utils/date'
import { getCurrencySymbol } from '../utils/currencySymbols'
import { effectiveUnitPriceInCurrency } from '../utils/effectiveAssetPrice'

const route = useRoute()
const router = useRouter()

// Используем stores вместо inject
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const portfolioAssetId = computed(() => parseInt(route.params.id))
const isLoading = ref(false)
const assetInfo = ref(null)
const priceHistory = ref([])
const priceHistoryCurrency = ref(null) // Валюта истории цен (из API getAssetPriceHistory)
const assetDailyValues = ref([]) // История стоимости позиции из portfolio_asset_daily_values
const assetInAllPortfolios = ref([])
const selectedPortfolioId = ref(null)
const selectedPeriod = ref('All')
const selectedChartType = ref('position') // 'position' | 'quantity' | 'price'
const showMinMax = ref(false)
const selectedTab = ref('general') // 'general' | 'analytics' | 'dividends'

const tabs = [
  { id: 'general', label: 'Общее' },
  { id: 'analytics', label: 'Аналитика' },
  { id: 'dividends', label: 'Дивиденды' }
]

const analyticsChartMetric = ref('position') // 'position' | 'quantity'

const assetChartMenuOptions = computed(() => [
  { id: 'minmax', label: 'Min / Max', modelValue: showMinMax.value }
])

const analyticsChartVariants = [
  { value: 'position', label: 'Стоимость позиции' },
  { value: 'quantity', label: 'Количество' }
]

const analyticsChartMenuOptions = computed(() => [
  { id: 'minmax', label: 'Min / Max', modelValue: showMinMax.value }
])

function onAssetChartOptionToggle(id, val) {
  if (id === 'minmax') showMinMax.value = val
}

function onAnalyticsChartMenuToggle(id, val) {
  if (id === 'minmax') showMinMax.value = val
}
const cashOperations = ref([]) // Все операции из cash_operations (выплаты, комиссии, налоги и т.д.)
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
        // Устанавливаем портфель, в котором находится актив, как выбранный по умолчанию
        if (result.portfolios.length > 0 && !selectedPortfolioId.value) {
          // Используем portfolio_id из portfolio_asset, если он есть в списке портфелей
          const assetPortfolioId = result.portfolio_asset.portfolio_id
          const portfolioExists = result.portfolios.find(p => p.portfolio_id === assetPortfolioId)
          if (portfolioExists) {
            selectedPortfolioId.value = assetPortfolioId
          } else {
            // Если портфель не найден в списке, используем первый
            selectedPortfolioId.value = result.portfolios[0].portfolio_id
          }
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
        priceHistoryCurrency.value = result.portfolio_asset.currency_ticker || null
      } else if (result.portfolio_asset.asset_id) {
        // Если истории нет в основном запросе, загружаем отдельно (для больших объемов данных)
        await loadPriceHistory(result.portfolio_asset.asset_id)
      }
      
      // ОПТИМИЗИРОВАНО: используем daily_values и cash_operations из основного запроса
      if (result.portfolio_asset.daily_values) {
        assetDailyValues.value = result.portfolio_asset.daily_values
        console.log('Загружены данные стоимости позиции из основного запроса:', result.portfolio_asset.daily_values.length, 'записей')
      }
      
      if (result.portfolio_asset.cash_operations) {
        cashOperations.value = result.portfolio_asset.cash_operations
        console.log('Загружены операции из основного запроса:', result.portfolio_asset.cash_operations.length, 'записей')
      }
    }
  } catch (error) {
    console.error('Ошибка при загрузке информации об активе:', error)
  } finally {
    isLoading.value = false
  }
}

// ОПТИМИЗИРОВАНО: не загружаем транзакции для всех портфелей при инициализации
// Транзакции будут загружены только для выбранного портфеля при смене
async function loadTransactionsForAllPortfolios(portfolios) {
  // Транзакции уже загружены для текущего portfolio_asset_id из основного запроса
  // Для других портфелей транзакции будут загружены при смене портфеля
  // Это значительно уменьшает количество запросов при загрузке страницы
}

// Загрузка всех операций из cash_operations для данного актива
async function loadAllCashOperations() {
  if (!assetInfo.value?.asset_id) return
  
  try {
    const assetId = assetInfo.value.asset_id
    const allOperations = []
    
    // Загружаем операции для всех портфелей, где есть этот актив
    if (assetInAllPortfolios.value && assetInAllPortfolios.value.length > 0) {
      for (const portfolio of assetInAllPortfolios.value) {
        if (portfolio.portfolio_id) {
          try {
            const response = await operationsService.getOperations({
              portfolio_id: portfolio.portfolio_id,
              limit: 1000
            })
            
            const operations = Array.isArray(response) ? response : []
            if (operations && Array.isArray(operations)) {
              // Фильтруем операции для данного актива (включая Buy/Sell)
              const assetOperations = operations.filter(op => op.asset_id === assetId)
              allOperations.push(...assetOperations)
            }
          } catch (error) {
            console.error(`Ошибка при загрузке операций для портфеля ${portfolio.portfolio_id}:`, error)
          }
        }
      }
    } else if (selectedPortfolioId.value) {
      // Fallback: загружаем только для выбранного портфеля
      const response = await operationsService.getOperations({
        portfolio_id: selectedPortfolioId.value,
        limit: 1000
      })
      
      const operations = Array.isArray(response) ? response : []
      if (operations && Array.isArray(operations)) {
        const assetOperations = operations.filter(op => op.asset_id === assetId)
        allOperations.push(...assetOperations)
      }
    }
    
    cashOperations.value = allOperations
  } catch (error) {
    console.error('Ошибка при загрузке операций:', error)
    cashOperations.value = []
  }
}

// Загрузка истории цен
async function loadPriceHistory(assetId) {
  try {
    const result = await assetsService.getAssetPriceHistory(assetId)
    if (result.success && result.prices) {
      priceHistory.value = result.prices
      priceHistoryCurrency.value = result.currency_ticker || null
    }
  } catch (error) {
    console.error('Ошибка при загрузке истории цен:', error)
  }
}

// Загрузка истории стоимости позиции из portfolio_asset_daily_values
async function loadAssetDailyValues() {
  // Используем portfolio_asset_id из выбранного портфеля или текущего актива
  const targetPortfolioAssetId = selectedPortfolioAsset.value?.portfolio_asset_id || portfolioAssetId.value
  
  if (!targetPortfolioAssetId) {
    assetDailyValues.value = []
    return
  }
  
  try {
    const result = await assetsService.getAssetDailyValues(targetPortfolioAssetId)
    if (result.success && result.values) {
      assetDailyValues.value = result.values
      console.log('Загружены данные стоимости позиции:', result.values.length, 'записей')
    } else {
      console.warn('Не удалось загрузить данные стоимости позиции:', result.error)
      assetDailyValues.value = []
    }
  } catch (error) {
    console.error('Ошибка при загрузке истории стоимости позиции:', error)
    assetDailyValues.value = []
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
  return normalizeDateToString(firstDate) || ''
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
      date: normalizeDateToString(tx.transaction_date) || ''
    }))
    .sort((a, b) => a.date.localeCompare(b.date))
  
  const quantityMap = {}
  let cumulativeQuantity = 0
  
  const priceDates = [...new Set(
    priceHistory.value.map(p => (p.trade_date || '').split('T')[0])
  )].filter(Boolean).sort()
  
  let txIndex = 0
  for (const priceDateStr of priceDates) {
    // Применяем все транзакции до и включая эту дату
    while (txIndex < txList.length) {
      const tx = txList[txIndex]
      const txDateStr = tx.date
      
      // Сравниваем даты как строки
      if (txDateStr > priceDateStr) break
      
      // transaction_type: 1 = buy (плюс), 2 = sell (минус), 3 = amortization (минус)
      const txQuantity = Number(tx.quantity) || 0
      if (tx.transaction_type === 1 || (typeof tx.transaction_type === 'string' && tx.transaction_type.toLowerCase() === 'buy')) {
        cumulativeQuantity += txQuantity
      } else if (tx.transaction_type === 2 || tx.transaction_type === 3 || 
                 (typeof tx.transaction_type === 'string' && (tx.transaction_type.toLowerCase() === 'sell' || tx.transaction_type.toLowerCase().includes('amortization') || tx.transaction_type.toLowerCase().includes('аморт')))) {
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

  let filteredPrices = priceHistory.value
  if (firstTransactionDate.value && selectedChartType.value !== 'price') {
    const firstDateStr = typeof firstTransactionDate.value === 'string'
      ? firstTransactionDate.value.split('T')[0]
      : normalizeDateToString(new Date(firstTransactionDate.value)) || ''
    filteredPrices = filteredPrices.filter(p => (p.trade_date || '').split('T')[0] >= firstDateStr)
  }

  if (!filteredPrices.length) {
    return { labels: [], datasets: [] }
  }

  const priceMap = new Map()
  for (const p of filteredPrices) {
    priceMap.set(p.trade_date, p.price)
  }
  const labels = [...priceMap.keys()].sort()
  
  let datasets = []
  
  if (selectedChartType.value === 'position') {
    // График стоимости позиции - используем данные из portfolio_asset_daily_values
    if (assetDailyValues.value && assetDailyValues.value.length > 0) {
      // Фильтруем данные по выбранному периоду
      let filteredValues = [...assetDailyValues.value]
      
      // Фильтруем по первой транзакции
      if (firstTransactionDate.value) {
        filteredValues = filteredValues.filter(v => {
          const valueDate = new Date(v.report_date)
          valueDate.setHours(0, 0, 0, 0)
          const firstDate = new Date(firstTransactionDate.value)
          firstDate.setHours(0, 0, 0, 0)
          return valueDate >= firstDate
        })
      }
      
      // Сортируем по дате
      filteredValues.sort((a, b) => {
        const dateA = new Date(a.report_date)
        const dateB = new Date(b.report_date)
        return dateA - dateB
      })
      
      if (filteredValues.length > 0) {
        const data = filteredValues.map(v => {
          const value = v.position_value
          // Проверяем, что значение не null и не undefined
          if (value === null || value === undefined) {
            console.warn('Найдено null/undefined position_value для даты:', v.report_date)
            return 0
          }
          return Number(value)
        })
        const labels = filteredValues.map(v => v.report_date)
        
        datasets = [{
          label: 'Стоимость позиции',
          data,
          color: '#3b82f6',
          fill: true
        }]
        
        return {
          labels,
          datasets
        }
      } else {
        console.warn('Нет данных после фильтрации для графика стоимости позиции')
      }
    } else {
      console.warn('Нет данных assetDailyValues для графика стоимости позиции')
    }
    
    const quantities = quantityByDate.value
    const data = labels.map(date => {
      const normalizedDate = date.split('T')[0]
      const qty = quantities[normalizedDate] || 0
      const price = priceMap.get(date) || 0
      return (qty * price / leverage) * currencyRate
    })
    
    datasets = [{
      label: 'Стоимость позиции',
      data,
      color: '#3b82f6',
      fill: true
    }]
  } else if (selectedChartType.value === 'quantity') {
    // График количества актива - используем данные из portfolio_asset_daily_values
    if (assetDailyValues.value && assetDailyValues.value.length > 0) {
      // Фильтруем данные по выбранному периоду
      let filteredValues = [...assetDailyValues.value]
      if (firstTransactionDate.value) {
        filteredValues = filteredValues.filter(v => {
          const valueDate = new Date(v.report_date)
          valueDate.setHours(0, 0, 0, 0)
          const firstDate = new Date(firstTransactionDate.value)
          firstDate.setHours(0, 0, 0, 0)
          return valueDate >= firstDate
        })
      }
      
      if (filteredValues.length > 0) {
        const data = filteredValues.map(v => v.quantity || 0)
        const labels = filteredValues.map(v => v.report_date)
        
        datasets = [{
          label: 'Количество актива',
          data,
          color: '#10b981',
          fill: true
        }]
        
        return {
          labels,
          datasets
        }
      }
    }
    
    const quantities = quantityByDate.value
    const data = labels.map(date => quantities[date.split('T')[0]] || 0)
    
    datasets = [{
      label: 'Количество актива',
      data,
      color: '#10b981',
      fill: true
    }]
  } else if (selectedChartType.value === 'price') {
    const data = labels.map(date => priceMap.get(date) || 0)
    
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

// Данные для графика цены единицы (вкладка "Общее")
const priceChartData = computed(() => {
  if (!priceHistory.value || !priceHistory.value.length) {
    return { labels: [], datasets: [] }
  }

  const priceMap = new Map()
  for (const p of priceHistory.value) {
    priceMap.set(p.trade_date, p.price)
  }
  const labels = [...priceMap.keys()].sort()
  const data = labels.map(date => priceMap.get(date) || 0)

  return {
    labels,
    datasets: [{
      label: 'Цена единицы актива',
      data,
      color: '#f59e0b',
      fill: true
    }]
  }
})

// Данные для графика стоимости позиции (вкладка "Аналитика")
const positionChartData = computed(() => {
  if (!selectedPortfolioAsset.value) return { labels: [], datasets: [] }

  if (assetDailyValues.value && assetDailyValues.value.length > 0) {
    let filteredValues = [...assetDailyValues.value]

    if (firstTransactionDate.value) {
      filteredValues = filteredValues.filter(v => {
        const valueDate = new Date(v.report_date)
        valueDate.setHours(0, 0, 0, 0)
        const firstDate = new Date(firstTransactionDate.value)
        firstDate.setHours(0, 0, 0, 0)
        return valueDate >= firstDate
      })
    }

    filteredValues.sort((a, b) => new Date(a.report_date) - new Date(b.report_date))

    if (filteredValues.length > 0) {
      return {
        labels: filteredValues.map(v => v.report_date),
        datasets: [{
          label: 'Стоимость позиции',
          data: filteredValues.map(v => Number(v.position_value ?? 0)),
          color: '#3b82f6',
          fill: true
        }]
      }
    }
  }

  if (!priceHistory.value?.length) return { labels: [], datasets: [] }

  const asset = selectedPortfolioAsset.value
  const leverage = asset.leverage || 1
  const currencyRate = asset.currency_rate_to_rub || portfolioAsset.value?.asset.currency_rate_to_rub || 1

  let filteredPrices = priceHistory.value
  if (firstTransactionDate.value) {
    const firstDateStr = typeof firstTransactionDate.value === 'string'
      ? firstTransactionDate.value.split('T')[0]
      : normalizeDateToString(new Date(firstTransactionDate.value)) || ''
    filteredPrices = filteredPrices.filter(p => (p.trade_date || '').split('T')[0] >= firstDateStr)
  }
  if (!filteredPrices.length) return { labels: [], datasets: [] }

  const priceMap = new Map()
  for (const p of filteredPrices) priceMap.set(p.trade_date, p.price)
  const labels = [...priceMap.keys()].sort()
  const quantities = quantityByDate.value

  return {
    labels,
    datasets: [{
      label: 'Стоимость позиции',
      data: labels.map(date => {
        const qty = quantities[date.split('T')[0]] || 0
        const price = priceMap.get(date) || 0
        return (qty * price / leverage) * currencyRate
      }),
      color: '#3b82f6',
      fill: true
    }]
  }
})

// Данные для графика количества (вкладка "Аналитика")
const quantityChartData = computed(() => {
  if (!selectedPortfolioAsset.value) return { labels: [], datasets: [] }

  if (assetDailyValues.value && assetDailyValues.value.length > 0) {
    let filteredValues = [...assetDailyValues.value]
    if (firstTransactionDate.value) {
      filteredValues = filteredValues.filter(v => {
        const valueDate = new Date(v.report_date)
        valueDate.setHours(0, 0, 0, 0)
        const firstDate = new Date(firstTransactionDate.value)
        firstDate.setHours(0, 0, 0, 0)
        return valueDate >= firstDate
      })
    }
    if (filteredValues.length > 0) {
      return {
        labels: filteredValues.map(v => v.report_date),
        datasets: [{
          label: 'Количество актива',
          data: filteredValues.map(v => v.quantity || 0),
          color: '#10b981',
          fill: true
        }]
      }
    }
  }

  if (!priceHistory.value?.length) return { labels: [], datasets: [] }

  let filteredPrices = priceHistory.value
  if (firstTransactionDate.value) {
    const firstDateStr = typeof firstTransactionDate.value === 'string'
      ? firstTransactionDate.value.split('T')[0]
      : normalizeDateToString(new Date(firstTransactionDate.value)) || ''
    filteredPrices = filteredPrices.filter(p => (p.trade_date || '').split('T')[0] >= firstDateStr)
  }
  if (!filteredPrices.length) return { labels: [], datasets: [] }

  const priceMap = new Map()
  for (const p of filteredPrices) priceMap.set(p.trade_date, p.price)
  const labels = [...priceMap.keys()].sort()
  const quantities = quantityByDate.value

  return {
    labels,
    datasets: [{
      label: 'Количество актива',
      data: labels.map(date => quantities[date.split('T')[0]] || 0),
      color: '#10b981',
      fill: true
    }]
  }
})

const analyticsChartData = computed(() =>
  analyticsChartMetric.value === 'position' ? positionChartData.value : quantityChartData.value
)

const analyticsChartYType = computed(() =>
  analyticsChartMetric.value === 'position' ? 'position' : 'quantity'
)

const analyticsChartTitle = computed(() =>
  analyticsChartMetric.value === 'position' ? 'Стоимость позиции' : 'Количество актива'
)

const analyticsChartFormatter = computed(() =>
  analyticsChartMetric.value === 'position' ? formatPositionCurrency : formatQuantity
)

// Форматирование для графика количества (без валюты)
const formatQuantity = (value) => {
  if (typeof value !== 'number') return value
  return value.toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 8
  })
}

// Форматирование для графика стоимости позиции (в рублях)
const formatPositionCurrency = (value) => {
  return formatOperationAmount(value || 0, 'RUB')
}

// --- Period summary для графиков ---
function getPeriodStartDateByKey(period) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  if (period === '7D') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 7)
  if (period === '1M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 30)
  if (period === '3M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 90)
  if (period === '6M') return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 180)
  if (period === 'YTD') return new Date(today.getFullYear(), 0, 1)
  if (period === '1Y') return new Date(today.getFullYear(), today.getMonth() - 11, 1)
  if (period === '5Y') return new Date(today.getFullYear() - 5, today.getMonth(), today.getDate())
  return null
}

function computePeriodStats(chartData, period) {
  const labels = chartData?.labels
  const data = chartData?.datasets?.[0]?.data
  if (!labels?.length || !data?.length) return { changeValue: 0, changePercent: 0, startDate: null, endDate: null }

  const today = new Date()
  today.setHours(23, 59, 59, 999)
  const points = labels.map((label, i) => ({
    date: new Date(label),
    value: Number(data[i]) || 0
  })).sort((a, b) => a.date - b.date)
  if (!points.length) return { changeValue: 0, changePercent: 0, startDate: null, endDate: null }

  const start = getPeriodStartDateByKey(period)
  let filtered = points
  if (start) {
    start.setHours(0, 0, 0, 0)
    filtered = points.filter(p => {
      const pd = new Date(p.date)
      pd.setHours(0, 0, 0, 0)
      return pd >= start && pd <= today
    })
    if (!filtered.length) {
      const before = points.filter(p => p.date <= today)
      filtered = before.length ? [before[before.length - 1]] : [points[0]]
    }
  }

  const first = filtered[0].value
  const last = filtered[filtered.length - 1].value
  const changeValue = last - first
  const changePercent = first === 0 ? 0 : (changeValue / Math.abs(first)) * 100
  return {
    changeValue,
    changePercent,
    startDate: filtered[0].date,
    endDate: filtered[filtered.length - 1].date
  }
}

const priceChartPeriodStats = computed(() => computePeriodStats(priceChartData.value, selectedPeriod.value))
const analyticsChartPeriodStats = computed(() => computePeriodStats(analyticsChartData.value, selectedPeriod.value))

const formatPriceChangeValue = computed(() => {
  const currency = assetQuoteCurrency.value
  return (v) => formatOperationAmount(v || 0, currency)
})

const formatAnalyticsChangeValue = computed(() => {
  if (analyticsChartMetric.value === 'quantity') return (v) => formatQuantity(v)
  return (v) => formatOperationAmount(v || 0, 'RUB')
})

// Определяем валюту актива для графика цены единицы (computed для реактивности)
// Используем ту же логику, что и в basicInfoItems
const assetQuoteCurrency = computed(() => {
  const quoteAssetId = selectedPortfolioAsset.value?.quote_asset_id || 
                       assetInfo.value?.quote_asset_id ||
                       portfolioAsset.value?.asset?.quote_asset_id
  
  if (quoteAssetId) {
    const refData = dashboardStore.referenceData
    
    // Ищем валюту в списке валют (currencies)
    if (refData?.currencies) {
      const currency = refData.currencies.find(c => c.id === quoteAssetId)
      if (currency && currency.ticker) {
        // Нормализуем ticker (берем первые 3 символа)
        const normalized = currency.ticker.trim().substring(0, 3).toUpperCase()
        const validCurrencyCodes = ['RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
        if (validCurrencyCodes.includes(normalized)) {
          return normalized
        }
        return currency.ticker
      }
    }
    
  }
  
  // Fallback: используем currency_ticker из данных актива
  const currencyTicker = selectedPortfolioAsset.value?.currency_ticker || 
                         assetInfo.value?.currency_ticker ||
                         portfolioAsset.value?.asset?.currency_ticker
  
  if (currencyTicker) {
    const normalized = normalizeCurrencyTicker(currencyTicker)
    if (normalized !== 'RUB') {
      return normalized
    }
  }
  
  return 'RUB'
})

// Форматирование для графика цены единицы (в валюте актива) - computed для реактивности
// Важно: используем assetQuoteCurrency.value при каждом вызове, чтобы всегда получать актуальное значение
const formatPriceCurrency = computed(() => {
  return (value) => {
    // Всегда используем актуальное значение assetQuoteCurrency.value
    const currency = assetQuoteCurrency.value
    return formatOperationAmount(value || 0, currency)
  }
})

// Выбираем форматтер в зависимости от типа графика
const chartFormatter = computed(() => {
  if (selectedChartType.value === 'quantity') {
    return formatQuantity
  } else if (selectedChartType.value === 'position') {
    return formatPositionCurrency
  } else if (selectedChartType.value === 'price') {
    return formatPriceCurrency.value
  }
  return formatCurrency
})

// Поиск корневого портфеля "Все активы" (портфель без parent_portfolio_id)
const rootPortfolio = computed(() => {
  if (!portfolios.value || !portfolios.value.length) return null
  
  // Ищем портфель без parent_portfolio_id (корневой)
  return portfolios.value.find(p => !p.parent_portfolio_id) || null
})

// Сводка по всем портфелям, где есть этот актив (шапка страницы)
const aggregatedPortfolioMetrics = computed(() => {
  const list = assetInAllPortfolios.value
  if (!list || !list.length) return null

  let totalQuantity = 0
  let totalValueRub = 0
  let totalPnl = 0

  for (const p of list) {
    totalQuantity += Number(p.quantity) || 0
    totalValueRub += Number(p.asset_value) || 0
    totalPnl += Number(p.total_pnl) || 0
  }

  const rootVal = Number(rootPortfolio.value?.total_value) || 0
  const shareInRootPercent = rootVal > 0 ? (totalValueRub / rootVal) * 100 : null

  return {
    totalQuantity,
    totalValueRub,
    shareInRootPercent,
    totalPnl,
    isProfit: totalPnl >= 0
  }
})

/** Цена в шапке (чистая + НКД), для отображения */
const headerUnitPriceDisplay = computed(() => {
  const pa = selectedPortfolioAsset.value
  const a = portfolioAsset.value?.asset
  const src = pa || a
  if (!src) return '-'
  const u = effectiveUnitPriceInCurrency(src)
  if (u === 0 && src.last_price == null && !(Number(src.accrued_coupon) > 0)) return '-'
  return u.toFixed(2)
})

// Расчет роста цены для выбранного портфеля
const selectedPriceGrowth = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const asset = selectedPortfolioAsset.value
  const currentPrice = effectiveUnitPriceInCurrency(asset)
  const averagePrice = asset.average_price || 0
  
  if (averagePrice === 0) return null
  
  const percent = ((currentPrice - averagePrice) / averagePrice) * 100
  
  return {
    percent,
    isPositive: percent >= 0
  }
})

// Комиссии из cash_operations для выбранного портфеля
const commissionsTotal = computed(() => {
  // Фильтруем только комиссии для выбранного портфеля
  const commissionsList = allCashOperationsList.value.filter(op => {
    const opType = (op.operation_type || op.type || '').toLowerCase()
    const opTypeId = op.operation_type_id
    return (opType.includes('commission') || opType.includes('комиссия') || opType.includes('commision') || opTypeId === 7)
  })
  
  // Суммируем комиссии в рублях (amount_rub уже рассчитан по курсу на дату операции)
  // Комиссии - это расходы, поэтому берем абсолютное значение (на случай если они отрицательные в базе)
  return commissionsList.reduce((sum, op) => {
    const amountRub = Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
    // Берем абсолютное значение, так как комиссии - это всегда расходы (положительная сумма)
    return sum + Math.abs(amountRub)
  }, 0)
})

// Расчет общей прибыли для выбранного портфеля
// ИСПРАВЛЕНО: используем total_pnl из portfolio_asset_daily_values вместо пересчета
const selectedTotalProfit = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  // Используем total_pnl из portfolio_asset_daily_values (уже рассчитан в БД)
  const totalPnl = selectedPortfolioAsset.value.total_pnl || 0
  
  // Для совместимости разбиваем на компоненты (если нужно для отображения)
  const unrealized = selectedProfitLoss.value?.profit || 0
  const realized = realizedProfit.value || 0
  const payoutAmount = selectedPortfolioAsset.value.payouts || 0
  const commissions = Math.abs(selectedPortfolioAsset.value.commissions || 0)
  
  return {
    unrealized,
    realized,
    payouts: payoutAmount,
    commissions,
    total: totalPnl,  // Используем total_pnl из таблицы
    isProfit: totalPnl >= 0
  }
})

// Полученные выплаты (из cash_operations)
const receivedPayouts = computed(() => {
  return receivedPayoutsTotal.value
})

// Нормализует код валюты (защита от некорректных значений типа "RUB000UTSTOM")
const normalizeCurrencyTicker = (ticker) => {
  if (!ticker || typeof ticker !== 'string') return 'RUB'
  
  // Берем только первые 3 символа и приводим к верхнему регистру
  const normalized = ticker.trim().substring(0, 3).toUpperCase()
  
  // Список валидных кодов валют
  const validCurrencyCodes = ['RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
  if (validCurrencyCodes.includes(normalized)) {
    return normalized
  }
  
  // Если не валидный код, пробуем найти в referenceData
  const refData = dashboardStore.referenceData
  if (refData && refData.currencies) {
    const currency = refData.currencies.find(c => {
      const cTicker = c.ticker || ''
      return cTicker.toUpperCase() === normalized || cTicker.toUpperCase().startsWith(normalized)
    })
    if (currency && currency.ticker) {
      return currency.ticker.toUpperCase()
    }
  }
  
  return 'RUB'
}

// Определяем валюту актива из quote_asset_id
const assetCurrency = computed(() => {
  // Сначала пытаемся найти валюту по quote_asset_id в referenceData (наиболее надежный способ)
  const quoteAssetId = assetInfo.value?.quote_asset_id || 
                       selectedPortfolioAsset.value?.quote_asset_id ||
                       portfolioAsset.value?.asset?.quote_asset_id
  
  if (quoteAssetId) {
    const refData = dashboardStore.referenceData
    
    // Ищем валюту в списке валют (currencies)
    if (refData && refData.currencies) {
      const currency = refData.currencies.find(c => c.id === quoteAssetId)
      if (currency && currency.ticker) {
        return normalizeCurrencyTicker(currency.ticker)
      }
    }
    
  }
  
  // Если не нашли по quote_asset_id, пробуем получить из currency_ticker (но нормализуем)
  let currencyTicker = null
  if (selectedPortfolioAsset.value?.currency_ticker) {
    currencyTicker = selectedPortfolioAsset.value.currency_ticker
  } else if (assetInfo.value?.currency_ticker) {
    currencyTicker = assetInfo.value.currency_ticker
  } else if (portfolioAsset.value?.asset?.currency_ticker) {
    currencyTicker = portfolioAsset.value.asset.currency_ticker
  }
  
  // Если нашли ticker, нормализуем его (защита от некорректных значений типа "RUB000UTSTOM")
  if (currencyTicker) {
    return normalizeCurrencyTicker(currencyTicker)
  }
  
  // Если ничего не найдено
  return 'RUB'
})

const assetHistoryTitle = computed(() => {
  const cur = assetCurrency.value
  if (cur && selectedChartType.value === 'price') {
    return `История актива (цена в ${cur})`
  }
  return 'История актива'
})

// Расчет доли в корневом портфеле для выбранного портфеля
const selectedPortfolioPercentageInRoot = computed(() => {
  if (!selectedPortfolioAsset.value) return null

  const rootValue = rootPortfolio.value?.total_value || 0
  const assetValue = selectedPortfolioAsset.value.asset_value || 0

  if (rootValue === 0) return null

  return (assetValue / rootValue) * 100
})

// Computed properties для виджетов метрик
const basicInfoItems = computed(() => {
  // Для "Основная информация" используем валюту актива (quote_asset_id)
  // Например, для BTC это будет USD
  const quoteAssetId = selectedPortfolioAsset.value?.quote_asset_id || 
                       assetInfo.value?.quote_asset_id ||
                       portfolioAsset.value?.asset?.quote_asset_id
  
  let assetQuoteCurrency = 'RUB'
  if (quoteAssetId) {
    const refData = dashboardStore.referenceData
    if (refData?.currencies) {
      const currency = refData.currencies.find(c => c.id === quoteAssetId)
      if (currency && currency.ticker) {
        assetQuoteCurrency = currency.ticker
      }
    }
  }
  
  const result = [
    { label: 'Количество', value: selectedPortfolioAsset.value?.quantity || 0, format: 'number' },
    { 
      label: 'Средняя цена', 
      value: selectedPortfolioAsset.value?.average_price || 0, 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, assetQuoteCurrency)
    },
    { 
      label: 'Текущая цена', 
      value: effectiveUnitPriceInCurrency(selectedPortfolioAsset.value), 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, assetQuoteCurrency)
    }
  ]
  
  if (selectedPriceGrowth.value) {
    result.push({
      label: 'Рост цены',
      value: selectedPriceGrowth.value.percent,
      format: 'percent',
      isPositive: selectedPriceGrowth.value.isPositive,
      showValueChange: true
    })
  }
  
  return result
})

const contributionItems = computed(() => {
  // Для "Вклад в портфель" все значения в рублях
  const result = [
    { 
      label: 'Общая стоимость портфеля', 
      value: selectedPortfolioAsset.value?.portfolio_total_value || 0, 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, 'RUB')
    },
    { 
      label: 'Стоимость актива', 
      value: selectedPortfolioAsset.value?.asset_value || 0, 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, 'RUB')
    },
    { label: 'Доля в портфеле', value: selectedPortfolioAsset.value?.percentage_in_portfolio || 0, format: 'number', suffix: '%' }
  ]
  
  if (selectedPortfolioPercentageInRoot.value !== null && selectedPortfolioPercentageInRoot.value !== undefined) {
    result.push({
      label: 'Доля в портфеле "Все активы"',
      value: selectedPortfolioPercentageInRoot.value,
      format: 'number',
      suffix: '%'
    })
  }
  
  return result
})

const profitLossItems = computed(() => {
  // Для "Прибыль и убытки" все значения всегда в рублях
  // (так как все операции конвертируются в рубли через amount_rub)
  // Инвестированная сумма рассчитывается из amount_rub операций покупки
  // Текущая стоимость конвертируется в рубли через currency_rate_to_rub
  const displayCurrency = 'RUB'
  
  return [
    { 
      label: 'Инвестировано', 
      value: selectedProfitLoss.value?.invested || 0, 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, displayCurrency)
    },
    { 
      label: 'Текущая стоимость', 
      value: selectedProfitLoss.value?.currentValue || 0, 
      format: 'currency',
      formatter: (v) => formatOperationAmount(v, displayCurrency)
    },
    { 
      label: 'Нереализованная прибыль', 
      value: selectedProfitLoss.value?.profit || 0, 
      format: 'currency',
      isPositive: selectedProfitLoss.value?.isProfit || false,
      formatter: (v) => formatOperationAmount(v, displayCurrency)
    },
    { 
      label: 'Прибыль от продаж', 
      value: realizedProfit.value || 0, 
      format: 'currency',
      isPositive: realizedProfit.value >= 0,
      formatter: (v) => formatOperationAmount(v, displayCurrency)
    },
    { 
      label: 'Получено выплат', 
      // ОПТИМИЗИРОВАНО: используем payouts из portfolio_asset_daily_values (уже в RUB)
      value: selectedPortfolioAsset.value?.payouts || 0, 
      format: 'currency',
      colorClass: 'profit',
      formatter: (v) => formatOperationAmount(v, 'RUB')
    },
    { 
      label: 'Комиссии', 
      // ОПТИМИЗИРОВАНО: используем commissions из portfolio_asset_daily_values (уже в RUB)
      value: Math.abs(selectedPortfolioAsset.value?.commissions || 0), 
      format: 'currency',
      // Если комиссии равны 0, показываем зеленым (как выплаты), иначе красным (расход)
      colorClass: (selectedPortfolioAsset.value?.commissions || 0) === 0 ? 'profit' : 'loss',
      formatter: (v) => {
        // Если значение 0, показываем просто 0 без минуса
        if (v === 0) return formatOperationAmount(0, 'RUB')
        return formatOperationAmount(-v, 'RUB') // Вычитаем при форматировании
      }
    },
    { 
      label: 'Общая прибыль', 
      value: selectedTotalProfit.value?.total || 0, 
      format: 'currency',
      isPositive: selectedTotalProfit.value?.isProfit || false,
      formatter: (v) => formatOperationAmount(v, displayCurrency)
    }
  ]
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

// Расчет инвестированной суммы из операций покупки (используем amount_rub)
const investedFromOperations = computed(() => {
  if (!selectedPortfolioAsset.value || !cashOperations.value) return 0
  
  const portfolioId = selectedPortfolioAsset.value.portfolio_id
  const assetId = selectedPortfolioAsset.value.asset_id || assetInfo.value?.asset_id
  
  if (!portfolioId || !assetId) return 0
  
  // Фильтруем операции покупки (Buy) для выбранного портфеля и актива
  const buyOperations = cashOperations.value.filter(op => {
    const opType = (op.operation_type || op.type || '').toLowerCase()
    const opTypeId = op.operation_type_id
    const isBuy = opType.includes('buy') || opType.includes('покупка') || opTypeId === 1
    const matchesPortfolio = op.portfolio_id === portfolioId
    const matchesAsset = op.asset_id === assetId
    
    return isBuy && matchesPortfolio && matchesAsset
  })
  
  // Суммируем amount_rub из операций покупки (уже в рублях)
  // Берем по модулю, так как операции покупки могут быть отрицательными
  return buyOperations.reduce((sum, op) => {
    const amountRub = Number(op.amount_rub ?? op.amountRub ?? 0) || 0
    return sum + Math.abs(amountRub)
  }, 0)
})

// Расчет прибыли/убытка для выбранного портфеля
// ОПТИМИЗИРОВАНО: используем данные из portfolio_asset_daily_values
const selectedProfitLoss = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const asset = selectedPortfolioAsset.value
  
  // ОПТИМИЗИРОВАНО: используем invested_value из portfolio_asset_daily_values (уже в RUB)
  // Это значение корректно пересчитывается после продаж и учитывает только текущее количество
  const invested = asset.invested_value || 0
  
  // ОПТИМИЗИРОВАНО: используем asset_value из portfolio_asset_daily_values (уже в RUB)
  // Это значение корректно рассчитывается с учетом текущей цены и количества
  const currentValue = asset.asset_value || 0
  
  const profit = currentValue - invested
  const averagePrice = asset.average_price || 0
  const currentPrice = effectiveUnitPriceInCurrency(asset)
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
  // Данные приходят из бэкенда как 'all_payouts' (массив объектов выплат)
  // 'payouts' - это число (накопленная сумма), а 'all_payouts' - массив истории выплат
  const payoutHistoryRaw = assetInfo.value.all_payouts || assetInfo.value.payouts || []
  // Убеждаемся, что payoutHistory - это массив
  const payoutHistory = Array.isArray(payoutHistoryRaw) ? payoutHistoryRaw : []
  
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
// ОПТИМИЗИРОВАНО: используем realized_pnl из portfolio_asset_daily_values (уже в RUB)
const realizedProfit = computed(() => {
  // ОПТИМИЗИРОВАНО: используем realized_pnl из portfolio_asset_daily_values
  // Это значение уже рассчитано и переведено в рубли с учетом курса валюты на дату транзакции
  const realizedPnl = selectedPortfolioAsset.value?.realized_pnl || 0
  
  return realizedPnl
})

// Рост цены (в процентах)
const priceGrowth = computed(() => {
  if (!portfolioAsset.value) return null
  
  const asset = portfolioAsset.value.asset
  const currentPrice = effectiveUnitPriceInCurrency(asset)
  const averagePrice = asset.average_price || 0
  
  if (averagePrice === 0) return null
  
  const growth = ((currentPrice - averagePrice) / averagePrice) * 100
  return {
    percent: growth,
    isPositive: growth >= 0
  }
})

// Общая прибыль (unrealized + realized + выплаты - комиссии)
// ИСПРАВЛЕНО: используем total_pnl из portfolio_asset_daily_values вместо пересчета
const totalProfit = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  // Используем total_pnl из portfolio_asset_daily_values (уже рассчитан в БД)
  const totalPnl = selectedPortfolioAsset.value.total_pnl || 0
  
  // Для совместимости разбиваем на компоненты (если нужно для отображения)
  const unrealizedProfit = profitLoss.value?.profit || 0
  const realized = realizedProfit.value || 0
  const payoutAmount = selectedPortfolioAsset.value.payouts || 0
  const commissions = selectedPortfolioAsset.value.commissions || 0
  
  return {
    unrealized: unrealizedProfit,
    realized,
    payouts: payoutAmount,
    commissions,
    total: totalPnl,  // Используем total_pnl из таблицы
    isProfit: totalPnl >= 0
  }
})

// Все операции из cash_operations для выбранного портфеля
const allCashOperationsList = computed(() => {
  // Возвращаем все операции для выбранного портфеля
  return cashOperations.value || []
})

// Полученные выплаты из cash_operations (для обратной совместимости и статистики)
const receivedPayoutsList = computed(() => {
  // Фильтруем только выплаты (Dividend, Coupon) для выбранного портфеля
  return allCashOperationsList.value.filter(op => {
    const opType = (op.operation_type || op.type || '').toLowerCase()
    const opTypeId = op.operation_type_id
    return (opType.includes('dividend') || opType.includes('дивиденд') || opTypeId === 3) ||
           (opType.includes('coupon') || opType.includes('купон') || opTypeId === 4)
  })
})

// Сумма полученных выплат в рублях (используем amount_rub из базы данных)
// amount_rub рассчитывается по курсу валюты на дату операции
const receivedPayoutsTotal = computed(() => {
  if (!receivedPayoutsList.value || receivedPayoutsList.value.length === 0) {
    return 0
  }
  
  // Суммируем выплаты в рублях (amount_rub уже рассчитан по курсу на дату операции)
  const total = receivedPayoutsList.value.reduce((sum, op) => {
    // Проверяем оба варианта: snake_case (amount_rub) и camelCase (amountRub)
    // Также проверяем, что значение не null и не undefined
    const amountRub = Number(op.amount_rub ?? op.amountRub ?? op.amount) || 0
    return sum + amountRub
  }, 0)
  
  return total
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
        amount: tx.price * tx.quantity || 0,
        currency: assetCurrency.value
      })
    })
  }
  
  // Собираем ID транзакций для исключения дублирования
  const transactionIds = new Set()
  transactions.forEach(tx => {
    if (tx.id) transactionIds.add(tx.id)
    if (tx.transaction_id) transactionIds.add(tx.transaction_id)
  })
  
  // Добавляем все операции из cash_operations для выбранного портфеля
  // Исключаем операции, которые созданы из транзакций (Buy/Sell)
  allCashOperationsList.value.forEach(op => {
    // Пропускаем cash_operations, которые связаны с транзакциями (созданы триггером)
    // Проверяем по transaction_id
    if (op.transaction_id) {
      const txId = op.transaction_id
      // Проверяем все возможные форматы ID
      if (transactionIds.has(txId) || 
          transactionIds.has(Number(txId)) || 
          transactionIds.has(String(txId))) {
        return // Пропускаем, так как это дубликат транзакции
      }
    }
    
    // Также пропускаем операции типа Buy/Sell из cash_operations (они должны быть только в transactions)
    const opType = (op.operation_type || op.type || '').toLowerCase()
    const opTypeId = op.operation_type_id
    if (opType.includes('buy') || opType.includes('покупка') || opTypeId === 1 ||
        opType.includes('sell') || opType.includes('продажа') || opTypeId === 2) {
      return // Пропускаем Buy/Sell из cash_operations
    }
    
    // Определяем тип операции по текстовому названию из operation_type
    // opType уже объявлен выше для проверки Buy/Sell
    let operationType = 0
    
    // Определяем тип операции по названию (из get_cash_operations приходит переведенное название)
    if (opType.includes('дивиденд') || opType.includes('dividend')) {
      operationType = 3 // Дивиденды
    } else if (opType.includes('купон') || opType.includes('coupon')) {
      operationType = 4 // Купоны
    } else if (opType.includes('комиссия') || opType.includes('commission') || opType.includes('commision')) {
      operationType = 7 // Комиссия
    } else if (opType.includes('налог') || opType.includes('tax')) {
      operationType = 8 // Налог
    } else if (opType.includes('депозит') || opType.includes('пополнение') || opType.includes('deposit')) {
      operationType = 5 // Пополнение
    } else if (opType.includes('вывод') || opType.includes('withdraw')) {
      operationType = 6 // Вывод
    } else if (opType.includes('аморт') || opType.includes('amortization') || opType.includes('погаш')) {
      operationType = 9 // Амортизация
    } else if (opType.includes('другое') || opType.includes('other')) {
      operationType = 10 // Другое
    }
    
    // Если не удалось определить по названию, пытаемся по operation_type_id (если есть)
    if (operationType === 0 && op.operation_type_id) {
      operationType = op.operation_type_id
    }
    
    // Определяем валюту операции: из currency_ticker операции или из валюты актива
    const operationCurrency = op.currency_ticker || assetCurrency.value
    
    // Используем amount_rub (уже переведено в рубли по курсу на дату операции)
    // amount - это сумма в исходной валюте операции, amount_rub - сумма в рублях
    // Проверяем оба варианта: snake_case (amount_rub) и camelCase (amountRub)
    // Приоритет: amount_rub > amountRub > amount (fallback для старых записей)
    const operationAmountRub = Number(
      op.amount_rub ?? 
      op.amountRub ?? 
      (op.currency_ticker && op.currency_ticker !== 'RUB' ? 0 : op.amount) ?? 
      0
    ) || 0
    
    // Определяем категорию операции для отображения
    let operationCategory = 'cash'
    if (operationType === 3 || operationType === 4) {
      operationCategory = 'payout'
    } else if (operationType === 7 || operationType === 8) {
      operationCategory = 'expense'
    } else if (operationType === 5 || operationType === 6) {
      operationCategory = 'cash'
    } else {
      operationCategory = 'other'
    }
    
    operations.push({
      id: `cash_op_${op.cash_operation_id || op.id}`,
      type: operationCategory,
      date: op.operation_date || op.date,
      operationType: operationType,
      quantity: null,
      price: null,
      amount: operationAmountRub, // Используем amount_rub для отображения в рублях
      amount_original: Number(op.amount) || 0, // Сохраняем оригинальную сумму в исходной валюте
      currency: 'RUB', // Операции всегда отображаем в рублях (amount_rub)
      currency_original: operationCurrency // Сохраняем исходную валюту операции
    })
  })
  
  // Сортируем по дате (от новых к старым)
  return operations.sort((a, b) => {
    const dateA = new Date(a.date)
    const dateB = new Date(b.date)
    return dateB - dateA
  })
})

// Форматирование валюты (использует валюту актива)
const formatCurrency = (value) => {
  return formatOperationAmount(value || 0, assetCurrency.value)
}

// Сортировка выплат по дате отсечки (новые сверху; без отсечки — по дате выплаты)
const sortedPayouts = computed(() => {
  if (!payouts.value?.history) return []
  const key = (p) => new Date(p.record_date || p.payment_date || p.date || 0).getTime()
  return [...payouts.value.history].sort((a, b) => key(b) - key(a))
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

/** Статус: по дате выплаты; если её нет (часто у прогнозов с dohod.ru) — по дате отсечки */
const getPayoutStatus = (p) => {
  const todayStr = normalizeDateToString(new Date())
  const payStr = normalizeDateToString(p.payment_date || p.date)
  if (payStr) {
    if (payStr > todayStr) return { key: 'forecast', label: 'Прогноз' }
    return { key: 'paid', label: 'Выплачены' }
  }
  const recordStr = normalizeDateToString(p.record_date)
  if (recordStr) {
    if (recordStr > todayStr) return { key: 'forecast', label: 'Прогноз' }
    return { key: 'paid', label: 'Выплачены' }
  }
  return { key: 'unknown', label: '—' }
}

const payoutTableRows = computed(() =>
  sortedPayouts.value.map((p) => ({ p, status: getPayoutStatus(p) }))
)

const formatPayoutDividendYield = (y) => {
  if (y == null || y === '') return '—'
  const n = Number(y)
  if (Number.isNaN(n)) return '—'
  return `${n.toFixed(2)} %`
}

// Нормализация типа операции (как на странице Transactions)
const normalizeType = (type, opType = null) => {
  // Для транзакций
  if (opType === 'transaction') {
    if (type === 1) return 'buy'
    if (type === 2) return 'sell'
    if (type === 3) return 'amortization'
  }
  
  // Для всех операций (по числовому типу)
  if (typeof type === 'number') {
    if (type === 1) return 'buy'
    if (type === 2) return 'sell'
    if (type === 3) return 'dividend'
    if (type === 4) return 'coupon'
    if (type === 5) return 'deposit'
    if (type === 6) return 'withdraw'
    if (type === 7) return 'commission'
    if (type === 8) return 'tax'
    if (type === 9) return 'amortization'
    if (type === 10) return 'other'
  }
  
  // Для строковых типов
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('покуп') || t.includes('buy')) return 'buy'
    if (t.includes('прод') || t.includes('sell')) return 'sell'
    if (t.includes('аморт') || t.includes('amortization') || t.includes('погаш')) return 'amortization'
    if (t.includes('див') || t.includes('div')) return 'dividend'
    if (t.includes('купон') || t.includes('coupon')) return 'coupon'
    if (t.includes('пополн') || t.includes('deposit')) return 'deposit'
    if (t.includes('вывод') || t.includes('withdraw')) return 'withdraw'
    if (t.includes('комисс') || t.includes('commission')) return 'commission'
    if (t.includes('налог') || t.includes('tax')) return 'tax'
  }
  
  // По категории операции
  if (opType === 'payout') {
    if (type === 3) return 'dividend'
    if (type === 4) return 'coupon'
  }
  if (opType === 'expense') {
    if (type === 7) return 'commission'
    if (type === 8) return 'tax'
  }
  if (opType === 'cash') {
    if (type === 5) return 'deposit'
    if (type === 6) return 'withdraw'
  }
  
  return 'other'
}

// Форматирование даты
const formatDate = formatDateForDisplay

// Получение текстового названия типа операции для отображения
const getOperationTypeLabel = (op) => {
  const operationType = op.operationType || op.type
  
  // Для транзакций
  if (op.type === 'transaction') {
    if (operationType === 1) return 'Покупка'
    if (operationType === 2) return 'Продажа'
    if (operationType === 3) return 'Погашение'
  }
  
  // Для всех остальных операций
  if (operationType === 3) return 'Дивиденды'
  if (operationType === 4) return 'Купоны'
  if (operationType === 5) return 'Пополнение'
  if (operationType === 6) return 'Вывод'
  if (operationType === 7) return 'Комиссия'
  if (operationType === 8) return 'Налог'
  if (operationType === 9) return 'Амортизация'
  if (operationType === 10) return 'Другое'
  
  // Fallback: пытаемся определить по строковому типу
  const opTypeStr = (op.operation_type || op.type || '').toLowerCase()
  if (opTypeStr.includes('dividend') || opTypeStr.includes('дивиденд')) return 'Дивиденды'
  if (opTypeStr.includes('coupon') || opTypeStr.includes('купон')) return 'Купоны'
  if (opTypeStr.includes('commission') || opTypeStr.includes('комиссия')) return 'Комиссия'
  if (opTypeStr.includes('tax') || opTypeStr.includes('налог')) return 'Налог'
  if (opTypeStr.includes('deposit') || opTypeStr.includes('пополнение')) return 'Пополнение'
  if (opTypeStr.includes('withdraw') || opTypeStr.includes('вывод')) return 'Вывод'
  if (opTypeStr.includes('other') || opTypeStr.includes('другое')) return 'Другое'
  
  return 'Операция'
}

// Загрузка при монтировании
onMounted(() => {
  // Прокручиваем страницу в начало
  window.scrollTo(0, 0)
  loadAssetInfo()
})

// Отслеживание изменений route.params.id
watch(() => route.params.id, () => {
  // Прокручиваем страницу в начало при изменении актива
  window.scrollTo(0, 0)
  loadAssetInfo()
}, { immediate: false })

// Отслеживание изменений выбранного портфеля
// ОПТИМИЗИРОВАНО: при смене портфеля загружаем данные только для нового портфеля через getPortfolioAssetInfo
let portfolioChangeTimeout = null
watch(selectedPortfolioId, async (newPortfolioId, oldPortfolioId) => {
  // Пропускаем первый вызов (инициализация)
  if (!oldPortfolioId) return
  
  if (newPortfolioId && assetInfo.value?.asset_id) {
    // Очищаем предыдущий таймаут, если он есть
    if (portfolioChangeTimeout) {
      clearTimeout(portfolioChangeTimeout)
    }
    // Задержка для предотвращения множественных вызовов при быстрой смене портфеля
    portfolioChangeTimeout = setTimeout(async () => {
      // Находим portfolio_asset_id для нового портфеля
      const newPortfolioAsset = assetInAllPortfolios.value.find(
        p => p.portfolio_id === newPortfolioId
      )
      
      if (newPortfolioAsset?.portfolio_asset_id) {
        // Загружаем данные для актива в новом портфеле через единый запрос
        try {
          const result = await assetsService.getPortfolioAssetInfo(newPortfolioAsset.portfolio_asset_id)
          if (result.success && result.portfolio_asset) {
            // Обновляем daily_values и cash_operations из нового запроса
            if (result.portfolio_asset.daily_values) {
              assetDailyValues.value = result.portfolio_asset.daily_values
            }
            if (result.portfolio_asset.cash_operations) {
              cashOperations.value = result.portfolio_asset.cash_operations
            }
            // Обновляем транзакции для нового портфеля
            if (result.portfolio_asset.transactions) {
              portfolioTransactions.value[newPortfolioAsset.portfolio_asset_id] = result.portfolio_asset.transactions
            }
          }
        } catch (error) {
          console.error('Ошибка при загрузке данных для нового портфеля:', error)
        }
      }
    }, 100)
  }
})

// ОПТИМИЗИРОВАНО: убран watch для selectedPortfolioAsset
// Данные загружаются при смене портфеля через watch(selectedPortfolioId)

// Обработчик изменения портфеля
async function handlePortfolioChange(portfolioId) {
  selectedPortfolioId.value = portfolioId
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

      <!-- Блок с названием актива, ценой, ключевыми метриками и табами -->
      <div class="asset-overview-block">
        <div class="asset-overview-top">
          <div class="asset-main-info">
            <h1 class="asset-name">{{ portfolioAsset.asset.name }}</h1>
            <div class="asset-meta">
              <span class="meta-item ticker">{{ portfolioAsset.asset.ticker }}</span>
              <span v-if="portfolioAsset.asset.leverage && portfolioAsset.asset.leverage > 1" class="meta-item">
                ×{{ portfolioAsset.asset.leverage }}
              </span>
            </div>
          </div>
          <div class="asset-price-info">
            <div class="price-main">
              {{ headerUnitPriceDisplay }}
              <span v-if="assetCurrency" class="price-currency"> {{ getCurrencySymbol(assetCurrency) }}</span>
            </div>
            <div v-if="selectedPortfolioAsset?.daily_change !== undefined && selectedPortfolioAsset.daily_change !== 0" class="price-change">
              <ValueChangePill
                :value="selectedPriceChangePercent"
                :is-positive="selectedPortfolioAsset.daily_change >= 0"
                format="percent"
              />
              <span class="price-change-currency">
                ({{ selectedPortfolioAsset.daily_change >= 0 ? '+' : '' }}{{ formatCurrency(selectedPortfolioAsset.daily_change) }})
              </span>
            </div>
          </div>
        </div>

        <!-- Ключевые метрики: сумма по всем портфелям с этим активом -->
        <div class="asset-key-metrics" v-if="aggregatedPortfolioMetrics">
          <div class="key-metric">
            <span class="key-metric-label">Количество</span>
            <span class="key-metric-value">{{ aggregatedPortfolioMetrics.totalQuantity }}</span>
          </div>
          <div class="key-metric">
            <span class="key-metric-label">Стоимость</span>
            <span class="key-metric-value">{{ formatOperationAmount(aggregatedPortfolioMetrics.totalValueRub, 'RUB') }}</span>
          </div>
          <div class="key-metric">
            <span class="key-metric-label">Доля</span>
            <span class="key-metric-value">
              {{
                aggregatedPortfolioMetrics.shareInRootPercent != null
                  ? `${aggregatedPortfolioMetrics.shareInRootPercent.toFixed(2)}%`
                  : '—'
              }}
            </span>
          </div>
          <div class="key-metric">
            <span class="key-metric-label">Общая прибыль</span>
            <span
              class="key-metric-value"
              :class="aggregatedPortfolioMetrics.isProfit ? 'text-green' : 'text-red'"
            >
              {{ formatOperationAmount(aggregatedPortfolioMetrics.totalPnl, 'RUB') }}
            </span>
          </div>
        </div>

        <!-- Табы навигации -->
        <div class="asset-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            :class="['asset-tab', { active: selectedTab === tab.id }]"
            @click="selectedTab = tab.id"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>

      <!-- ===================== TAB: Общее ===================== -->
      <template v-if="selectedTab === 'general'">
        <!-- График цены и описание актива -->
        <div class="widgets-grid">
          <WidgetContainer :gridColumn="8" minHeight="var(--widget-height-large)">
            <Widget title="История цены" :icon="LineChart">
              <template #header>
                <ChartOptionsMenu
                  :options="assetChartMenuOptions"
                  @toggle="onAssetChartOptionToggle"
                />
              </template>
              <template #subheader>
                <PeriodFilters
                  :modelValue="selectedPeriod"
                  @update:modelValue="selectedPeriod = $event"
                />
                <ChartPeriodSummary
                  :startDate="priceChartPeriodStats.startDate"
                  :endDate="priceChartPeriodStats.endDate"
                  :changeValue="priceChartPeriodStats.changeValue"
                  :changePercent="priceChartPeriodStats.changePercent"
                  :formatValue="formatPriceChangeValue"
                />
              </template>
              <div class="asset-chart-body">
                <div class="chart-container">
                  <MultiLineChart
                    v-if="priceChartData.labels.length"
                    :chartData="priceChartData"
                    :period="selectedPeriod"
                    chartType="price"
                    :formatCurrency="formatPriceCurrency"
                    :showMinMaxGuides="showMinMax"
                  />
                  <div v-else class="no-chart-data">Нет данных для отображения графика</div>
                </div>
              </div>
            </Widget>
          </WidgetContainer>

          <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-large)">
            <Widget title="Описание актива" :icon="Hash">
              <div class="asset-description-placeholder">
                <p>Описание актива будет здесь</p>
              </div>
            </Widget>
          </WidgetContainer>
        </div>

        <div class="widgets-grid">
          <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
            <MetricsWidget title="Основная информация" :icon="Building2" :items="basicInfoItems" />
          </WidgetContainer>

          <WidgetContainer :gridColumn="8" minHeight="var(--widget-height-medium)">
            <Widget title="Операции" :icon="History">
              <div class="table-container">
                <table class="transactions-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th class="text-right">Кол-во</th>
                      <th class="text-right">Цена</th>
                      <th class="text-right">Сумма</th>
                      <th class="text-right">Валюта</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="op in allOperations" :key="op.id" class="tx-row">
                      <td class="td-date">{{ formatDate(op.date) }}</td>
                      <td>
                        <span :class="['badge', 'badge-' + normalizeType(op.operationType, op.type)]">
                          {{ getOperationTypeLabel(op) }}
                        </span>
                      </td>
                      <td class="text-right num-font">{{ op.quantity || '—' }}</td>
                      <td class="text-right num-font">{{ op.price ? op.price.toLocaleString() : '—' }}</td>
                      <td class="text-right num-font font-semibold" :class="op.amount >= 0 ? 'text-green' : 'text-red'">
                        {{ formatOperationAmount(Math.abs(op.amount || 0), op.currency || 'RUB') }}
                      </td>
                      <td class="text-right num-font">{{ op.currency || 'RUB' }}</td>
                    </tr>
                    <tr v-if="allOperations.length === 0">
                      <td colspan="6" class="empty-cell">
                        <div class="empty-state">
                          <span class="empty-icon">🔍</span>
                          <p>Операции не найдены</p>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Widget>
          </WidgetContainer>
        </div>
      </template>

      <!-- ===================== TAB: Аналитика ===================== -->
      <template v-if="selectedTab === 'analytics'">
        <!-- График: стоимость позиции или количество (переключение в меню ⋯) -->
        <div class="widgets-grid">
          <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-large)">
            <Widget :title="analyticsChartTitle" :icon="LineChart">
              <template #header>
                <ChartVariantSelect
                  v-model="analyticsChartMetric"
                  :options="analyticsChartVariants"
                />
                <ChartOptionsMenu
                  :options="analyticsChartMenuOptions"
                  @toggle="onAnalyticsChartMenuToggle"
                />
              </template>
              <template #subheader>
                <PeriodFilters
                  :modelValue="selectedPeriod"
                  @update:modelValue="selectedPeriod = $event"
                />
                <ChartPeriodSummary
                  :startDate="analyticsChartPeriodStats.startDate"
                  :endDate="analyticsChartPeriodStats.endDate"
                  :changeValue="analyticsChartPeriodStats.changeValue"
                  :changePercent="analyticsChartPeriodStats.changePercent"
                  :formatValue="formatAnalyticsChangeValue"
                />
              </template>
              <div class="asset-chart-body">
                <div class="chart-container">
                  <MultiLineChart
                    v-if="analyticsChartData.labels.length"
                    :chartData="analyticsChartData"
                    :period="selectedPeriod"
                    :chartType="analyticsChartYType"
                    :formatCurrency="analyticsChartFormatter"
                    :showMinMaxGuides="analyticsChartMetric === 'position' && showMinMax"
                  />
                  <div v-else class="no-chart-data">Нет данных для отображения графика</div>
                </div>
              </div>
            </Widget>
          </WidgetContainer>
        </div>

        <!-- Показатели аналитики -->
        <div class="widgets-grid">
          <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
            <MetricsWidget title="Вклад в портфель" :icon="PieChart" :items="contributionItems" />
          </WidgetContainer>

          <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
            <MetricsWidget title="Прибыль и убытки" :icon="TrendingDown" :items="profitLossItems" />
          </WidgetContainer>

          <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
            <MetricsWidget title="Основная информация" :icon="Building2" :items="basicInfoItems" />
          </WidgetContainer>
        </div>

        <!-- Операции -->
        <div class="widgets-grid">
          <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
            <Widget title="Операции" :icon="History">
              <div class="table-container">
                <table class="transactions-table">
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Тип</th>
                      <th class="text-right">Кол-во</th>
                      <th class="text-right">Цена</th>
                      <th class="text-right">Сумма</th>
                      <th class="text-right">Валюта</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="op in allOperations" :key="op.id" class="tx-row">
                      <td class="td-date">{{ formatDate(op.date) }}</td>
                      <td>
                        <span :class="['badge', 'badge-' + normalizeType(op.operationType, op.type)]">
                          {{ getOperationTypeLabel(op) }}
                        </span>
                      </td>
                      <td class="text-right num-font">{{ op.quantity || '—' }}</td>
                      <td class="text-right num-font">{{ op.price ? op.price.toLocaleString() : '—' }}</td>
                      <td class="text-right num-font font-semibold" :class="op.amount >= 0 ? 'text-green' : 'text-red'">
                        {{ formatOperationAmount(Math.abs(op.amount || 0), op.currency || 'RUB') }}
                      </td>
                      <td class="text-right num-font">{{ op.currency || 'RUB' }}</td>
                    </tr>
                    <tr v-if="allOperations.length === 0">
                      <td colspan="6" class="empty-cell">
                        <div class="empty-state">
                          <span class="empty-icon">🔍</span>
                          <p>Операции не найдены</p>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Widget>
          </WidgetContainer>
        </div>
      </template>

      <!-- ===================== TAB: Дивиденды ===================== -->
      <template v-if="selectedTab === 'dividends'">
        <div class="widgets-grid">
          <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
            <Widget title="История выплат" :icon="Coins">
              <div class="table-container">
                <table class="transactions-table payouts-history-table">
                  <thead>
                    <tr>
                      <th>Статус</th>
                      <th>Дата отсечки</th>
                      <th>Тип выплаты</th>
                      <th>Дата последней покупки</th>
                      <th>Дата выплаты</th>
                      <th class="text-right">Сумма</th>
                      <th class="text-right">Доходность, %</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="({ p, status }, idx) in payoutTableRows"
                      :key="p.id ?? `payout-${idx}`"
                      class="tx-row"
                    >
                      <td>
                        <span
                          class="payout-status-badge"
                          :class="{
                            'payout-status-badge--paid': status.key === 'paid',
                            'payout-status-badge--forecast': status.key === 'forecast',
                            'payout-status-badge--unknown': status.key === 'unknown'
                          }"
                        >
                          {{ status.label }}
                        </span>
                      </td>
                      <td class="td-date">{{ p.record_date ? formatDate(p.record_date) : '—' }}</td>
                      <td>
                        <span :class="['badge', 'badge-' + normalizeType(p.type)]">
                          {{ getPayoutTypeLabel(p.type) }}
                        </span>
                      </td>
                      <td class="td-date">{{ p.last_buy_date ? formatDate(p.last_buy_date) : '—' }}</td>
                      <td class="td-date">{{ (p.payment_date || p.date) ? formatDate(p.payment_date || p.date) : '—' }}</td>
                      <td class="text-right num-font font-semibold text-green">
                        {{ formatOperationAmount(Math.abs(Number(p.value) || 0), assetCurrency) }}
                      </td>
                      <td class="text-right num-font">{{ formatPayoutDividendYield(p.dividend_yield) }}</td>
                    </tr>
                    <tr v-if="payoutTableRows.length === 0">
                      <td colspan="7" class="empty-cell">
                        <div class="empty-state">
                          <span class="empty-icon">🔍</span>
                          <p>Нет данных о выплатах</p>
                        </div>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </Widget>
          </WidgetContainer>
        </div>
      </template>

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

/* Блок с названием актива, ценой, метриками и табами */
.asset-overview-block {
  background: white;
  padding: 1.5rem 1.5rem 0;
  border-radius: 12px;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.asset-overview-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  flex-wrap: wrap;
  padding-bottom: 1rem;
}

.asset-main-info {
  flex: 1;
  min-width: 200px;
}

.asset-name {
  font-size: 1.5rem;
  font-weight: 600;
  color: #111827;
  margin: 0 0 0.25rem 0;
  line-height: 1.3;
}

.asset-meta {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.meta-item {
  font-size: 0.8125rem;
  color: #9ca3af;
  font-weight: 400;
}

.meta-item.ticker {
  color: #6b7280;
  font-weight: 500;
}

.asset-price-info {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.price-main {
  font-size: 1.75rem;
  font-weight: 700;
  color: #111827;
  line-height: 1.2;
}

.price-currency {
  font-size: 1.25rem;
  color: #6b7280;
  font-weight: 500;
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

/* Ключевые метрики в overview */
.asset-key-metrics {
  display: flex;
  gap: 2rem;
  padding: 0.75rem 0;
  border-top: 1px solid #f3f4f6;
  flex-wrap: wrap;
}

.key-metric {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.key-metric-label {
  font-size: 0.6875rem;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  font-weight: 500;
}

.key-metric-value {
  font-size: 0.875rem;
  font-weight: 600;
  color: #111827;
}

/* Табы навигации */
.asset-tabs {
  display: flex;
  gap: 0;
  border-top: 1px solid #f3f4f6;
  margin: 0 -1.5rem;
  padding: 0 1.5rem;
}

.asset-tab {
  position: relative;
  padding: 0.75rem 1rem;
  background: none;
  border: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: color 0.2s;
  white-space: nowrap;
}

.asset-tab:hover {
  color: #111827;
}

.asset-tab.active {
  color: #111827;
  font-weight: 600;
}

.asset-tab.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 1rem;
  right: 1rem;
  height: 2px;
  background: #3b82f6;
  border-radius: 1px 1px 0 0;
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

.transactions-section h2,
.payouts-section h2 {
  margin: 0 0 1.5rem 0;
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
}

.asset-chart-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.asset-chart-header-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.asset-chart-body {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 0.75rem;
}

.asset-chart-period-row {
  flex-shrink: 0;
}

.chart-container {
  flex: 1;
  min-height: 360px;
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

.payout-status-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
  text-transform: none;
}

.payout-status-badge--paid {
  background: #dcfce7;
  color: #166534;
}

.payout-status-badge--forecast {
  background: #e0e7ff;
  color: #3730a3;
}

.payout-status-badge--unknown {
  background: #f3f4f6;
  color: #6b7280;
}

.badge-other {
  background: #f3f4f6;
  color: #4b5563;
}

.badge-deposit {
  background: #ccfbf1;
  color: #0f766e;
}

.badge-withdraw {
  background: #ffedd5;
  color: #9a3412;
}

.badge-tax {
  background: #fee2e2;
  color: #991b1b;
}

.badge-commission {
  background: #fef3c7;
  color: #92400e;
}

/* Стили таблицы */
.table-container {
  overflow-x: auto;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.transactions-table th {
  text-align: left;
  padding: 12px 16px;
  background: #f9fafb;
  color: #6b7280;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  border-bottom: 1px solid #e5e7eb;
}

.transactions-table th.text-right {
  text-align: right;
}

.transactions-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f3f4f6;
  vertical-align: middle;
}

.transactions-table tr:last-child td {
  border-bottom: none;
}

.transactions-table tr:hover {
  background: #f9fafb;
}

.td-date {
  color: #374151;
  white-space: nowrap;
}

.text-right {
  text-align: right !important;
}

.num-font {
  font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace;
  font-size: 13px;
  letter-spacing: -0.5px;
}

.font-semibold {
  font-weight: 600;
}

.text-green {
  color: #059669;
}

.text-red {
  color: #dc2626;
}

.empty-cell {
  text-align: center;
  padding: 40px;
}

.empty-state {
  color: #9ca3af;
}

.empty-icon {
  font-size: 32px;
  display: block;
  margin-bottom: 8px;
  opacity: 0.5;
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

  .chart-container {
    min-height: 280px;
  }
}
</style>

