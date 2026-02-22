<script setup>
import { ref, computed, watch, onMounted } from 'vue'
import { Check } from 'lucide-vue-next'
import { Button, ToggleSwitch } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import { useTransactionsStore } from '../../stores/transactions.store'
import { useDashboardStore } from '../../stores/dashboard.store'
import { useAssetsStore } from '../../stores/assets.store'
import transactionsService from '../../services/transactionsService'
import assetsService from '../../services/assetsService'

const props = defineProps({
  asset: Object,
  onSubmit: Function // универсальный обработчик добавления транзакции/операции
})

const emit = defineEmits(['close'])

const transactionsStore = useTransactionsStore()
const dashboardStore = useDashboardStore()
const assetsStore = useAssetsStore()

// Типы операций
const operationTypes = [
  { value: 1, label: 'Покупка', category: 'transaction' },
  { value: 2, label: 'Продажа', category: 'transaction' },
  { value: 3, label: 'Дивиденды', category: 'payout' },
  { value: 4, label: 'Купоны', category: 'payout' },
  { value: 7, label: 'Комиссия', category: 'expense' },
  { value: 8, label: 'Налог', category: 'expense' },
  { value: 5, label: 'Пополнение', category: 'cash' },
  { value: 6, label: 'Вывод', category: 'cash' },
  { value: 9, label: 'Другое', category: 'other' }
]

// Режим: 'single' - одна операция, 'recurring' - повторяющиеся операции
const mode = ref('single')

const operationType = ref(1) // По умолчанию Покупка
const quantity = ref(0)
const price = ref(0)
const amount = ref(0)
const dividendYield = ref(null)
const date = ref(new Date().toISOString().slice(0, 10))
const error = ref('')
const saving = ref(false)
const loadingPrice = ref(false) // Состояние загрузки рыночной цены
const priceHistoryCache = ref(null) // Кэш истории цен актива
const isLoadingHistory = ref(false) // Флаг для предотвращения двойной загрузки истории

// Поля для повторяющихся операций
const startDate = ref('')
const endDate = ref(new Date().toISOString().slice(0, 10))
const dayOfMonth = ref(new Date().getDate()) // День месяца по умолчанию - сегодняшний день

// Инициализация начальной даты из данных актива
const initializeStartDate = () => {
  if (props.asset) {
    // Начальная дата = дата первой покупки (first_purchase_date)
    if (props.asset.first_purchase_date) {
      const date = new Date(props.asset.first_purchase_date)
      if (!isNaN(date.getTime())) {
        startDate.value = date.toISOString().slice(0, 10)
        // Устанавливаем день месяца по умолчанию на день первой покупки
        dayOfMonth.value = date.getDate()
        return
      }
    }
    
    // Если first_purchase_date нет, используем сегодняшнюю дату
    if (!startDate.value) {
      startDate.value = new Date().toISOString().slice(0, 10)
    }
  } else {
    // Если asset нет, используем сегодняшнюю дату
    startDate.value = new Date().toISOString().slice(0, 10)
  }
}

// Инициализируем при монтировании и при изменении asset
onMounted(() => {
  initializeStartDate()
})

watch(() => props.asset, () => {
  initializeStartDate()
}, { immediate: true, deep: true })

// Валюты
const useCustomCurrency = ref(false)
const currencyId = ref(47) // RUB по умолчанию
const createAssetFromCurrency = ref(false) // Автоматически создать актив из валюты

// Использование рыночной цены для транзакций
const useMarketPrice = ref(false) // Переключатель для автоматической загрузки рыночной цены

// Автоматическая загрузка рыночной цены при включении переключателя
watch(useMarketPrice, async (newValue) => {
  if (newValue && isTransaction.value && props.asset?.asset_id && date.value) {
    // Загружаем цену один раз при включении переключателя
    await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
  }
})

// Автоматическое обновление цены при изменении даты, если переключатель включен
watch(date, async (newDate) => {
  if (useMarketPrice.value && isTransaction.value && props.asset?.asset_id && newDate) {
    // Обновляем цену при изменении даты
    await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
  }
})

// Получаем список валют из referenceData (включая криптовалюты)
const currencies = computed(() => {
  const refData = dashboardStore.referenceData
  if (!refData || !refData.currencies) return []
  
  // Сортируем: сначала традиционные валюты, потом криптовалюты
  const sorted = [...refData.currencies].sort((a, b) => {
    // RUB всегда первый
    if (a.ticker === 'RUB') return -1
    if (b.ticker === 'RUB') return 1
    // Потом популярные валюты (USD, EUR)
    const popular = ['USD', 'EUR', 'GBP', 'CNY', 'JPY']
    const aPopular = popular.indexOf(a.ticker)
    const bPopular = popular.indexOf(b.ticker)
    if (aPopular !== -1 && bPopular !== -1) return aPopular - bPopular
    if (aPopular !== -1) return -1
    if (bPopular !== -1) return 1
    // Потом популярные криптовалюты (BTC, ETH)
    const crypto = ['BTC', 'ETH', 'USDT', 'USDC']
    const aCrypto = crypto.indexOf(a.ticker)
    const bCrypto = crypto.indexOf(b.ticker)
    if (aCrypto !== -1 && bCrypto !== -1) return aCrypto - bCrypto
    if (aCrypto !== -1) return -1
    if (bCrypto !== -1) return 1
    // Остальные по алфавиту
    return (a.ticker || '').localeCompare(b.ticker || '')
  })
  
  return sorted.map(c => ({
    value: c.id,
    label: `${c.ticker} - ${c.name || c.ticker}`,
    ticker: c.ticker
  }))
})

// Текущая цена актива и количество для расчета доходности
const assetPrice = computed(() => {
  if (!props.asset?.last_price) return null
  return props.asset.last_price
})

const assetQuantity = computed(() => {
  if (!props.asset?.quantity) return null
  return props.asset.quantity
})

// Вычисляем количество операций для повторяющегося режима
const operationsCount = computed(() => {
  if (mode.value !== 'recurring' || !startDate.value || !endDate.value || !dayOfMonth.value) return 0
  
  const start = new Date(startDate.value)
  const end = new Date(endDate.value)
  if (end < start) return 0
  
  // Функция для получения валидного дня месяца
  const getValidDay = (year, month, day) => {
    const lastDay = new Date(year, month, 0).getDate()
    return Math.min(day, lastDay)
  }
  
  let count = 0
  let currentYear = start.getFullYear()
  let currentMonth = start.getMonth() + 1 // getMonth() возвращает 0-11
  
  // Находим первую дату операции
  let firstOpDay = getValidDay(currentYear, currentMonth, dayOfMonth.value)
  let firstOpDate = new Date(currentYear, currentMonth - 1, firstOpDay)
  
  // Если первая дата раньше startDate, переходим к следующему месяцу
  if (firstOpDate < start) {
    if (currentMonth === 12) {
      currentYear++
      currentMonth = 1
    } else {
      currentMonth++
    }
    firstOpDay = getValidDay(currentYear, currentMonth, dayOfMonth.value)
    firstOpDate = new Date(currentYear, currentMonth - 1, firstOpDay)
  }
  
  // Подсчитываем операции до endDate
  while (firstOpDate <= end) {
    if (firstOpDate >= start) {
      count++
    }
    
    // Переходим к следующему месяцу
    if (currentMonth === 12) {
      currentYear++
      currentMonth = 1
    } else {
      currentMonth++
    }
    
    firstOpDay = getValidDay(currentYear, currentMonth, dayOfMonth.value)
    firstOpDate = new Date(currentYear, currentMonth - 1, firstOpDay)
  }
  
  return count
})

// Автоматический расчет доходности для выплат с учетом валют
watch([amount, assetPrice, assetQuantity, currencyId, useCustomCurrency, operationType], () => {
  if (isPayout.value && amount.value && assetPrice.value && assetQuantity.value) {
    // Получаем валюту актива
    const assetCurrencyId = props.asset?.quote_asset_id || 47 // По умолчанию RUB
    const payoutCurrencyId = useCustomCurrency.value ? currencyId.value : 47
    
    // Получаем тикеры валют из referenceData
    const refData = dashboardStore.referenceData
    let assetCurrencyTicker = 'RUB'
    let payoutCurrencyTicker = 'RUB'
    
    if (refData && refData.currencies) {
      const assetCurrency = refData.currencies.find(c => c.id === assetCurrencyId)
      if (assetCurrency && assetCurrency.ticker) {
        assetCurrencyTicker = assetCurrency.ticker
      }
      
      const payoutCurrency = refData.currencies.find(c => c.id === payoutCurrencyId)
      if (payoutCurrency && payoutCurrency.ticker) {
        payoutCurrencyTicker = payoutCurrency.ticker
      }
    }
    
    // Рассчитываем доходность: (сумма выплаты / (цена актива * количество)) * 100
    const totalValue = assetPrice.value * assetQuantity.value
    if (totalValue > 0) {
      let payoutAmountInAssetCurrency = Math.abs(amount.value)
      
      // Если валюта выплаты отличается от валюты актива, конвертируем сумму выплаты
      if (payoutCurrencyTicker !== assetCurrencyTicker) {
        // Получаем курсы валют (если доступны)
        // Для упрощения используем прямую конвертацию через курсы, если они есть
        // Если курсов нет, используем упрощенный расчет (предполагаем 1:1 для одинаковых валют)
        // В реальности нужно получать курсы из referenceData или из данных актива
        const assetCurrencyRate = props.asset?.currency_rate_to_rub || 1
        const payoutCurrencyRate = 1 // TODO: получить курс валюты выплаты из referenceData
        
        // Конвертируем: сумма выплаты в валюте выплаты -> RUB -> валюта актива
        const amountInRub = payoutAmountInAssetCurrency * payoutCurrencyRate
        payoutAmountInAssetCurrency = assetCurrencyRate > 0 ? amountInRub / assetCurrencyRate : payoutAmountInAssetCurrency
      }
      
      dividendYield.value = parseFloat(((payoutAmountInAssetCurrency / totalValue) * 100).toFixed(4))
    } else {
      dividendYield.value = null
    }
  } else if (!isPayout.value) {
    // Сбрасываем доходность для не-выплат
    dividendYield.value = null
  }
}, { immediate: false })

// Вычисляемые свойства
const selectedOperation = computed(() => {
  return operationTypes.find(op => op.value === operationType.value)
})

const isTransaction = computed(() => {
  return operationType.value === 1 || operationType.value === 2
})

const isPayout = computed(() => {
  return operationType.value === 3 || operationType.value === 4
})

const isExpense = computed(() => {
  return operationType.value === 7 || operationType.value === 8
})

const isCashOperation = computed(() => {
  return operationType.value === 5 || operationType.value === 6
})

const isOther = computed(() => {
  return operationType.value === 9
})

const requiresQuantity = computed(() => {
  return isTransaction.value
})

const requiresAmount = computed(() => {
  return !isTransaction.value
})

const selectedCurrency = computed(() => {
  if (!useCustomCurrency.value) return { ticker: 'RUB', symbol: '₽' }
  const currency = currencies.value.find(c => c.value === currencyId.value)
  if (!currency) return { ticker: 'RUB', symbol: '₽' }
  // Используем ticker из объекта валюты
  const ticker = currency.ticker || currency.label.split(' - ')[0] || 'RUB'
  const symbols = { 
    RUB: '₽', USD: '$', EUR: '€', GBP: '£', CNY: '¥', JPY: '¥',
    BTC: '₿', ETH: 'Ξ', USDT: '₮', USDC: '₮', BNB: 'BNB', SOL: '◎'
  }
  return { ticker, symbol: symbols[ticker] || ticker }
})

const amountLabel = computed(() => {
  const symbol = selectedCurrency.value.symbol
  if (isPayout.value) return `Сумма выплаты (${symbol})`
  if (isExpense.value) return `Сумма расхода (${symbol})`
  if (isCashOperation.value) {
    return operationType.value === 5 ? `Сумма пополнения (${symbol})` : `Сумма вывода (${symbol})`
  }
  return `Сумма (${symbol})`
})

// Функция для получения portfolio_id из актива или портфелей
function getPortfolioId() {
  // Сначала пробуем получить из props.asset
  if (props.asset?.portfolio_id) {
    return props.asset.portfolio_id
  }
  
  const portfolios = dashboardStore.portfolios || []
  if (portfolios.length === 0) {
    throw new Error('Не удалось определить portfolio_id. Портфели не загружены.')
  }
  
  // Если нет в props.asset, ищем в портфелях по portfolio_asset_id
  if (props.asset?.portfolio_asset_id) {
    for (const portfolio of portfolios) {
      if (portfolio.assets && Array.isArray(portfolio.assets)) {
        const portfolioAsset = portfolio.assets.find(pa => 
          pa.portfolio_asset_id === props.asset.portfolio_asset_id ||
          pa.id === props.asset.portfolio_asset_id
        )
        if (portfolioAsset && portfolio.id) {
          return portfolio.id
        }
      }
    }
  }
  
  // Если есть asset_id, ищем портфель по asset_id
  if (props.asset?.asset_id) {
    for (const portfolio of portfolios) {
      if (portfolio.assets && Array.isArray(portfolio.assets)) {
        const portfolioAsset = portfolio.assets.find(pa => pa.asset_id === props.asset.asset_id)
        if (portfolioAsset && portfolio.id) {
          return portfolio.id
        }
      }
    }
  }
  
  // Если ничего не найдено, пробуем взять первый портфель
  if (portfolios[0]?.id) {
    return portfolios[0].id
  }
  
  throw new Error('Не удалось определить portfolio_id. Убедитесь, что выбран актив из портфеля.')
}

// Функция для поиска актива в конкретном портфеле
function findAssetInPortfolio(portfolioId, assetId) {
  const portfolio = dashboardStore.portfolios?.find(p => p.id === portfolioId)
  if (!portfolio?.assets || !Array.isArray(portfolio.assets)) {
    return null
  }
  return portfolio.assets.find(pa => pa.asset_id === assetId)
}

// Функция для поиска или создания актива по валюте
// Если актив уже существует в портфеле, просто возвращает его ID (без создания дубликата)
// Если актив есть в системе, но не в портфеле - создает portfolio_asset с quantity=0
// Если актив не найден - создает новый кастомный актив
async function findOrCreateCurrencyAsset(currencyTicker, currencyId) {
  const refData = dashboardStore.referenceData
  if (!refData?.assets) {
    throw new Error('Не удалось загрузить справочные данные')
  }
  
  // Получаем portfolio_id
  const portfolioId = getPortfolioId()
  
  // Ищем актив с таким тикером валюты
  const existingAsset = refData.assets.find(a => a.ticker === currencyTicker && !a.user_id)
  
  if (existingAsset) {
    // Проверяем, есть ли актив уже в нужном портфеле
    const portfolioAsset = findAssetInPortfolio(portfolioId, existingAsset.id)
    if (portfolioAsset) {
      // Актив уже есть в портфеле - просто возвращаем его ID
      // Это предотвращает создание дубликата и конфликтов
      // Транзакция покупки будет создана позже через createBuyTransaction
      return {
        asset_id: existingAsset.id,
        portfolio_asset_id: portfolioAsset.portfolio_asset_id || portfolioAsset.id
      }
    }
    
    // Актив есть в системе, но его нет в портфеле - создаем portfolio_asset без транзакции
    // Создаем с quantity=0, транзакция не будет создана (будет создана позже через createBuyTransaction)
    // На бэкенде это обработается корректно: если portfolio_asset уже существует, он обновится
    const assetData = {
      portfolio_id: portfolioId,
      asset_id: existingAsset.id,
      quantity: 0, // Транзакция не будет создана при quantity=0
      average_price: 1,
      date: date.value
    }
    
    const result = await assetsStore.addAsset(assetData)
    if (result.success && result.asset) {
      return {
        asset_id: existingAsset.id,
        portfolio_asset_id: result.asset.portfolio_asset_id
      }
    }
    throw new Error('Не удалось добавить актив в портфель')
  }
  
  // Актив не найден, создаем новый кастомный актив
  // Определяем asset_type_id: 6 для криптовалют, 5 для обычных валют
  const cryptoCurrencies = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL']
  const assetTypeId = cryptoCurrencies.includes(currencyTicker) ? 6 : 5
  
  // Создаем с quantity=0, транзакция не будет создана (будет создана позже через createBuyTransaction)
  const assetData = {
    portfolio_id: portfolioId,
    asset_type_id: assetTypeId,
    name: currencyTicker,
    ticker: currencyTicker,
    currency: currencyId,
    quantity: 0, // Транзакция не будет создана при quantity=0
    average_price: 1,
    date: date.value
  }
  
  const result = await assetsStore.addAsset(assetData)
  if (result.success && result.asset) {
    return {
      asset_id: result.asset.asset_id,
      portfolio_asset_id: result.asset.portfolio_asset_id
    }
  }
  
  throw new Error('Не удалось создать актив')
}

// Функция для получения цены актива на дату
// Если передан cachedHistory, использует его вместо загрузки из API
async function getAssetPriceOnDate(assetId, targetDate, cachedHistory = null) {
  try {
    // Сначала пытаемся получить информацию об активе из referenceData
    const refData = dashboardStore.referenceData
    let assetTicker = null
    let assetInfo = null
    
    if (refData?.assets) {
      assetInfo = refData.assets.find(a => a.id === assetId)
      if (assetInfo && assetInfo.ticker) {
        assetTicker = assetInfo.ticker
      }
    }
    
    let priceHistory = cachedHistory
    
    // Если история не передана, но есть в глобальном кэше, используем её
    if (!priceHistory && priceHistoryCache.value && priceHistoryCache.value.length > 0) {
      priceHistory = priceHistoryCache.value
    }
    
    // Загружаем историю цен только если она не передана в кэше и нет в глобальном кэше
    // Это fallback для обратной совместимости (не должно вызываться при использовании переключателя)
    if (!priceHistory) {
      // Получаем историю цен актива
      // Используем дату на день позже, чтобы включить саму дату операции
      const targetDateObj = new Date(targetDate)
      targetDateObj.setHours(23, 59, 59, 999) // Конец дня, чтобы включить саму дату
      const endDateStr = targetDateObj.toISOString().slice(0, 10) // YYYY-MM-DD
      
      const priceHistoryResponse = await assetsService.getAssetPriceHistory(
        assetId,
        null, // start_date - не ограничиваем
        endDateStr, // end_date - до даты операции включительно
        1000 // Увеличиваем лимит, чтобы получить больше записей
      )
      
      if (priceHistoryResponse.success && priceHistoryResponse.prices) {
        priceHistory = priceHistoryResponse.prices
      }
    }
    
    if (priceHistory && priceHistory.length > 0) {
      // Нормализуем целевую дату для сравнения
      const targetDateNormalized = new Date(targetDate)
      targetDateNormalized.setHours(0, 0, 0, 0)
      
      // Сортируем по дате (от новых к старым)
      const sortedPrices = [...priceHistory].sort((a, b) => {
        const dateA = new Date(a.trade_date)
        const dateB = new Date(b.trade_date)
        return dateB - dateA
      })
      
      // Ищем цену на точную дату или ближайшую предыдущую
      for (const priceRecord of sortedPrices) {
        const priceDate = new Date(priceRecord.trade_date)
        priceDate.setHours(0, 0, 0, 0)
        
        // Проверяем, что дата цены <= целевой даты
        if (priceDate <= targetDateNormalized) {
          const price = parseFloat(priceRecord.price)
          if (price && price > 0) {
            return price
          }
        }
      }
    }
    
    // Если цена не найдена в истории, пытаемся получить из referenceData
    if (refData) {
      // Сначала пробуем получить из assets
      if (refData.assets && assetInfo) {
        if (assetInfo.last_price) {
          const price = parseFloat(assetInfo.last_price)
          if (price && price > 0) {
            return price
          }
        }
      }
      
      // Если это валюта/криптовалюта, пробуем получить курс из currencies
      if (assetTicker && refData.currencies) {
        const currency = refData.currencies.find(c => c.ticker === assetTicker)
        if (currency) {
          // Для валют/криптовалют используем rate_to_rub как цену в рублях
          if (currency.rate_to_rub) {
            const rate = parseFloat(currency.rate_to_rub)
            if (rate && rate > 0) {
              return rate
            }
          }
          // Если rate_to_rub нет, пробуем получить из asset_last_currency_prices через assets
          if (refData.assets) {
            const currencyAsset = refData.assets.find(a => a.ticker === assetTicker)
            if (currencyAsset && currencyAsset.last_price) {
              const price = parseFloat(currencyAsset.last_price)
              if (price && price > 0) {
                return price
              }
            }
          }
        }
      }
    }
    
    // Если ничего не найдено, возвращаем null (не используем fallback 1)
    // Это позволит системе показать ошибку или запросить цену вручную
    return null
  } catch (error) {
    console.error('Ошибка при получении цены актива:', error)
    return null
  }
}

// Функция для загрузки истории цен актива (вызывается один раз при включении переключателя)
async function loadPriceHistory() {
  if (!props.asset?.asset_id) {
    return false
  }
  
  // Если история уже загружена для этого актива, не загружаем повторно
  if (priceHistoryCache.value && priceHistoryCache.value.length > 0) {
    return true
  }
  
  // Если уже идет загрузка истории, не запускаем повторную загрузку
  if (isLoadingHistory.value) {
    // Ждем завершения текущей загрузки
    while (isLoadingHistory.value) {
      await new Promise(resolve => setTimeout(resolve, 50))
    }
    // После завершения проверяем, загрузилась ли история
    return priceHistoryCache.value && priceHistoryCache.value.length > 0
  }
  
  try {
    isLoadingHistory.value = true
    loadingPrice.value = true
    
    // Загружаем полную историю цен актива (без ограничения по дате)
    const priceHistoryResponse = await assetsService.getAssetPriceHistory(
      props.asset.asset_id,
      null, // start_date - не ограничиваем
      null, // end_date - не ограничиваем, загружаем всю историю
      10000 // Большой лимит для получения всей истории
    )
    
    if (priceHistoryResponse.success && priceHistoryResponse.prices) {
      // Сохраняем историю в кэш
      priceHistoryCache.value = priceHistoryResponse.prices
      return true
    }
    
    return false
  } catch (e) {
    console.error('Ошибка при загрузке истории цен:', e)
    return false
  } finally {
    isLoadingHistory.value = false
    loadingPrice.value = false
  }
}

// Функция для получения рыночной цены на дату транзакции и заполнения поля цены
async function loadMarketPrice(silent = false) {
  if (!props.asset?.asset_id) {
    if (!silent) {
      error.value = 'Не выбран актив'
    }
    return false
  }
  
  if (!date.value) {
    if (!silent) {
      error.value = 'Выберите дату транзакции'
    }
    return false
  }
  
  if (!silent) {
    loadingPrice.value = true
    error.value = ''
  }
  
  try {
    // Используем кэшированную историю цен, если она есть
    const marketPrice = await getAssetPriceOnDate(
      props.asset.asset_id, 
      date.value, 
      priceHistoryCache.value
    )
    
    if (marketPrice && marketPrice > 0) {
      price.value = marketPrice
      return true
    } else {
      if (!silent) {
        error.value = `Не удалось получить рыночную цену актива на дату ${date.value}. Пожалуйста, введите цену вручную.`
      }
      return false
    }
  } catch (e) {
    if (!silent) {
      error.value = 'Ошибка при получении рыночной цены: ' + (e.message || 'Неизвестная ошибка')
    }
    return false
  } finally {
    if (!silent) {
      loadingPrice.value = false
    }
  }
}

// Автоматическая загрузка истории цен и рыночной цены при включении переключателя
watch(useMarketPrice, async (newValue, oldValue) => {
  // Загружаем историю цен и цену только при включении переключателя (переходе с false на true)
  if (newValue && !oldValue && isTransaction.value && props.asset?.asset_id) {
    // Загружаем историю цен один раз при включении переключателя (если еще не загружена)
    const historyLoaded = await loadPriceHistory()
    
    // Если история загружена или уже была в кэше, загружаем цену на текущую дату
    if (historyLoaded && date.value) {
      await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
    }
  }
  // При выключении переключателя НЕ очищаем кэш - сохраняем для повторного использования
})

// Автоматическое обновление цены при изменении даты, если переключатель включен
watch(date, async (newDate, oldDate) => {
  // Обновляем цену только если переключатель включен и дата действительно изменилась
  if (useMarketPrice.value && isTransaction.value && props.asset?.asset_id && newDate && newDate !== oldDate) {
    // Используем кэшированную историю цен для быстрого поиска цены
    await loadMarketPrice(true) // silent = true, чтобы не показывать ошибки при автоматической загрузке
  }
}, { immediate: false })

// Очистка кэша истории цен при изменении актива
watch(() => props.asset?.asset_id, (newAssetId, oldAssetId) => {
  if (newAssetId !== oldAssetId) {
    priceHistoryCache.value = null
    // Если переключатель включен и актив изменился, загружаем новую историю
    if (useMarketPrice.value && isTransaction.value && newAssetId && date.value) {
      loadPriceHistory().then(() => {
        loadMarketPrice(true)
      })
    }
  }
})

// Функция для создания транзакции покупки
async function createBuyTransaction(assetId, portfolioAssetId, quantity, transactionDate) {
  // Получаем рыночную цену актива на дату операции
  let price = await getAssetPriceOnDate(assetId, transactionDate)
  
  // Если цена не найдена, пытаемся получить из referenceData по тикеру
  if (!price || price <= 0) {
    const refData = dashboardStore.referenceData
    if (refData?.assets) {
      const asset = refData.assets.find(a => a.id === assetId)
      if (asset?.ticker && refData.currencies) {
        const currency = refData.currencies.find(c => c.ticker === asset.ticker)
        if (currency?.rate_to_rub) {
          price = parseFloat(currency.rate_to_rub)
        }
      }
      // Если не нашли в currencies, пробуем last_price из assets
      if ((!price || price <= 0) && asset?.last_price) {
        price = parseFloat(asset.last_price)
      }
    }
  }
  
  // Если цена все еще не найдена, используем fallback на 1 с предупреждением
  // Это позволит создать транзакцию, но пользователь должен будет исправить цену вручную
  if (!price || price <= 0) {
    console.warn(`Не удалось получить цену актива ${assetId} на дату ${transactionDate}. Используется fallback цена = 1. Пожалуйста, обновите цену вручную.`)
    price = 1
  }
  
  // Используем store для создания транзакции, чтобы автоматически обновился dashboard
  await transactionsStore.addTransaction({
    asset_id: assetId,
    portfolio_asset_id: portfolioAssetId,
    transaction_type: 1, // buy
    quantity,
    price,
    transaction_date: transactionDate
  })
}

// Функция для генерации дат для повторяющихся операций
function generateRecurringDates(startDate, endDate, dayOfMonth) {
  const dates = []
  const start = new Date(startDate)
  const end = new Date(endDate)
  
  let current = new Date(start.getFullYear(), start.getMonth(), dayOfMonth)
  
  // Если первая дата раньше startDate, переходим к следующему месяцу
  if (current < start) {
    current.setMonth(current.getMonth() + 1)
  }
  
  while (current <= end) {
    // Проверяем, что день месяца валиден для этого месяца
    const lastDay = new Date(current.getFullYear(), current.getMonth() + 1, 0).getDate()
    const validDay = Math.min(dayOfMonth, lastDay)
    current.setDate(validDay)
    
    if (current >= start && current <= end) {
      dates.push(new Date(current))
    }
    
    // Переходим к следующему месяцу
    current.setMonth(current.getMonth() + 1)
    current.setDate(dayOfMonth)
  }
  
  return dates
}

const handleSubmit = async () => {
  error.value = ''
  
  // Валидация для транзакций (Buy/Sell) - не поддерживаются в режиме повторения
  if (isTransaction.value && mode.value === 'recurring') {
    error.value = 'Повторяющиеся операции не поддерживаются для транзакций (Покупка/Продажа)'
    return
  }
  
  if (isTransaction.value) {
    if (!quantity.value || quantity.value <= 0) {
      error.value = 'Введите количество'
      return
    }
    if (!price.value || price.value <= 0) {
      error.value = 'Введите цену'
      return
    }
  }
  
  // Валидация для остальных операций
  if (requiresAmount.value) {
    if (!amount.value || amount.value === 0) {
      error.value = 'Введите сумму'
      return
    }
  }
  
  // Валидация для выплат (Dividend/Coupon)
  if (isPayout.value && !props.asset?.asset_id) {
    error.value = 'Не указан актив'
    return
  }
  
  // Валидация для повторяющихся операций
  if (mode.value === 'recurring') {
    if (!startDate.value) {
      error.value = 'Выберите начальную дату'
      return
    }
    if (!endDate.value) {
      error.value = 'Выберите конечную дату'
      return
    }
    if (new Date(endDate.value) < new Date(startDate.value)) {
      error.value = 'Конечная дата должна быть позже начальной'
      return
    }
    if (!dayOfMonth.value || dayOfMonth.value < 1 || dayOfMonth.value > 31) {
      error.value = 'День месяца должен быть от 1 до 31'
      return
    }
  }

  saving.value = true

  try {
    // Для Buy/Sell используем старый метод через onSubmit
    if (isTransaction.value) {
      await props.onSubmit({
        asset_id: props.asset.asset_id,
        portfolio_asset_id: props.asset.portfolio_asset_id,
        transaction_type: operationType.value,
        quantity: quantity.value,
        price: price.value,
        transaction_date: date.value,
        date: date.value
      })
    } else if (mode.value === 'recurring') {
      // Для повторяющихся операций используем batch API
      // Получаем portfolio_id из актива или портфелей
      const portfolioId = props.asset?.portfolio_id || getPortfolioId()
      
      const batchData = {
        portfolio_id: portfolioId,
        operation_type: operationType.value,
        amount: amount.value,
        start_date: startDate.value,
        end_date: endDate.value,
        day_of_month: dayOfMonth.value,
        currency_id: useCustomCurrency.value ? currencyId.value : 47
      }
      
      // Добавляем asset_id если есть
      if (props.asset?.asset_id) {
        batchData.asset_id = props.asset.asset_id
      }
      
      // Для Buy/Sell также нужны portfolio_asset_id
      if (props.asset?.portfolio_asset_id) {
        batchData.portfolio_asset_id = props.asset.portfolio_asset_id
      }
      
      // Для выплат добавляем доходность (если указана)
      if (isPayout.value && dividendYield.value) {
        batchData.dividend_yield = dividendYield.value
      }
      
      // Создаем операции дивидендов по первоначальному активу (props.asset.asset_id) через batch API
      // Это важно: операции дивидендов всегда привязаны к активу, по которому выплачиваются дивиденды
      await transactionsStore.addOperationsBatch(batchData)
      
      // Если нужно создать актив из валюты для повторяющихся операций
      // Это создает транзакции покупки актива валюты (например, BTC) для каждой даты выплаты дивидендов
      if (isPayout.value && createAssetFromCurrency.value && useCustomCurrency.value && selectedCurrency.value.ticker !== 'RUB') {
        // findOrCreateCurrencyAsset проверяет, есть ли актив уже в портфеле
        // Если есть - возвращает существующий portfolio_asset_id (без создания дубликата)
        // Если нет - создает новый portfolio_asset с quantity=0
        const currencyAsset = await findOrCreateCurrencyAsset(selectedCurrency.value.ticker, currencyId.value)
        const dates = generateRecurringDates(startDate.value, endDate.value, dayOfMonth.value)
        
        // Создаем транзакции покупки для каждой даты
        // Используем Promise.all для параллельного выполнения, но с ограничением
        // Если актив уже был в портфеле, транзакции просто добавятся к существующему активу
        const batchSize = 5 // Обрабатываем по 5 транзакций за раз
        for (let i = 0; i < dates.length; i += batchSize) {
          const batch = dates.slice(i, i + batchSize)
          await Promise.all(batch.map(async (opDate) => {
            const dateStr = opDate.toISOString().slice(0, 10)
            await createBuyTransaction(
              currencyAsset.asset_id,
              currencyAsset.portfolio_asset_id,
              Math.abs(amount.value),
              dateStr
            )
          }))
        }
        
        // Обновляем dashboard после создания всех транзакций
        await dashboardStore.reloadDashboard()
      }
    } else {
      // Для остальных операций используем обычный API
      // Получаем portfolio_id из актива или портфелей
      const portfolioId = props.asset?.portfolio_id || getPortfolioId()
      
      const operationData = {
        portfolio_id: portfolioId,
        operation_type: operationType.value,
        amount: amount.value,
        operation_date: date.value,
        currency_id: useCustomCurrency.value ? currencyId.value : 47 // Выбранная валюта или RUB по умолчанию
      }
      
      // Добавляем asset_id если есть
      if (props.asset?.asset_id) {
        operationData.asset_id = props.asset.asset_id
      }
      
      // Для Buy/Sell также нужны portfolio_asset_id
      if (props.asset?.portfolio_asset_id) {
        operationData.portfolio_asset_id = props.asset.portfolio_asset_id
      }
      
      // Для выплат добавляем доходность (если указана)
      if (isPayout.value && dividendYield.value) {
        operationData.dividend_yield = dividendYield.value
      }
      
      // Создаем операцию дивидендов по первоначальному активу (props.asset.asset_id)
      // Это важно: операция дивидендов всегда привязана к активу, по которому выплачиваются дивиденды
      await transactionsStore.addOperation(operationData)
      
      // Если нужно создать актив из валюты для одиночной операции
      // Это создает транзакцию покупки актива валюты (например, BTC), в которую выплачены дивиденды
      if (isPayout.value && createAssetFromCurrency.value && useCustomCurrency.value && selectedCurrency.value.ticker !== 'RUB') {
        // findOrCreateCurrencyAsset проверяет, есть ли актив уже в портфеле
        // Если есть - возвращает существующий portfolio_asset_id (без создания дубликата)
        // Если нет - создает новый portfolio_asset с quantity=0
        const currencyAsset = await findOrCreateCurrencyAsset(selectedCurrency.value.ticker, currencyId.value)
        
        // Создаем транзакцию покупки актива валюты
        // Цена получается автоматически из истории цен на дату операции
        // Количество = сумма дивидендов в валюте выплаты
        // createBuyTransaction использует store, который автоматически обновит dashboard
        // Если актив уже был в портфеле, транзакция просто добавится к существующему активу
        await createBuyTransaction(
          currencyAsset.asset_id,
          currencyAsset.portfolio_asset_id,
          Math.abs(amount.value),
          date.value
        )
      }
    }
    
    emit('close')
  } catch (e) {
    error.value = 'Ошибка при добавлении операции: ' + (e.response?.data?.detail || e.message || 'Неизвестная ошибка')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="modal-backdrop" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Добавление операции</h2>
        <button class="close-btn" @click="emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <form @submit.prevent="handleSubmit" class="form-content">
        <div class="form-section">
          <div class="asset-info" v-if="asset">
            <span class="asset-icon">📈</span>
            <div>
              <strong>{{ asset.name }}</strong>
              <span class="ticker">({{ asset.ticker }})</span>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <span class="label-icon">🔄</span>
            Тип операции
          </label>
          <CustomSelect
            v-model="operationType"
            :options="operationTypes"
            placeholder="Выберите тип"
            :show-empty-option="false"
            option-label="label"
            option-value="value"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <!-- Переключатель режима (только для не-транзакций) -->
        <div v-if="!isTransaction" class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <span class="label-icon">⚙️</span>
            Режим добавления
          </label>
          <div class="mode-switch">
            <button
              type="button"
              :class="['mode-btn', { active: mode === 'single' }]"
              @click="mode = 'single'"
            >
              Одна операция
            </button>
            <button
              type="button"
              :class="['mode-btn', { active: mode === 'recurring' }]"
              @click="mode = 'recurring'"
            >
              Повторяющиеся операции
            </button>
          </div>
        </div>

        <!-- Поля для транзакций (Buy/Sell) -->
        <div v-if="isTransaction" class="form-section">
          <div class="section-divider"></div>
          
          <!-- Переключатель использования рыночной цены -->
          <div class="toggle-wrapper">
            <ToggleSwitch v-model="useMarketPrice" />
            <span class="toggle-label-text">
              Использовать рыночную цену на дату транзакции
            </span>
          </div>
          
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">🔢</span>
                Количество
              </label>
              <input type="number" v-model.number="quantity" min="0" step="0.000001" class="form-input" required />
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">💰</span>
                Цена (₽)
                <span v-if="loadingPrice" style="margin-left: 8px; color: #3b82f6;">⏳ Загрузка...</span>
              </label>
              <input 
                type="number" 
                v-model.number="price" 
                min="0" 
                step="0.000001" 
                class="form-input" 
                required 
                :disabled="useMarketPrice && loadingPrice"
              />
              <small class="form-hint" style="margin-top: 4px;" v-if="useMarketPrice">
                Цена автоматически обновляется при изменении даты
              </small>
              <small class="form-hint" style="margin-top: 4px;">
                Можно вводить до 6 знаков после запятой
              </small>
            </div>
          </div>
          <div class="form-field" style="margin-top: 12px;">
            <label class="form-label">
              <span class="label-icon">📅</span>
              Дата транзакции
            </label>
            <input type="date" v-model="date" required class="form-input" />
          </div>
        </div>

        <!-- Поля для остальных операций -->
        <div v-if="requiresAmount" class="form-section">
          <div class="section-divider"></div>
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">💰</span>
              {{ amountLabel }}
            </label>
            <input 
              type="number" 
              v-model.number="amount" 
              :step="isPayout ? 0.000001 : 0.01" 
              class="form-input" 
              required
              :placeholder="isExpense ? 'Отрицательное значение' : 'Положительное значение'"
            />
            <small class="form-hint" v-if="isExpense">
              Введите отрицательное значение (например, -50)
            </small>
            <small class="form-hint" v-else-if="isPayout">
              Можно вводить до 6 знаков после запятой (например, 0.001234)
            </small>
          </div>
        </div>

        <!-- Дополнительные поля для выплат (Dividend/Coupon) -->
        <div v-if="isPayout" class="form-section">
          <div class="section-divider"></div>
          
          <!-- Выбор валюты выплаты -->
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">💱</span>
              Валюта выплаты
            </label>
            <div class="toggle-wrapper">
              <ToggleSwitch 
                v-model="useCustomCurrency" 
              />
              <span class="toggle-label-text">{{ useCustomCurrency ? 'Выплата в другой валюте' : 'Выплата в рублях (RUB)' }}</span>
            </div>
            <CustomSelect
              v-if="useCustomCurrency"
              v-model="currencyId"
              :options="currencies"
              placeholder="Выберите валюту"
              :show-empty-option="false"
              option-label="label"
              option-value="value"
              :min-width="'100%'"
              :flex="'none'"
              class="currency-select"
            />
          </div>
          
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">📊</span>
                Доходность (%)
                <span class="label-hint" v-if="dividendYield && assetPrice && assetQuantity">(рассчитано автоматически)</span>
              </label>
              <input 
                type="number" 
                v-model.number="dividendYield" 
                min="0" 
                step="0.0001" 
                class="form-input" 
                :readonly="!!(assetPrice && assetQuantity && amount)"
                :placeholder="assetPrice && assetQuantity ? 'Рассчитывается автоматически' : 'Введите вручную (опционально)'"
              />
            </div>
          </div>
          
          <!-- Переключатель для автоматического создания актива из валюты -->
          <div v-if="useCustomCurrency && selectedCurrency.ticker !== 'RUB'" class="form-field">
            <div class="toggle-wrapper">
              <ToggleSwitch 
                v-model="createAssetFromCurrency" 
              />
              <span class="toggle-label-text">
                Создать актив из валюты ({{ selectedCurrency.ticker }})
              </span>
            </div>
            <small class="form-hint">
              Будет создан актив с валютой {{ selectedCurrency.ticker }} и транзакция покупки на сумму дивидендов
            </small>
          </div>
        </div>

        <!-- Дата операции (для одиночной операции) -->
        <div v-if="mode === 'single' && !isTransaction" class="form-section">
          <div class="section-divider"></div>
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">📅</span>
              Дата операции
            </label>
            <input type="date" v-model="date" required class="form-input" />
          </div>
        </div>

        <!-- Поля для повторяющихся операций -->
        <template v-if="mode === 'recurring' && !isTransaction">
          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-row">
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📅</span>
                  Начальная дата
                </label>
                <input type="date" v-model="startDate" required class="form-input" />
              </div>
              <div class="form-field">
                <label class="form-label">
                  <span class="label-icon">📅</span>
                  Конечная дата
                </label>
                <input type="date" v-model="endDate" required class="form-input" />
              </div>
            </div>
          </div>

          <div class="form-section">
            <div class="section-divider"></div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">📆</span>
                День месяца
              </label>
              <input 
                type="number" 
                v-model.number="dayOfMonth" 
                min="1" 
                max="31" 
                class="form-input" 
                required
              />
              <small class="form-hint">
                Операция будет создаваться каждый месяц в указанный день (1-31)
              </small>
            </div>
            <div v-if="operationsCount > 0" class="info-box">
              <span class="info-icon">ℹ️</span>
              <span>Будет создано <strong>{{ operationsCount }}</strong> операций</span>
            </div>
          </div>
        </template>

        <div v-if="error" class="error">{{ error }}</div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="emit('close')" :disabled="saving">Отмена</Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            {{ saving ? 'Сохранение...' : (mode === 'recurring' ? 'Создать повторяющиеся операции' : 'Добавить') }}
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
  padding: 16px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes slideUp {
  from {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.01em;
}

.close-btn {
  background: #f3f4f6;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
  transform: scale(1.05);
}

.close-btn:active {
  transform: scale(0.95);
}

.close-btn svg {
  width: 16px;
  height: 16px;
}

.form-content {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.form-content::-webkit-scrollbar {
  width: 6px;
}

.form-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.form-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.form-section {
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 16px 0;
}

.asset-info {
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.asset-icon {
  font-size: 18px;
  opacity: 0.8;
}

.asset-info strong {
  color: #111827;
  font-weight: 600;
}

.ticker {
  color: #6b7280;
  margin-left: 6px;
  font-size: 13px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  font-size: 14px;
  opacity: 0.8;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}

.label-hint {
  font-weight: 400;
  color: #6b7280;
  font-size: 11px;
  margin-left: 4px;
}

.toggle-wrapper {
  margin-bottom: 12px;
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-label-text {
  font-size: 13px;
  color: #374151;
  font-weight: 500;
}

.currency-select {
  margin-top: 8px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.error {
  padding: 10px 14px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 12px;
}

.mode-switch {
  display: flex;
  gap: 8px;
  background: #f3f4f6;
  padding: 4px;
  border-radius: 12px;
}

.mode-btn {
  flex: 1;
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #6b7280;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.mode-btn:hover {
  background: rgba(255, 255, 255, 0.5);
  color: #374151;
}

.mode-btn.active {
  background: white;
  color: #111827;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.info-box {
  margin-top: 12px;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13px;
  color: #1e40af;
}

.info-icon {
  font-size: 16px;
}

.info-box strong {
  color: #1e3a8a;
  font-weight: 600;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

.market-price-btn {
  white-space: nowrap;
  padding: 8px 16px;
  min-width: auto;
  border: 1.5px solid #3b82f6;
  border-radius: 10px;
  background: #eff6ff;
  color: #3b82f6;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: inherit;
}

.market-price-btn:hover:not(:disabled) {
  background: #dbeafe;
  border-color: #2563eb;
  color: #2563eb;
}

.market-price-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  border-color: #d1d5db;
  background: #f3f4f6;
  color: #9ca3af;
}

</style>
