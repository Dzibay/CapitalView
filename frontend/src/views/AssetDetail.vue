<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft } from 'lucide-vue-next'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import CustomSelect from '../components/base/CustomSelect.vue'
import assetsService from '../services/assetsService'
import operationsService from '../services/operationsService'
import { formatOperationAmount } from '../utils/formatCurrency'
import { normalizeDateToString, formatDateForDisplay } from '../utils/date'
import { effectiveUnitPriceInCurrency } from '../utils/effectiveAssetPrice'
import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvKpiStrip from '../cabinet/ui/CvKpiStrip.vue'
import CvWidget from '../cabinet/ui/CvWidget.vue'
import CvSegmented from '../cabinet/ui/CvSegmented.vue'
import DashboardSkeleton from '../cabinet/dashboard/DashboardSkeleton.vue'
import AssetSeriesWidget from '../cabinet/asset/AssetSeriesWidget.vue'
import PayoutYearsChart from '../cabinet/asset/PayoutYearsChart.vue'
import { OP_GROUPS, groupOf } from '../cabinet/operations/opKinds'
import { PAYOUT_KINDS } from '../cabinet/dividends/payoutTypes'
import { SERIES } from '../cabinet/palette'
import { money, moneyIn, pct, num, axisMoney } from '../cabinet/format'

const route = useRoute()
const router = useRouter()

// Используем stores вместо inject
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const routeAssetId = computed(() => {
  const n = parseInt(route.params.id, 10)
  return Number.isFinite(n) ? n : null
})
/** portfolio_asset_id, для которого пришли transactions/daily_values в первом ответе detail */
const initialDetailPortfolioAssetId = ref(null)
const isLoading = ref(false)
const assetInfo = ref(null)
const priceHistory = ref([])
const priceHistoryCurrency = ref(null) // Валюта истории цен (из API getAssetPriceHistory)
const assetDailyValues = ref([]) // История стоимости позиции из portfolio_asset_daily_values
const assetInAllPortfolios = ref([])
const selectedPortfolioId = ref(null)
const selectedPeriod = ref('All')
const selectedChartType = ref('position') // для устаревшего комбинированного chartData

/** Есть позиция хотя бы в одном портфеле — иначе аналитика по портфелю нечего показывать (см. get_asset_detail_for_user: portfolios = []). */
const hasUserPositionAnalytics = computed(
  () => Array.isArray(assetInAllPortfolios.value) && assetInAllPortfolios.value.length > 0
)

/** Вкладка выплат: только если в ответе есть история выплат по активу. */
const hasPayoutHistoryForTab = computed(() => {
  if (!assetInfo.value) return false
  const raw = assetInfo.value.all_payouts ?? assetInfo.value.payouts
  return Array.isArray(raw) && raw.length > 0
})

const analyticsChartMetric = ref('position') // 'position' | 'quantity'

const cashOperations = ref([]) // Все операции из cash_operations (выплаты, комиссии, налоги и т.д.)
const portfolioTransactions = ref({}) // Транзакции для каждого portfolio_asset_id


// Получаем информацию о портфеле из dashboardStore для расчета вклада
const portfolios = computed(() => dashboardStore.portfolios ?? [])

// Поиск портфеля и актива в нем
const portfolioAsset = computed(() => {
  if (!assetInfo.value?.asset_id || !portfolios.value.length) return null
  const aid = assetInfo.value.asset_id
  for (const portfolio of portfolios.value) {
    if (portfolio.assets) {
      const asset = portfolio.assets.find(a => a.asset_id === aid)
      if (asset) return { asset, portfolio }
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
  if (!assetInAllPortfolios.value.length) return null
  if (!selectedPortfolioId.value) return assetInAllPortfolios.value[0] || null
  return assetInAllPortfolios.value.find(p => p.portfolio_id === selectedPortfolioId.value) || assetInAllPortfolios.value[0] || null
})

/** Для шапки (цена): выбранная позиция или «голый» актив без позиций в портфелях */
const overviewAsset = computed(() => selectedPortfolioAsset.value || assetInfo.value)

// Загрузка информации о портфельном активе (оптимизированная версия)
async function loadAssetInfo() {
  if (routeAssetId.value == null) return

  selectedPortfolioId.value = null
  initialDetailPortfolioAssetId.value = null
  portfolioTransactions.value = {}

  isLoading.value = true
  try {
    const result = await assetsService.getAssetDetailPage(routeAssetId.value)
    if (result.success && result.portfolio_asset) {
      assetInfo.value = result.portfolio_asset
      initialDetailPortfolioAssetId.value = result.portfolio_asset.id ?? null

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

        // Сохраняем транзакции для portfolio_asset_id из ответа detail
        if (result.portfolio_asset.id != null && result.portfolio_asset.transactions) {
          portfolioTransactions.value[result.portfolio_asset.id] = result.portfolio_asset.transactions
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
  const targetPortfolioAssetId =
    selectedPortfolioAsset.value?.portfolio_asset_id ?? initialDetailPortfolioAssetId.value
  
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
  
  // Если выбранный портфель совпадает с тем, для которого загружен первичный detail
  if (selectedPortfolioAssetId === initialDetailPortfolioAssetId.value) {
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
  const currencyRate =
    asset.currency_rate_to_rub ||
    portfolioAsset.value?.asset?.currency_rate_to_rub ||
    assetInfo.value?.currency_rate_to_rub ||
    1

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
          color: '#7381ff',
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
      color: '#7381ff',
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
          color: '#b0b8ff',
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
      color: '#b0b8ff',
      fill: true
    }]
  } else if (selectedChartType.value === 'price') {
    const data = labels.map(date => priceMap.get(date) || 0)
    
    datasets = [{
      label: 'Цена единицы актива',
      data,
      color: '#7381ff',
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
      color: '#7381ff',
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
          color: '#7381ff',
          fill: true
        }]
      }
    }
  }

  if (!priceHistory.value?.length) return { labels: [], datasets: [] }

  const asset = selectedPortfolioAsset.value
  const leverage = asset.leverage || 1
  const currencyRate =
    asset.currency_rate_to_rub ||
    portfolioAsset.value?.asset?.currency_rate_to_rub ||
    assetInfo.value?.currency_rate_to_rub ||
    1

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
      color: '#7381ff',
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
          color: '#b0b8ff',
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
      color: '#b0b8ff',
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

// Сумма стоимости позиции по всем портфелям (виджет «вклад» при масштабе «Все активы»)
const sumAssetValueAcrossPortfolios = computed(() =>
  assetInAllPortfolios.value.reduce((s, p) => s + (Number(p.asset_value) || 0), 0)
)

// Ключевые метрики в шапке — только по выбранному портфелю
const aggregatedPortfolioMetrics = computed(() => {
  const pa = selectedPortfolioAsset.value
  if (!pa) return null

  const totalQuantity = Number(pa.quantity) || 0
  const totalValueRub = Number(pa.asset_value) || 0
  const totalPnl = Number(pa.total_pnl) || 0
  const portfolioTotal = Math.max(0, Number(pa.portfolio_total_value) || 0)
  const shareInPortfolioPercent =
    portfolioTotal > 0 ? (totalValueRub / portfolioTotal) * 100 : null

  return {
    totalQuantity,
    totalValueRub,
    shareInPortfolioPercent,
    totalPnl,
    isProfit: totalPnl >= 0
  }
})

/** Цена в шапке (чистая + НКД), для отображения */
const headerUnitPriceDisplay = computed(() => {
  const pa = selectedPortfolioAsset.value
  const a = portfolioAsset.value?.asset
  const src = pa || a || assetInfo.value
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

const contributionScope = ref('portfolio')

const contributionScopeOptions = [
  { value: 'portfolio', label: 'По портфелю' },
  { value: 'all_assets', label: 'По всем активам' }
]

const contributionAssetLabel = computed(() => {
  const t = selectedPortfolioAsset.value?.ticker || assetInfo.value?.ticker
  return t ? String(t).trim() : 'Этот актив'
})

const contributionAssetAllocation = computed(() => {
  const pa = selectedPortfolioAsset.value

  let totalVal = 0
  let raw = 0
  if (contributionScope.value === 'all_assets') {
    totalVal = Math.max(0, Number(rootPortfolio.value?.total_value) || 0)
    const sumAll = sumAssetValueAcrossPortfolios.value
    raw =
      sumAll > 0
        ? sumAll
        : Math.max(0, Number(pa?.asset_value) || 0)
  } else {
    totalVal = Math.max(0, Number(pa?.portfolio_total_value) || 0)
    raw = Math.max(0, Number(pa?.asset_value) || 0)
  }

  const asset = totalVal > 0 ? Math.min(raw, totalVal) : raw
  const rest = totalVal > 0 ? Math.max(0, totalVal - asset) : 0
  if (asset + rest <= 0) return null
  return {
    labels: [contributionAssetLabel.value, 'Остальные активы'],
    datasets: [{
      data: [asset, rest],
      backgroundColor: ['#7381ff', 'rgba(255, 255, 255, 0.08)']
    }]
  }
})

const contributionEmptyMessage = computed(() =>
  contributionScope.value === 'all_assets'
    ? 'Нет данных о портфеле «Все активы»'
    : 'Нет данных о стоимости портфеля'
)

function formatContributionCenterRub(value) {
  const n = Number(value)
  const x = Number.isFinite(n) ? n : 0
  return x.toLocaleString('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  })
}

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

// Изменение цены за день в процентах (выбранная позиция или актив без позиций)
const selectedPriceChangePercent = computed(() => {
  const oa = overviewAsset.value
  if (!oa || !oa.last_price) return 0

  const lastPrice = oa.last_price
  const dailyChange = oa.daily_change || 0
  
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

/** Те же строки, что в таблице «История выплат», в формате PayoutsChartWidget (агрегация по месяцу даты выплаты) */
const assetDividendPayoutsChartSeries = computed(() => {
  const byMonth = {}
  for (const p of sortedPayouts.value) {
    const raw = p.payment_date || p.date || p.record_date
    const ns = normalizeDateToString(raw)
    if (!ns || ns.length < 7) continue
    const monthKey = ns.slice(0, 7)
    if (!/^\d{4}-\d{2}$/.test(monthKey)) continue

    if (!byMonth[monthKey]) {
      byMonth[monthKey] = { month: monthKey, dividends: 0, coupons: 0, amortizations: 0 }
    }
    const value = Math.abs(Number(p.value) || 0)
    const t = (p.type || '').toLowerCase()
    if (t.includes('dividend') || t.includes('дивиденд')) {
      byMonth[monthKey].dividends += value
    } else if (t.includes('coupon') || t.includes('купон')) {
      byMonth[monthKey].coupons += value
    } else if (t.includes('amort') || t.includes('аморт')) {
      byMonth[monthKey].amortizations += value
    } else {
      byMonth[monthKey].dividends += value
    }
  }
  return Object.values(byMonth).sort((a, b) => a.month.localeCompare(b.month))
})

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

// ── Карточка актива в стиле кабинета ────────────────────────────────────────
const assetName = computed(() => portfolioAsset.value?.asset?.name ?? assetInfo.value?.name ?? '')
const assetTicker = computed(() => portfolioAsset.value?.asset?.ticker ?? assetInfo.value?.ticker ?? '')
const assetType = computed(() => assetInfo.value?.type || portfolioAsset.value?.asset?.type || '')
const assetLeverage = computed(() => Number(portfolioAsset.value?.asset?.leverage ?? assetInfo.value?.leverage) || 1)

/** Цена единицы (чистая + НКД) в валюте бумаги; дешёвые бумаги — с 4 знаками */
const unitPrice = computed(() => {
  const src = selectedPortfolioAsset.value || portfolioAsset.value?.asset || assetInfo.value
  return src ? effectiveUnitPriceInCurrency(src) : 0
})
const priceDigits = computed(() => (unitPrice.value !== 0 && Math.abs(unitPrice.value) < 1 ? 4 : 2))
const fmtPrice = (v, opts = {}) => moneyIn(v, assetCurrency.value, { digits: priceDigits.value, ...opts })
const dailyChange = computed(() => Number(overviewAsset.value?.daily_change) || 0)
const tone = (v) => (v > 0 ? 'cv-up' : v < 0 ? 'cv-down' : '')

const pageMeta = computed(() => [
  assetTicker.value,
  assetLeverage.value > 1 ? `плечо ×${assetLeverage.value}` : '',
  assetCurrency.value !== 'RUB' ? `котируется в ${assetCurrency.value}` : '',
  portfolioOptions.value.length === 1 ? `в портфеле «${portfolioOptions.value[0].label}»` : '',
].filter(Boolean))

const kpis = computed(() => {
  const hasQuote = !!overviewAsset.value?.last_price
  const list = [{
    key: 'price',
    label: 'Цена',
    value: unitPrice.value,
    format: (v) => fmtPrice(v),
    delta: hasQuote ? selectedPriceChangePercent.value : null,
    note: hasQuote ? fmtPrice(dailyChange.value, { sign: true }) : 'нет котировки',
  }]
  const m = aggregatedPortfolioMetrics.value
  if (m) {
    list.push(
      { key: 'qty', label: 'Количество', value: m.totalQuantity, format: (v) => `${num(v, 6)} шт` },
      { key: 'value', label: 'Стоимость', value: m.totalValueRub, format: (v) => money(v) },
      {
        key: 'share',
        label: 'Доля в портфеле',
        value: m.shareInPortfolioPercent ?? 0,
        format: (v) => (m.shareInPortfolioPercent == null ? '—' : pct(v, { sign: false, digits: 2 })),
      },
      {
        key: 'pnl',
        label: 'Общая прибыль',
        value: m.totalPnl,
        format: (v) => money(v, { sign: true }),
        tone: m.totalPnl > 0 ? 'up' : m.totalPnl < 0 ? 'down' : undefined,
      },
    )
  }
  return list
})

// график: цена всегда, стоимость и количество — если бумага есть в портфеле
const chartMetric = ref('price')
const seriesMetrics = computed(() => {
  const list = []
  const price = priceChartData.value
  const pos = positionChartData.value
  const qty = quantityChartData.value
  if (price.labels.length > 1) {
    list.push({
      value: 'price', label: 'Цена', title: 'Цена единицы',
      dates: price.labels, values: price.datasets[0].data,
      format: (v) => fmtPrice(v), axis: (v) => num(v, priceDigits.value),
    })
  }
  if (hasUserPositionAnalytics.value && pos.labels.length > 1) {
    list.push({
      value: 'position', label: 'Стоимость', title: 'Стоимость позиции',
      dates: pos.labels, values: pos.datasets[0].data,
      format: (v) => money(v), axis: axisMoney,
    })
  }
  if (hasUserPositionAnalytics.value && qty.labels.length > 1) {
    list.push({
      value: 'quantity', label: 'Количество', title: 'Количество',
      dates: qty.labels, values: qty.datasets[0].data,
      format: (v) => `${num(v, 6)} шт`, axis: (v) => num(v, 2),
    })
  }
  return list
})
watch(seriesMetrics, (list) => {
  if (list.length && !list.some((m) => m.value === chartMetric.value)) chartMetric.value = list[0].value
})

/** Разложение общей прибыли: рост цены, продажи, выплаты, комиссии */
const pnlParts = computed(() => {
  const pa = selectedPortfolioAsset.value
  if (!pa) return null
  const rows = [
    { key: 'unr', label: 'Рост цены', value: selectedProfitLoss.value?.profit || 0 },
    { key: 'real', label: 'Прибыль от продаж', value: realizedProfit.value || 0 },
    { key: 'pay', label: 'Выплаты', value: Number(pa.payouts) || 0 },
    { key: 'fee', label: 'Комиссии', value: -Math.abs(Number(pa.commissions) || 0) },
  ]
  const max = Math.max(1, ...rows.map((r) => Math.abs(r.value)))
  return {
    invested: selectedProfitLoss.value?.invested || 0,
    current: selectedProfitLoss.value?.currentValue || 0,
    total: selectedTotalProfit.value?.total || 0,
    rows: rows.map((r) => ({ ...r, w: (Math.abs(r.value) / max) * 100 })),
  }
})

const SCOPE_OPTIONS = [
  { value: 'portfolio', label: 'Портфель' },
  { value: 'all_assets', label: 'Все' },
]
const shareInfo = computed(() => {
  const a = contributionAssetAllocation.value
  if (!a) return null
  const [asset, rest] = a.datasets[0].data
  const total = asset + rest
  return { asset, total, share: total > 0 ? (asset / total) * 100 : 0 }
})
const positionFacts = computed(() => {
  const pa = selectedPortfolioAsset.value
  if (!pa) return []
  const g = selectedPriceGrowth.value
  return [
    { label: 'Средняя цена', value: fmtPrice(Number(pa.average_price) || 0) },
    { label: 'Текущая цена', value: fmtPrice(unitPrice.value) },
    { label: 'Цена к средней', value: g ? pct(g.percent) : '—', tone: g ? tone(g.percent) : '' },
    { label: 'Вложено', value: money(pnlParts.value?.invested || 0) },
  ]
})

// операции по позиции
const OP_SIGN = { buy: -1, sell: 1, payout: 1, fee: -1, deposit: 1, withdraw: -1, other: 0 }
const SLUG_LABEL = {
  buy: 'Покупка', sell: 'Продажа', amortization: 'Погашение', dividend: 'Дивиденды', coupon: 'Купоны',
  deposit: 'Пополнение', withdraw: 'Вывод', commission: 'Комиссия', tax: 'Налог',
}
const opRows = computed(() => allOperations.value.map((op) => {
  const slug = normalizeType(op.operationType, op.type)
  const group = groupOf(slug)
  const amount = Math.abs(Number(op.amount) || 0)
  const label = getOperationTypeLabel(op)
  return {
    id: op.id,
    date: op.date,
    // транзакции могут прийти со строковым типом («Покупка») — тогда подпись берём по нормализованному типу
    label: label === 'Операция' ? SLUG_LABEL[slug] || label : label,
    group,
    color: OP_GROUPS[group].color,
    qty: Number(op.quantity) || 0,
    price: Number(op.price) || 0,
    amount: (OP_SIGN[group] ?? 0) * amount || amount,
    currency: op.currency || 'RUB',
    income: group === 'payout',
  }
}))
const opsLimit = ref(10)

// выплаты на одну бумагу
const payoutKind = (t) => {
  const s = String(t || '').toLowerCase()
  if (s.includes('купон') || s.includes('coupon')) return 'coupon'
  if (s.includes('аморт') || s.includes('amort')) return 'amortization'
  return 'dividend'
}
const payoutChartRows = computed(() => payoutTableRows.value
  .map(({ p, status }) => {
    const raw = p.payment_date || p.date || p.record_date
    const d = raw ? new Date(raw) : null
    if (!d || Number.isNaN(d.getTime())) return null
    return { date: d, kind: payoutKind(p.type), value: Math.abs(Number(p.value) || 0), forecast: status.key === 'forecast' }
  })
  .filter(Boolean))
const payoutSummary = computed(() => {
  const yearAgo = Date.now() - 365 * 86400000
  const rows = payoutChartRows.value
  const last12 = rows.filter((r) => !r.forecast && r.date.getTime() > yearAgo).reduce((s, r) => s + r.value, 0)
  const next = rows.filter((r) => r.forecast).sort((a, b) => a.date - b.date)[0] || null
  return { last12, yieldPct: unitPrice.value ? (last12 / unitPrice.value) * 100 : null, next }
})
const payoutsLimit = ref(8)

// каскадное появление — когда пришли данные актива
const intro = ref(false)
watch(() => assetInfo.value?.asset_id, (id) => {
  if (!id) return
  intro.value = true
  opsLimit.value = 10
  payoutsLimit.value = 8
  setTimeout(() => { intro.value = false }, 1600)
})
</script>

<template>
  <div class="ad">
    <button type="button" class="ad__back cv-btn cv-btn--ghost cv-btn--sm" @click="router.back()">
      <ArrowLeft :size="15" /> Назад
    </button>

    <DashboardSkeleton v-if="isLoading || uiStore.loading" />

    <template v-else-if="assetInfo">
      <CvPageHead :eyebrow="assetType || 'Актив'" :title="assetName" :meta="pageMeta">
        <template v-if="portfolioOptions.length > 1" #actions>
          <CustomSelect
            :modelValue="selectedPortfolioId || assetInAllPortfolios[0]?.portfolio_id"
            :options="portfolioOptions"
            label=""
            placeholder="Портфель"
            :show-empty-option="false"
            option-label="label"
            option-value="value"
            :min-width="'200px'"
            :flex="'none'"
            @update:modelValue="handlePortfolioChange"
          />
        </template>
      </CvPageHead>

      <div class="cv-grid" :class="{ 'is-intro': intro }">
        <CvKpiStrip class="is-xl" :items="kpis" :style="{ '--i': 0 }" />

        <AssetSeriesWidget
          v-if="seriesMetrics.length"
          v-model:metric="chartMetric"
          class="is-xl"
          :metrics="seriesMetrics"
          :style="{ '--i': 1 }"
        />

        <CvWidget v-if="pnlParts" class="is-l" title="Из чего складывается прибыль" :style="{ '--i': 2 }">
          <div class="pl">
            <dl class="pl__top">
              <div><dt>Вложено</dt><dd class="cv-num">{{ money(pnlParts.invested) }}</dd></div>
              <div><dt>Стоит сейчас</dt><dd class="cv-num">{{ money(pnlParts.current) }}</dd></div>
            </dl>
            <ul class="pl__rows">
              <li v-for="r in pnlParts.rows" :key="r.key">
                <span class="pl__label">{{ r.label }}</span>
                <span class="pl__track"><i :class="{ 'is-neg': r.value < 0 }" :style="{ width: `${r.w}%` }" /></span>
                <b class="cv-num" :class="tone(r.value)">{{ money(r.value, { sign: true }) }}</b>
              </li>
            </ul>
            <div class="pl__total">
              <span>Общая прибыль</span>
              <b class="cv-num" :class="tone(pnlParts.total)">{{ money(pnlParts.total, { sign: true }) }}</b>
            </div>
          </div>
        </CvWidget>

        <CvWidget v-if="selectedPortfolioAsset" class="is-s is-full-md" title="Позиция" :style="{ '--i': 3 }">
          <template #actions>
            <CvSegmented v-model="contributionScope" :options="SCOPE_OPTIONS" size="sm" aria-label="Доля от" />
          </template>
          <div class="pos">
            <div v-if="shareInfo" class="pos__share">
              <span class="pos__label">Доля {{ contributionScope === 'portfolio' ? 'в портфеле' : 'во всех активах' }}</span>
              <b class="pos__big cv-num">{{ pct(shareInfo.share, { sign: false, digits: 2 }) }}</b>
              <span class="pos__bar"><i :style="{ width: `${Math.max(0.8, shareInfo.share)}%`, background: SERIES[0] }" /></span>
              <small class="cv-num">{{ money(shareInfo.asset) }} из {{ money(shareInfo.total) }}</small>
            </div>
            <dl class="pos__facts">
              <div v-for="f in positionFacts" :key="f.label">
                <dt>{{ f.label }}</dt>
                <dd class="cv-num" :class="f.tone">{{ f.value }}</dd>
              </div>
            </dl>
          </div>
        </CvWidget>

        <CvWidget v-if="hasUserPositionAnalytics" class="is-xl" title="Операции" :style="{ '--i': 4 }" flush>
          <div v-if="opRows.length" class="ad__tablewrap">
            <table class="ad__table">
              <thead>
                <tr>
                  <th>Дата</th>
                  <th>Тип</th>
                  <th class="r c-hide-s">Кол-во</th>
                  <th class="r c-hide-s">Цена</th>
                  <th class="r">Сумма</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in opRows.slice(0, opsLimit)" :key="r.id">
                  <td class="c-date cv-num">{{ formatDate(r.date) }}</td>
                  <td>
                    <span class="ad__type"><i :style="{ background: r.color }" />{{ r.label }}</span>
                    <small v-if="r.qty" class="ad__sub cv-num">{{ num(r.qty, 6) }} шт по {{ fmtPrice(r.price) }}</small>
                  </td>
                  <td class="r cv-num c-mut c-hide-s">{{ r.qty ? num(r.qty, 6) : '—' }}</td>
                  <td class="r cv-num c-mut c-hide-s">{{ r.price ? fmtPrice(r.price) : '—' }}</td>
                  <td class="r cv-num c-amt" :class="{ 'cv-up': r.income }">{{ moneyIn(r.amount, r.currency, { digits: 2, sign: true }) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="ad__empty">По этой позиции ещё нет операций.</p>
          <button
            v-if="opRows.length > opsLimit"
            type="button"
            class="cv-btn cv-btn--ghost cv-btn--sm ad__more"
            @click="opsLimit += 20"
          >
            Показать ещё {{ Math.min(20, opRows.length - opsLimit) }} из {{ opRows.length - opsLimit }}
          </button>
        </CvWidget>

        <CvWidget v-if="payoutChartRows.length" class="is-xl" title="Выплаты на одну бумагу" :style="{ '--i': 5 }">
          <div class="pys">
            <dl class="pys__sum">
              <div><dt>За последние 12 месяцев</dt><dd class="cv-num">{{ fmtPrice(payoutSummary.last12) }}</dd></div>
              <div>
                <dt>Доходность к текущей цене</dt>
                <dd class="cv-num">{{ payoutSummary.yieldPct != null ? pct(payoutSummary.yieldPct, { sign: false, digits: 2 }) : '—' }}</dd>
              </div>
              <div>
                <dt>Следующая выплата</dt>
                <dd class="cv-num">
                  <template v-if="payoutSummary.next">{{ fmtPrice(payoutSummary.next.value) }} <small>{{ formatDate(payoutSummary.next.date) }}</small></template>
                  <template v-else>—</template>
                </dd>
              </div>
            </dl>
            <PayoutYearsChart :rows="payoutChartRows" :format="(v) => fmtPrice(v)" />
          </div>
        </CvWidget>

        <CvWidget v-if="payoutTableRows.length" class="is-xl" title="История выплат" :style="{ '--i': 6 }" flush>
          <div class="ad__tablewrap">
            <table class="ad__table">
              <thead>
                <tr>
                  <th>Статус</th>
                  <th>Отсечка</th>
                  <th class="c-hide-s">Тип</th>
                  <th class="c-hide-m">Купить до</th>
                  <th class="c-hide-m">Выплата</th>
                  <th class="r">На бумагу</th>
                  <th class="r c-hide-s">Доходность</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="({ p, status }, i) in payoutTableRows.slice(0, payoutsLimit)" :key="p.id ?? `payout-${i}`">
                  <td><span class="ad__status" :class="`is-${status.key}`">{{ status.label }}</span></td>
                  <td class="c-date cv-num">{{ p.record_date ? formatDate(p.record_date) : '—' }}</td>
                  <td class="c-hide-s">
                    <span class="ad__type"><i :style="{ background: PAYOUT_KINDS[payoutKind(p.type)].color }" />{{ PAYOUT_KINDS[payoutKind(p.type)].one }}</span>
                  </td>
                  <td class="c-date cv-num c-hide-m">{{ p.last_buy_date ? formatDate(p.last_buy_date) : '—' }}</td>
                  <td class="c-date cv-num c-hide-m">{{ (p.payment_date || p.date) ? formatDate(p.payment_date || p.date) : '—' }}</td>
                  <td class="r cv-num c-amt">{{ fmtPrice(Math.abs(Number(p.value) || 0)) }}</td>
                  <td class="r cv-num c-mut c-hide-s">{{ p.dividend_yield != null && p.dividend_yield !== '' && !Number.isNaN(Number(p.dividend_yield)) ? pct(Number(p.dividend_yield), { sign: false, digits: 2 }) : '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <button
            v-if="payoutTableRows.length > payoutsLimit"
            type="button"
            class="cv-btn cv-btn--ghost cv-btn--sm ad__more"
            @click="payoutsLimit += 20"
          >
            Показать ещё {{ Math.min(20, payoutTableRows.length - payoutsLimit) }} из {{ payoutTableRows.length - payoutsLimit }}
          </button>
        </CvWidget>
      </div>
    </template>

    <div v-else class="ad__missing cv-card">
      <b>Актив не найден</b>
      <p>Возможно, его удалили или ссылка устарела.</p>
      <button type="button" class="cv-btn cv-btn--primary" @click="router.push('/assets')">К списку активов</button>
    </div>
  </div>
</template>

<style scoped>
.ad { padding-bottom: 8px; }
.ad__back { gap: 6px; margin: 18px 0 -14px -8px; color: var(--cv-mut); }
.ad__back:hover { color: var(--cv-ink); }

/* ── прибыль ─────────────────────────────────────────────────────────── */
.pl { display: flex; flex-direction: column; gap: 18px; }
.pl__top { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin: 0; }
.pl__top div { display: flex; flex-direction: column; gap: 4px; }
.pl__top dt, .pos__label, .pos__facts dt, .pys__sum dt { font-size: 12px; color: var(--cv-mut); }
.pl__top dd { margin: 0; font-family: var(--cv-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }
.pl__rows { display: flex; flex-direction: column; gap: 12px; margin: 0; padding: 0; list-style: none; }
.pl__rows li { display: grid; grid-template-columns: 150px minmax(0, 1fr) auto; align-items: center; gap: 14px; font-size: 13px; }
.pl__label { color: var(--cv-ink-2); }
.pl__track { height: 6px; border-radius: 3px; background: rgba(255, 255, 255, .04); overflow: hidden; }
.pl__track i { display: block; height: 100%; border-radius: 3px; background: var(--cv-accent); transition: width .8s var(--cv-ease); }
.pl__track i.is-neg { background: repeating-linear-gradient(135deg, #8a8d99 0 2px, transparent 2px 5px); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .14); }
.pl__rows b { min-width: 110px; text-align: right; font-weight: 600; color: var(--cv-ink); }
.pl__total { display: flex; justify-content: space-between; align-items: baseline; padding-top: 14px; border-top: 1px solid var(--cv-line); font-size: 13px; color: var(--cv-mut); }
.pl__total b { font-family: var(--cv-display); font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }

/* ── позиция ─────────────────────────────────────────────────────────── */
.pos { display: flex; flex-direction: column; gap: 18px; }
.pos__share { display: flex; flex-direction: column; gap: 6px; }
.pos__big { font-family: var(--cv-display); font-size: 26px; font-weight: 600; letter-spacing: -0.03em; color: var(--cv-ink); line-height: 1.1; }
.pos__bar { height: 8px; margin-top: 4px; border-radius: 4px; background: rgba(255, 255, 255, .05); overflow: hidden; }
.pos__bar i { display: block; height: 100%; border-radius: 4px; transition: width .8s var(--cv-ease); }
.pos__share small { font-size: 12px; color: var(--cv-dim); }
.pos__facts { display: flex; flex-direction: column; margin: 0; }
.pos__facts div { display: flex; justify-content: space-between; gap: 12px; padding: 9px 0; border-top: 1px solid var(--cv-line); }
.pos__facts dd { margin: 0; font-size: 13px; font-weight: 600; color: var(--cv-ink); }

/* ── выплаты ─────────────────────────────────────────────────────────── */
.pys { display: flex; flex-direction: column; gap: 16px; min-width: 0; }
.pys__sum { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px 24px; margin: 0; }
.pys__sum div { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.pys__sum dd { margin: 0; font-family: var(--cv-display); font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); white-space: nowrap; }
.pys__sum dd small { margin-left: 4px; font-family: inherit; font-size: 12.5px; font-weight: 500; letter-spacing: 0; color: var(--cv-dim); }

/* ── таблицы ─────────────────────────────────────────────────────────── */
.ad__tablewrap { overflow-x: auto; }
.ad__table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ad__table th {
  padding: 10px 12px; text-align: left; white-space: nowrap;
  font-size: 11px; font-weight: 550; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim);
  border-top: 1px solid var(--cv-line); border-bottom: 1px solid var(--cv-line);
}
.ad__table td { padding: 11px 12px; color: var(--cv-ink-2); border-bottom: 1px solid var(--cv-line); vertical-align: middle; }
.ad__table tbody tr { transition: background .15s; }
.ad__table tbody tr:hover { background: var(--cv-hover); }
.ad__table tbody tr:last-child td { border-bottom: 0; }
.ad__table .r { text-align: right; }
.ad__table th:first-child, .ad__table td:first-child { padding-left: 20px; }
.ad__table th:last-child, .ad__table td:last-child { padding-right: 20px; }
.c-date { white-space: nowrap; color: var(--cv-mut) !important; }
.c-mut { color: var(--cv-mut) !important; white-space: nowrap; }
.c-amt { font-weight: 600; color: var(--cv-ink) !important; white-space: nowrap; }
.c-amt.cv-up { color: var(--cv-up) !important; }
.ad__type { display: inline-flex; align-items: center; gap: 7px; white-space: nowrap; color: var(--cv-ink-2); }
.ad__type i { width: 7px; height: 7px; flex: none; border-radius: 2px; }
.ad__sub { display: none; margin-top: 3px; font-size: 11.5px; color: var(--cv-dim); white-space: nowrap; }
.ad__status {
  display: inline-flex; align-items: center; height: 22px; padding: 0 8px; border-radius: 6px;
  font-size: 11.5px; font-weight: 550; white-space: nowrap;
  color: var(--cv-ink-2); background: rgba(255, 255, 255, .05);
}
.ad__status.is-forecast { color: var(--cv-accent-ink); background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line); }
.ad__status.is-unknown { color: var(--cv-dim); }
.ad__empty { margin: 0; padding: 28px 20px; text-align: center; font-size: 13px; color: var(--cv-mut); }
.ad__more { margin: 6px 14px 4px; }

.ad__missing { display: flex; flex-direction: column; align-items: center; gap: 8px; margin-top: 40px; padding: 48px 24px; text-align: center; }
.ad__missing b { font-size: 16px; color: var(--cv-ink); }
.ad__missing p { margin: 0 0 10px; font-size: 13px; color: var(--cv-mut); }

@media (max-width: 1024px) {
  .c-hide-m { display: none; }
}
@media (max-width: 768px) {
  .ad__back { margin-bottom: -18px; }
  .pl__rows li { grid-template-columns: minmax(0, 1fr) auto; gap: 6px 12px; }
  .pl__track { grid-column: 1 / -1; grid-row: 2; }
  .pl__rows b { min-width: 0; }
  .pys__sum { grid-template-columns: 1fr 1fr; }
  .pys__sum div:last-child { grid-column: 1 / -1; }
}
@media (max-width: 600px) {
  .ad :deep(.cv-w__actions) { flex-wrap: wrap; justify-content: flex-end; flex: 1 1 100%; }
  .c-hide-s { display: none; }
  .ad__sub { display: block; }
  .ad__table th:first-child, .ad__table td:first-child { padding-left: 14px; }
  .ad__table th:last-child, .ad__table td:last-child { padding-right: 14px; }
  .ad__table th, .ad__table td { padding-left: 8px; padding-right: 8px; }
}
</style>
