<script setup>
import { computed, unref } from "vue";
import { useContextMenu } from '../composables/useContextMenu';

// ✅ сохраняем props в переменную
const props = defineProps({
  portfolios: Array,
  expandedPortfolios: Array,
  updatingPortfolios: Object,
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
  return (asset.quantity * (asset.last_price || 0) / (asset.leverage || 1)) * (asset.currency_rate_to_rub || 1);
};

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

// 📦 === Рекурсивная сортировка портфелей по total_value ===
// Оптимизировано: минимизированы копии объектов
const sortPortfolios = (portfolios) => {
  if (!portfolios || portfolios.length === 0) return [];
  // Сортируем активы только если они есть
  const processedPortfolios = portfolios.map((p) => {
    const processed = { ...p };
    if (p.assets && p.assets.length > 0) {
      processed.assets = sortAssets(p.assets);
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

// 📈 Дивидендная доходность за текущий календарный год (%)
const getDividendYieldCurrentYear = (asset) => {
  if (!asset.dividends || !asset.last_price) return 0;
  const currentYear = new Date().getFullYear();
  const totalDividends = asset.dividends
    .filter(d => new Date(d.record_date).getFullYear() === currentYear)
    .reduce((sum, d) => sum + (parseFloat(d.value) || 0), 0);
  return (totalDividends / asset.last_price) * 100;
};

// 📊 Средняя дивидендная доходность за последние 5 лет (%)
const getDividendYield5Y = (asset) => {
  if (!asset.dividends || !asset.last_price) return 0;
  const yearly = {};
  for (const d of asset.dividends) {
    if (!d.record_date || !d.value) continue;
    const year = new Date(d.record_date).getFullYear();
    yearly[year] = (yearly[year] || 0) + parseFloat(d.value);
  }
  const currentYear = new Date().getFullYear();
  const yearsToInclude = Array.from({ length: 5 }, (_, i) => currentYear - i).reverse();
  const validYears = yearsToInclude.filter(y => yearly[y]);
  if (validYears.length === 0) return 0;
  const avgDividends = validYears.reduce((sum, y) => sum + yearly[y], 0) / validYears.length;
  return (avgDividends / asset.last_price) * 100;
};
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
          class="menu-btn icon-btn"
          @click.stop="openMenu($event, 'portfolio', portfolio.id)"
        >
          ⋯
        </button>
      </div>

      <transition name="slide-fade">
        <div v-if="expandedPortfolios.includes(portfolio.id)" class="portfolio-body">
          <div v-if="!portfolio.assets?.length && !portfolio.children?.length" class="empty-state">
            В этом портфеле пока нет активов
          </div>
          <div v-if="portfolio.assets && portfolio.assets.length > 0" class="table-responsive">
            <table class="asset-table">
              <thead>
                <tr>
                  <th class="col-name">Актив</th>
                  <th class="col-right">Кол-во</th>
                  <th class="col-right">Ср. цена</th>
                  <th class="col-right">Цена</th>
                  <th class="col-right">Стоимость</th>
                  <th class="col-right">Див (год)</th>
                  <th class="col-right">Див (5л)</th>
                  <th class="col-right">P&L (Всё)</th>
                  <th class="col-right">P&L (День)</th>
                  <th class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="asset in portfolio.assets" :key="asset.portfolio_asset_id">
                  <td class="cell-name">
                    <div class="asset-main">
                      <span class="asset-name">{{ asset.name }}</span>
                      <div class="asset-meta">
                        <span class="asset-ticker">{{ asset.ticker }}</span>
                        <span v-if="asset.leverage && asset.leverage > 1" class="badge-leverage">×{{ asset.leverage }}</span>
                      </div>
                    </div>
                  </td>
                  <td class="col-right">{{ asset.quantity }}</td>
                  <td class="col-right num-font">{{ asset.average_price.toFixed(2) }}</td>
                  <td class="col-right num-font">{{ asset.last_price || '-' }}</td>
                  <td class="col-right num-font bold">
                    {{ Math.max(0, (asset.quantity * asset.last_price / asset.leverage) * asset.currency_rate_to_rub).toLocaleString('ru-RU', { minimumFractionDigits: 0, maximumFractionDigits: 0 }) }} ₽
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
                  <td class="col-right num-font" :class="asset.last_price - asset.average_price >= 0 ? 'text-green' : 'text-red'">
                    {{ ((asset.last_price - asset.average_price) / asset.average_price * 100).toFixed(2) }}%
                  </td>
                  <td class="col-right num-font" :class="asset.daily_change >= 0 ? 'text-green' : 'text-red'">
                    {{ (asset.daily_change / asset.last_price * 100).toFixed(2) }}%
                  </td>
                  <td class="col-actions center">
                    <button
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
          <div v-if="portfolio.children && portfolio.children.length" class="child-portfolios">
            <PortfolioTree
              :portfolios="portfolio.children"
              :expandedPortfolios="expandedPortfolios"
              :updatingPortfolios="updatingPortfolios"
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
/* --- General Variables & Layout --- */
.portfolio-list {
  display: flex;
  flex-direction: column;
}

.portfolio-card {
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  border: 1px solid #eef0f2;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.portfolio-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

/* Child portfolios have less shadow and are indented */
.portfolio-card.is-child {
  margin-top: 16px;
  box-shadow: none;
  border: 1px solid #e2e8f0;
  background: #fcfcfc;
}

/* --- Header --- */
.portfolio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: #fff;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
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
}

.portfolio-name {
  font-weight: 600;
  font-size: 16px;
  color: #1e293b;
}

.portfolio-value {
  font-size: 14px;
  color: #64748b;
  font-weight: 500;
}

.spinner {
  font-size: 14px;
}

/* --- Body --- */
.portfolio-body {
  border-top: 1px solid #eef0f2;
}

.empty-state {
  padding: 24px;
  text-align: center;
  color: #94a3b8;
  font-style: italic;
  font-size: 14px;
}

/* --- Table Styles --- */
.table-responsive {
  overflow-x: auto;
}

.asset-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  color: #334155;
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

/* Column Alignments */
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

/* Font Tweaks */
.num-font {
  font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace;
  font-size: 12px;
  letter-spacing: -0.3px;
}
.bold {
  font-weight: 600;
}

/* Colors */
.text-green {
  color: #10b981;
}
.text-red {
  color: #ef4444;
}

/* Asset Cell Specifics */
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

/* --- Menu Button --- */
.menu-btn {
  background: transparent;
  border: none;
  font-size: 18px;
  color: #94a3b8;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  line-height: 1;
}
.menu-btn:hover {
  background: #f1f5f9;
  color: #475569;
}
.icon-btn {
  font-size: 18px;
}

/* --- Child Portfolios Wrapper --- */
.child-portfolios {
  padding: 0 16px 16px 24px; /* Indent child portfolios */
  background: #ffffff;
}

/* --- Transitions --- */
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
