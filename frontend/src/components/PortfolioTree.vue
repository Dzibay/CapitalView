<script setup>
import { computed, unref, ref, onMounted, onUnmounted } from "vue";
import { useRouter } from 'vue-router';
import { useContextMenu } from '../composables/useContextMenu';
import { getCurrencySymbol } from '../utils/currencySymbols';
import { effectiveUnitPriceInCurrency } from '../utils/effectiveAssetPrice';

const router = useRouter();

// На планшетах и мобильных показываем карточки вместо таблицы (без скролла)
const isMobileView = ref(typeof window !== 'undefined' && window.innerWidth <= 1024);
function updateMobileView() {
  if (typeof window !== 'undefined') {
    isMobileView.value = window.innerWidth <= 1024;
  }
}
onMounted(() => {
  if (typeof window !== 'undefined') {
    window.addEventListener('resize', updateMobileView);
  }
});
onUnmounted(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', updateMobileView);
  }
});

// ✅ сохраняем props в переменную
const props = defineProps({
  portfolios: Array,
  expandedPortfolios: Array,
  updatingPortfolios: Object,
  showSoldAssets: {
    type: Boolean,
    default: false
  },
  /** Только просмотр: без меню действий и переходов в карточку актива. */
  readOnly: {
    type: Boolean,
    default: false
  },
});

const emit = defineEmits([
  "togglePortfolio",
  "removeAsset",
  "clearPortfolio",
  "deletePortfolio",
  "addTransaction",
  "addPrice",
  "moveAsset"
]);

const { openMenu } = useContextMenu();

// 📊 === Функция сортировки активов по стоимости ===
// Вынесена вычисление стоимости для мемоизации
const calculateAssetValue = (asset) => {
  const unit = effectiveUnitPriceInCurrency(asset)
  return (asset.quantity * unit / (asset.leverage || 1)) * (asset.currency_rate_to_rub || 1)
}

const sortAssets = (assets) => {
  if (!assets || assets.length === 0) return [];
  // Создаем массив с предвычисленными значениями для оптимизации сортировки
  const assetsWithValue = assets.map(asset => ({
    asset,
    value: calculateAssetValue(asset)
  }));
  assetsWithValue.sort((a, b) => b.value - a.value); // по убыванию
  return assetsWithValue.map(item => item.asset);
};

// Фильтрация активов по количеству
const filterAssets = (assets) => {
  if (!assets || assets.length === 0) return [];
  if (props.showSoldAssets) {
    // Показываем все активы, включая проданные
    return assets;
  }
  // Фильтруем только активы с quantity > 0
  return assets.filter(asset => (asset.quantity || 0) > 0);
};

// 📦 === Рекурсивная сортировка портфелей по total_value ===
// Оптимизировано: минимизированы копии объектов
const sortPortfolios = (portfolios) => {
  if (!portfolios || portfolios.length === 0) return [];
  // Сортируем активы только если они есть
  const processedPortfolios = portfolios.map((p) => {
    const processed = { ...p };
    if (p.assets && p.assets.length > 0) {
      // Сначала фильтруем активы, затем сортируем
      const filteredAssets = filterAssets(p.assets);
      processed.assets = sortAssets(filteredAssets);
    }
    if (p.children && p.children.length > 0) {
      processed.children = sortPortfolios(p.children);
    }
    return processed;
  });
  processedPortfolios.sort((a, b) => (b.total_value || 0) - (a.total_value || 0));
  return processedPortfolios;
};

// === Вычисляемая коллекция для рендера ===
const sortedPortfolios = computed(() => sortPortfolios(unref(props.portfolios)));

// ==== Остальная логика ====
const togglePortfolio = (id) => emit("togglePortfolio", id);

// 📈 Дивидендная доходность TTM (~12 мес. по record_date, только type=dividend) — с сервера (dividend_yield_year_pct) или fallback
const isDividendPayoutRow = (d) => {
  const t = String(d?.type ?? '').trim().toLowerCase()
  if (!t) return true
  return t === 'dividend'
}

const getDividendYieldCurrentYear = (asset) => {
  if (asset.dividend_yield_year_pct != null && asset.dividend_yield_year_pct !== '') {
    return Number(asset.dividend_yield_year_pct)
  }
  const payouts = asset.payouts || asset.dividends || []
  if (!payouts.length || !asset.last_price) return 0
  const todayYmd = new Date()
  const todayDay = new Date(todayYmd.getFullYear(), todayYmd.getMonth(), todayYmd.getDate())
  const cutoffDay = new Date(todayDay)
  cutoffDay.setFullYear(cutoffDay.getFullYear() - 1)
  const totalDividends = payouts
    .filter((d) => {
      if (!isDividendPayoutRow(d) || !d.record_date) return false
      const rd = new Date(d.record_date)
      if (Number.isNaN(rd.getTime())) return false
      const rdDay = new Date(rd.getFullYear(), rd.getMonth(), rd.getDate())
      return rdDay > cutoffDay && rdDay <= todayDay
    })
    .reduce((sum, d) => sum + (parseFloat(d.value) || 0), 0)
  return (totalDividends / asset.last_price) * 100
}

// 📊 Средняя дивидендная доходность за окно 5 лет (%) — с сервера или как раньше
const getDividendYield5Y = (asset) => {
  if (asset.dividend_yield_5y_pct != null && asset.dividend_yield_5y_pct !== '') {
    return Number(asset.dividend_yield_5y_pct)
  }
  const payouts = asset.payouts || asset.dividends || []
  if (!payouts.length || !asset.last_price) return 0
  const yearly = {}
  for (const d of payouts) {
    if (!isDividendPayoutRow(d) || !d.record_date || !d.value) continue
    const year = new Date(d.record_date).getFullYear()
    yearly[year] = (yearly[year] || 0) + parseFloat(d.value)
  }
  const currentYear = new Date().getFullYear()
  const yearsToInclude = Array.from({ length: 5 }, (_, i) => currentYear - i).reverse()
  const validYears = yearsToInclude.filter(y => yearly[y])
  if (validYears.length === 0) return 0
  const avgDividends = validYears.reduce((sum, y) => sum + yearly[y], 0) / validYears.length
  return (avgDividends / asset.last_price) * 100
}

function goToAsset(asset) {
  if (props.readOnly) return
  router.push(`/assets/${asset.portfolio_asset_id}`)
}
</script>

<template>
  <div class="portfolio-list">
    <div
      v-for="portfolio in sortedPortfolios"
      :key="portfolio.id"
      class="portfolio-card"
      :class="{ 'is-child': portfolio.parent_portfolio_id }"
    >
      <div class="portfolio-header" @click="togglePortfolio(portfolio.id)">
        <div class="portfolio-info">
          <div class="toggle-icon" :class="{ rotated: expandedPortfolios.includes(portfolio.id) }">
            ▶
          </div>
          <div class="title-wrapper">
            <span class="portfolio-name">{{ portfolio.name }}</span>
            <span v-if="portfolio.total_value > 0" class="portfolio-value">
              {{ portfolio.total_value.toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }} ₽
            </span>
          </div>
          <span v-if="updatingPortfolios && unref(updatingPortfolios).has(portfolio.id)" class="spinner">⏳</span>
        </div>
        <button
          v-if="!readOnly"
          type="button"
          class="menu-btn icon-btn"
          @click.stop="openMenu($event, 'portfolio', portfolio)"
        >
          ⋯
        </button>
      </div>

      <transition name="slide-fade">
        <div v-if="expandedPortfolios.includes(portfolio.id)" class="portfolio-body">
          <div v-if="!portfolio.assets?.length && !portfolio.children?.length" class="empty-state">
            В этом портфеле пока нет активов
          </div>
          <!-- Десктоп: таблица -->
          <div v-if="portfolio.assets && portfolio.assets.length > 0 && !isMobileView" class="table-responsive">
            <table class="asset-table">
              <thead>
                <tr>
                  <th class="col-name">Актив</th>
                  <th class="col-right">Кол-во</th>
                  <th class="col-right">Ср. цена</th>
                  <th class="col-right">Цена</th>
                  <th class="col-right">Стоимость</th>
                  <th class="col-right">Див (12 мес.)</th>
                  <th class="col-right">Див (5л)</th>
                  <th class="col-right">P&L (Всё)</th>
                  <th class="col-right">P&L (День)</th>
                  <th v-if="!readOnly" class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr 
                  v-for="asset in portfolio.assets" 
                  :key="asset.portfolio_asset_id"
                  :class="{ 'sold-asset': (asset.quantity || 0) === 0 }"
                >
                  <td
                    class="cell-name"
                    :class="{ clickable: !readOnly }"
                    @click="goToAsset(asset)"
                  >
                    <div class="asset-main">
                      <span class="asset-name">
                        {{ asset.name }}
                        <span v-if="(asset.quantity || 0) === 0" class="sold-badge">(Продан)</span>
                      </span>
                      <div class="asset-meta">
                        <span class="asset-ticker">{{ asset.ticker }}</span>
                        <span v-if="asset.leverage && asset.leverage > 1" class="badge-leverage">×{{ asset.leverage }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="col-right">{{ asset.quantity }}</td>
                  <td class="col-right num-font">{{ asset.average_price.toFixed(2) }} {{ getCurrencySymbol(asset.currency_ticker) }}</td>
                  <td class="col-right num-font">{{ effectiveUnitPriceInCurrency(asset) ? effectiveUnitPriceInCurrency(asset) + ' ' + getCurrencySymbol(asset.currency_ticker) : '-' }}</td>
                  <td class="col-right num-font bold">
                    {{ Math.max(0, calculateAssetValue(asset)).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }} ₽
                  </td>
                  <td class="col-right num-font">
                    <span v-if="asset.type && (asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига'))">
                      {{ asset.properties?.coupon_percent ? asset.properties.coupon_percent.toFixed(2) + '%' : '–' }}
                    </span>
                    <span v-else>
                      {{ getDividendYieldCurrentYear(asset).toFixed(2) }}%
                    </span>
                  </td>
                  <td class="col-right num-font">
                    <span v-if="asset.type && (asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига'))">
                      –
                    </span>
                    <span v-else>
                      {{ getDividendYield5Y(asset).toFixed(2) }}%
                    </span>
                  </td>
                  <td class="col-right num-font" :class="effectiveUnitPriceInCurrency(asset) - asset.average_price >= 0 ? 'text-green' : 'text-red'">
                    {{ asset.average_price ? (((effectiveUnitPriceInCurrency(asset) - asset.average_price) / asset.average_price) * 100).toFixed(2) : '0.00' }}%
                  </td>
                  <td class="col-right num-font" :class="asset.daily_change >= 0 ? 'text-green' : 'text-red'">
                    {{ asset.last_price ? (asset.daily_change / asset.last_price * 100).toFixed(2) : '0.00' }}%
                  </td>
                  <td v-if="!readOnly" class="col-actions center">
                    <button
                      type="button"
                      class="menu-btn icon-btn"
                      @click.stop="openMenu($event, 'asset', asset)"
                    >
                      ⋮
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- Мобильная/планшет: карточки без скролла -->
          <div v-if="portfolio.assets && portfolio.assets.length > 0 && isMobileView" class="asset-cards">
            <div
              v-for="asset in portfolio.assets"
              :key="asset.portfolio_asset_id"
              class="asset-card"
              :class="{ 'sold-asset': (asset.quantity || 0) === 0 }"
            >
              <div
                class="asset-card-header"
                :class="{ clickable: !readOnly }"
                @click="goToAsset(asset)"
              >
                <div class="asset-card-title">
                  <span class="asset-name">{{ asset.name }}</span>
                  <span v-if="(asset.quantity || 0) === 0" class="sold-badge">(Продан)</span>
                </div>
                <div class="asset-card-meta">
                  <span class="asset-ticker">{{ asset.ticker }}</span>
                  <span v-if="asset.leverage && asset.leverage > 1" class="badge-leverage">×{{ asset.leverage }}</span>
                </div>
              </div>
              <div class="asset-card-body">
                <div class="asset-card-row">
                  <span class="asset-card-label">Кол-во</span>
                  <span class="asset-card-value">{{ asset.quantity }}</span>
                </div>
                <div class="asset-card-row">
                  <span class="asset-card-label">Цена</span>
                  <span class="asset-card-value num-font">{{ effectiveUnitPriceInCurrency(asset) ? effectiveUnitPriceInCurrency(asset) + ' ' + getCurrencySymbol(asset.currency_ticker) : '–' }}</span>
                </div>
                <div class="asset-card-row">
                  <span class="asset-card-label">Стоимость</span>
                  <span class="asset-card-value num-font bold">{{ Math.max(0, calculateAssetValue(asset)).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }} ₽</span>
                </div>
                <div class="asset-card-row">
                  <span class="asset-card-label">P&L</span>
                  <span class="asset-card-value num-font" :class="(effectiveUnitPriceInCurrency(asset) - asset.average_price) >= 0 ? 'text-green' : 'text-red'">{{ asset.average_price ? (((effectiveUnitPriceInCurrency(asset) - asset.average_price) / asset.average_price) * 100).toFixed(2) : '0.00' }}%</span>
                </div>
              </div>
              <div v-if="!readOnly" class="asset-card-actions">
                <button type="button" class="menu-btn icon-btn" @click.stop="openMenu($event, 'asset', asset)" aria-label="Меню">⋮</button>
              </div>
            </div>
          </div>
          <!-- Баланс портфеля - отображается внизу, под активами -->
          <div v-if="portfolio.balance !== undefined && portfolio.balance !== null && portfolio.balance !== 0" class="portfolio-balance-section">
            <div class="balance-row">
              <span class="balance-label">Свободный баланс:</span>
              <span class="balance-amount">
                {{ portfolio.balance.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }} ₽
              </span>
            </div>
          </div>
          <div v-if="portfolio.children && portfolio.children.length" class="child-portfolios">
            <PortfolioTree
              :portfolios="portfolio.children"
              :expandedPortfolios="expandedPortfolios"
              :updatingPortfolios="updatingPortfolios"
              :showSoldAssets="showSoldAssets"
              :read-only="readOnly"
              @togglePortfolio="$emit('togglePortfolio', $event)"
              @removeAsset="$emit('removeAsset', $event)"
              @deletePortfolio="$emit('deletePortfolio', $event)"
              @clearPortfolio="$emit('clearPortfolio', $event)"
              @addTransaction="$emit('addTransaction', $event)"
              @addPrice="$emit('addPrice', $event)"
              @moveAsset="$emit('moveAsset', $event)"
            />
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
/* --- Общие переменные и разметка --- */
.portfolio-list {
  display: flex;
  flex-direction: column;
  min-width: 0;
  max-width: 100%;
  width: 100%;
}

.portfolio-card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid #eef0f2;
  overflow: hidden;
  transition: box-shadow 0.2s;
  min-width: 0;
  max-width: 100%;
}
.portfolio-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

/* Дочерние портфели с меньшей тенью и отступом */
.portfolio-card.is-child {
  margin-top: 16px;
  box-shadow: none;
  border: 1px solid #e2e8f0;
  background: #fcfcfc;
}

/* --- Шапка --- */
.portfolio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #fff;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
  min-width: 0;
}
.portfolio-card.is-child > .portfolio-header {
  background: #fcfcfc;
}
.portfolio-header:hover {
  background: #f8fafc;
}

.portfolio-info {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.toggle-icon {
  font-size: 10px;
  color: #94a3b8;
  transition: transform 0.2s ease;
}
.toggle-icon.rotated {
  transform: rotate(90deg);
}

.title-wrapper {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
  overflow: hidden;
}

.portfolio-name {
  font-weight: 600;
  font-size: 16px;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.portfolio-values {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-end;
}

.portfolio-value {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.spinner {
  font-size: 14px;
}

/* --- Тело --- */
.portfolio-body {
  border-top: 1px solid #eef0f2;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

/* --- Обёртка дочерних портфелей (базовые стили, переопределяются в @media) --- */
.child-portfolios {
  padding: 0 16px 16px 16px;
  background: #ffffff;
}

/* --- Баланс портфеля --- */
.portfolio-balance-section {
  padding: 12px 20px;
  border-top: 1px solid #eef0f2;
  background: #fafbfc;
  font-size: 13px;
}

.balance-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.balance-label {
  color: #64748b;
  font-weight: 500;
}

.balance-amount {
  color: #1e293b;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace;
}

.empty-state {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-style: italic;
  font-size: 14px;
}

/* --- Стили таблицы --- */
.table-responsive {
  width: 100%;
  max-width: 100%; /* Ограничиваем контейнер */
  overflow-x: auto; /* Включаем прокрутку */
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch; /* Плавный скролл на iOS */
  position: relative;
}

/* Планшет: компактная таблица (если показывается) и меньшие отступы иерархии */
@media (max-width: 1200px) {
  .portfolio-header {
    padding: 12px 14px;
  }
  .portfolio-card.is-child {
    margin-top: 10px;
  }
  .child-portfolios {
    padding: 0 10px 10px 10px;
  }
  .portfolio-balance-section {
    padding: 10px 14px;
  }
  .asset-table {
    font-size: 12px;
    min-width: 620px;
  }
  .asset-table th,
  .asset-table td {
    padding: 8px 10px;
  }
  .col-name {
    min-width: 120px;
  }
  .num-font {
    font-size: 11px;
  }
  .asset-name {
    font-size: 13px;
  }
  .asset-ticker {
    font-size: 10px;
  }
}

/* Мобильные: компактные отступы для вложенных портфелей */
@media (max-width: 768px) {
  .portfolio-header {
    padding: 10px 12px;
  }
  .portfolio-card.is-child > .portfolio-header {
    padding: 8px 10px;
  }
  .portfolio-card.is-child {
    margin-top: 8px;
  }
  .child-portfolios {
    padding: 0 4px 8px 4px;
  }
  .portfolio-balance-section {
    padding: 8px 12px;
    font-size: 12px;
  }
  .portfolio-card.is-child .portfolio-balance-section {
    padding: 6px 10px;
  }
  .empty-state {
    padding: 16px;
    font-size: 13px;
  }
  .asset-cards {
    padding: 10px;
    gap: 8px;
  }
  .portfolio-card.is-child .asset-cards {
    padding: 6px 8px;
  }
  .asset-card {
    padding: 10px;
  }
  .portfolio-card.is-child .asset-card {
    padding: 8px;
  }
}

@media (max-width: 480px) {
  .portfolio-header {
    padding: 8px 10px;
  }
  .portfolio-card.is-child > .portfolio-header {
    padding: 6px 8px;
  }
  .portfolio-card.is-child {
    margin-top: 6px;
  }
  .child-portfolios {
    padding: 0 2px 6px 2px;
  }
  .portfolio-name {
    font-size: 14px;
  }
  .portfolio-value {
    font-size: 12px;
  }
  .asset-cards {
    padding: 8px;
    gap: 6px;
  }
  .portfolio-card.is-child .asset-cards {
    padding: 4px 6px;
  }
  .asset-card {
    padding: 8px;
  }
  .portfolio-card.is-child .asset-card {
    padding: 6px;
  }
  .asset-card-body {
    font-size: 11px;
  }
}

.asset-table {
  width: 100%;
  min-width: 700px;
  border-collapse: collapse;
  font-size: 13px;
  color: #334155;
  table-layout: auto;
}

.asset-table th {
  font-weight: 600;
  color: #64748b;
  padding: 12px 16px;
  background: #f8fafc;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}

.asset-table td {
  padding: 12px 16px;
  border-bottom: 1px solid #f1f5f9;
  vertical-align: middle;
}

.asset-table tr:last-child td {
  border-bottom: none;
}

.asset-table tr:hover td {
  background: #fbfbfc;
}

.asset-table tr.sold-asset {
  opacity: 0.6;
}

.asset-table tr.sold-asset:hover {
  opacity: 0.8;
}

.sold-badge {
  font-size: 11px;
  color: #ef4444;
  font-weight: 500;
  margin-left: 6px;
}

/* Выравнивание колонок */
.col-right {
  text-align: right;
}
.col-actions {
  width: 40px;
}
.col-name {
  min-width: 150px;
  text-align: left;
}
.center {
  text-align: center;
}

/* Настройки шрифта */
.num-font {
  font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace;
  font-size: 12px;
  letter-spacing: -0.3px;
}
.bold {
  font-weight: 600;
}

/* Цвета */
.text-green {
  color: #10b981;
}
.text-red {
  color: #ef4444;
}

/* Стили ячеек актива */
.cell-name.clickable {
  cursor: pointer;
}
.cell-name.clickable:hover {
  background: #f1f5f9;
}
.asset-card-header.clickable {
  cursor: pointer;
}
.asset-card-header.clickable:hover {
  background: #f1f5f9;
}
.asset-main {
  display: flex;
  flex-direction: column;
}
.asset-name {
  font-weight: 500;
  color: #0f172a;
  margin-bottom: 2px;
}
.asset-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}
.asset-ticker {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 4px;
}
.badge-leverage {
  font-size: 10px;
  background: #fff7ed;
  color: #ea580c;
  padding: 1px 4px;
  border-radius: 4px;
  border: 1px solid #ffedd5;
  font-weight: bold;
}

/* --- Кнопка меню --- */
.menu-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 6px 8px;
  border-radius: 8px;
  line-height: 1;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
  position: relative;
}

.menu-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 8px;
  background: transparent;
  transition: background 0.2s;
}

.menu-btn:hover {
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
  color: #3b82f6;
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(59,130,246,0.15);
}

.menu-btn:active {
  transform: translateY(0);
  box-shadow: 0 1px 3px rgba(59,130,246,0.1);
}

.icon-btn {
  font-size: 18px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

/* --- Мобильные карточки активов (без скролла) --- */
.asset-cards {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  box-sizing: border-box;
}

.asset-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 12px;
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 8px 12px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}

.asset-card.sold-asset {
  opacity: 0.7;
}

.asset-card-header {
  grid-column: 1;
  cursor: pointer;
  min-width: 0;
}

.asset-card-title {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
}

.asset-card-title .asset-name {
  font-weight: 600;
  font-size: 14px;
  color: #0f172a;
}

.asset-card-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
}

.asset-card-body {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 6px 16px;
  font-size: 12px;
  min-width: 0;
}

.asset-card-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.asset-card-label {
  color: #64748b;
  flex-shrink: 0;
}

.asset-card-value {
  color: #334155;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}

.asset-card-actions {
  grid-column: 2;
  grid-row: 1;
  align-self: start;
  justify-self: end;
}

/* --- Переходы --- */
.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: all 0.3s ease-out;
}
.slide-fade-enter-from,
.slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}
</style>
