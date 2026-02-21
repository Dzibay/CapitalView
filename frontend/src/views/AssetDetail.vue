<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard.store'
import { useUIStore } from '../stores/ui.store'
import MultiLineChart from '../components/MultiLineChart.vue'
import { 
  PeriodFilters, 
  WidgetContainer, 
  MetricsWidget, 
  ValueChange, 
  Widget 
} from '../components/widgets/base'
import { AssetPortfolioStatsWidget } from '../components/widgets/composite'
import { 
  OperationsListWidget, 
  AssetPayoutsListWidget 
} from '../components/widgets/lists'
import CustomSelect from '../components/base/CustomSelect.vue'
import LoadingState from '../components/base/LoadingState.vue'
import assetsService from '../services/assetsService'
import operationsService from '../services/operationsService'
import PageLayout from '../components/PageLayout.vue'
import { formatOperationAmount } from '../utils/formatCurrency'

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
      } else if (result.portfolio_asset.asset_id) {
        // Если истории нет в основном запросе, загружаем отдельно (для больших объемов данных)
        await loadPriceHistory(result.portfolio_asset.asset_id)
      }
      
      // Загружаем все операции из cash_operations
      await loadAllCashOperations()
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
    // График цены единицы актива - используем оригинальную валюту (без конвертации в рубли)
    const data = labels.map(date => {
      const price = filteredPrices.find(p => p.trade_date === date)?.price || 0
      return price // Не конвертируем в рубли, используем оригинальную цену
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
  // Используем больше знаков после запятой для малых значений (например, 0.0015)
  return value.toLocaleString('ru-RU', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 8
  })
}

// Форматирование для графика стоимости позиции (в рублях)
const formatPositionCurrency = (value) => {
  return formatOperationAmount(value || 0, 'RUB')
}

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
    
    // Если не нашли в currencies, ищем в assets (для криптовалют)
    if (refData?.assets) {
      const currencyAsset = refData.assets.find(a => a.id === quoteAssetId)
      if (currencyAsset && currencyAsset.ticker) {
        // Нормализуем ticker (берем первые 3 символа)
        const normalized = currencyAsset.ticker.trim().substring(0, 3).toUpperCase()
        const validCurrencyCodes = ['RUB', 'USD', 'EUR', 'GBP', 'CNY', 'JPY', 'BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
        if (validCurrencyCodes.includes(normalized)) {
          return normalized
        }
        return currencyAsset.ticker
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
const selectedTotalProfit = computed(() => {
  if (!selectedProfitLoss.value) return null
  
  const unrealized = selectedProfitLoss.value.profit
  const realized = realizedProfit.value
  const payoutAmount = receivedPayouts.value
  const commissions = commissionsTotal.value
  const total = unrealized + realized + payoutAmount - commissions
  
  return {
    unrealized,
    realized,
    payouts: payoutAmount,
    commissions,
    total,
    isProfit: total >= 0
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
    
    // Ищем валюту в списке активов (assets)
    if (refData && refData.assets) {
      const currencyAsset = refData.assets.find(a => a.id === quoteAssetId)
      if (currencyAsset && currencyAsset.ticker) {
        return normalizeCurrencyTicker(currencyAsset.ticker)
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
      value: selectedPortfolioAsset.value?.last_price || 0, 
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
      value: receivedPayouts.value || 0, 
      format: 'currency',
      colorClass: 'profit',
      formatter: (v) => formatOperationAmount(v, 'RUB')
    },
    { 
      label: 'Комиссии', 
      value: commissionsTotal.value || 0, 
      format: 'currency',
      colorClass: 'loss',
      formatter: (v) => formatOperationAmount(-v, 'RUB') // Вычитаем при форматировании
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
const selectedProfitLoss = computed(() => {
  if (!selectedPortfolioAsset.value) return null
  
  const asset = selectedPortfolioAsset.value
  const currentPrice = asset.last_price || 0
  const quantity = asset.quantity || 0
  const leverage = asset.leverage || 1
  
  // Используем инвестированную сумму из операций покупки (amount_rub уже в рублях)
  const invested = investedFromOperations.value
  
  // Для текущей стоимости используем текущую цену, количество и курс валюты к рублю
  const currencyRate = asset.currency_rate_to_rub || portfolioAsset.value?.asset.currency_rate_to_rub || 1
  const currentValue = (quantity * currentPrice / leverage) * currencyRate
  
  const profit = currentValue - invested
  const averagePrice = asset.average_price || 0
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
  
  // Получаем quote_asset_id актива для конвертации realized_pnl в рубли
  const quoteAssetId = selectedPortfolioAsset.value?.quote_asset_id || 
                       assetInfo.value?.quote_asset_id ||
                       portfolioAsset.value?.asset?.quote_asset_id
  
  // Получаем курс валюты актива к рублю
  const currencyRate = selectedPortfolioAsset.value?.currency_rate_to_rub || 
                       portfolioAsset.value?.asset?.currency_rate_to_rub || 
                       1
  
  // Суммируем realized_pnl из транзакций продажи, конвертируя в рубли
  // realized_pnl хранится в валюте актива (quote_asset_id), нужно конвертировать в рубли
  let totalRealized = 0
  
  for (const tx of transactions) {
    const txType = typeof tx.transaction_type === 'number' 
      ? tx.transaction_type 
      : (tx.transaction_type?.toLowerCase() === 'sell' ? 2 : 1)
    
    // Если это продажа и есть realized_pnl
    if (txType === 2 && tx.realized_pnl !== undefined && tx.realized_pnl !== null) {
      const realizedPnl = Number(tx.realized_pnl) || 0
      // Конвертируем в рубли, если актив не в рублях
      // Если quote_asset_id != RUB, то realized_pnl в валюте актива, нужно конвертировать
      if (quoteAssetId && quoteAssetId !== 47) {
        totalRealized += realizedPnl * currencyRate
      } else {
        totalRealized += realizedPnl
      }
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

// Общая прибыль (unrealized + realized + выплаты - комиссии)
const totalProfit = computed(() => {
  if (!profitLoss.value) return null
  
  const unrealizedProfit = profitLoss.value.profit || 0
  const realized = realizedProfit.value || 0
  // Используем receivedPayoutsTotal (из cash_operations, уже в рублях через amount_rub)
  // вместо payouts.value.total (из asset_payouts, старая структура)
  const payoutAmount = receivedPayoutsTotal.value || 0
  const commissions = commissionsTotal.value || 0
  
  const total = unrealizedProfit + realized + payoutAmount - commissions
  
  return {
    unrealized: unrealizedProfit,
    realized,
    payouts: payoutAmount,
    commissions,
    total,
    isProfit: total >= 0
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
    } else if (opType.includes('другое') || opType.includes('other')) {
      operationType = 9 // Другое
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
  // Для транзакций
  if (opType === 'transaction') {
    if (type === 1) return 'buy'
    if (type === 2) return 'sell'
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
    if (type === 9) return 'other'
  }
  
  // Для строковых типов
  if (typeof type === 'string') {
    const t = type.toLowerCase()
    if (t.includes('покуп') || t.includes('buy')) return 'buy'
    if (t.includes('прод') || t.includes('sell')) return 'sell'
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
const formatDate = (date) => {
  if (!date) return '—'
  return new Date(date).toLocaleDateString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric'
  })
}

// Получение текстового названия типа операции для отображения
const getOperationTypeLabel = (op) => {
  const operationType = op.operationType || op.type
  
  // Для транзакций
  if (op.type === 'transaction') {
    if (operationType === 1) return 'Покупка'
    if (operationType === 2) return 'Продажа'
  }
  
  // Для всех остальных операций
  if (operationType === 3) return 'Дивиденды'
  if (operationType === 4) return 'Купоны'
  if (operationType === 5) return 'Пополнение'
  if (operationType === 6) return 'Вывод'
  if (operationType === 7) return 'Комиссия'
  if (operationType === 8) return 'Налог'
  if (operationType === 9) return 'Другое'
  
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
watch(selectedPortfolioId, async (newPortfolioId) => {
  if (newPortfolioId && assetInfo.value?.asset_id) {
    await loadAllCashOperations()
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
          <MetricsWidget title="Основная информация" :items="basicInfoItems" />
        </WidgetContainer>

        <!-- Вклад в портфель -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
          <MetricsWidget title="Вклад в портфель" :items="contributionItems" />
        </WidgetContainer>

        <!-- Прибыль и убытки -->
        <WidgetContainer :gridColumn="4" minHeight="var(--widget-height-medium)">
          <MetricsWidget title="Прибыль и убытки" :items="profitLossItems" />
        </WidgetContainer>
      </div>

      <!-- Операции (транзакции + все операции) -->
      <div class="widgets-grid">
        <WidgetContainer :gridColumn="12" minHeight="var(--widget-height-medium)">
          <Widget title="Операции">
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

/* Table styles */
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

  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .chart-container {
    height: 300px;
  }
}
</style>

