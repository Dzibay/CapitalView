<script setup>
import { ref, computed, unref, onMounted, onBeforeUnmount } from "vue";

// ✅ сохраняем props в переменную
const props = defineProps({
  portfolios: Array,
  expandedPortfolios: Array,
  activePortfolioMenu: Number,
  updatingPortfolios: Object,
});

const emit = defineEmits([
  "togglePortfolio",
  "togglePortfolioMenu",
  "removeAsset",
  "clearPortfolio",
  "deletePortfolio",
  "selectAsset",
  "addTransaction", // Добавлено для проксирования
  "addPrice"        // Добавлено для проксирования
]);

const activeAssetMenu = ref(null);

// 📊 === Функция сортировки активов по стоимости ===
const sortAssets = (assets) => {
  if (!assets) return [];
  return [...assets].sort((a, b) => {
    const valA = (a.quantity * (a.last_price || 0) / (a.leverage || 1)) * (a.currency_rate_to_rub || 1);
    const valB = (b.quantity * (b.last_price || 0) / (b.leverage || 1)) * (b.currency_rate_to_rub || 1);
    return valB - valA; // по убыванию
  });
};

// 📦 === Рекурсивная сортировка портфелей по total_value ===
const sortPortfolios = (portfolios) => {
  if (!portfolios) return [];
  return [...portfolios]
    .map((p) => ({
      ...p,
      assets: sortAssets(p.assets),
      children: sortPortfolios(p.children || []),
    }))
    .sort((a, b) => (b.total_value || 0) - (a.total_value || 0));
};

// === Вычисляемая коллекция для рендера ===
const sortedPortfolios = computed(() => sortPortfolios(unref(props.portfolios)));

// ==== Остальная логика ====
const togglePortfolio = (id) => emit("togglePortfolio", id);
const togglePortfolioMenu = (id) => emit("togglePortfolioMenu", id);

const toggleAssetMenu = (id) => {
  activeAssetMenu.value = activeAssetMenu.value === id ? null : id;
};

const removeAsset = (id) => emit("removeAsset", id);
const clearPortfolio = (id) => emit("clearPortfolio", id);
const addTransaction = (asset) => emit("addTransaction", asset);
const addPrice = (asset) => emit('addPrice', asset)
const deletePortfolio = (id) => emit("deletePortfolio", id);

const handleClickOutside = (event) => {
  if (!event.target.closest(".menu-container")) {
    activeAssetMenu.value = null;
    emit("togglePortfolioMenu", null);
  }
};

onMounted(() => document.addEventListener("click", handleClickOutside));
onBeforeUnmount(() => document.removeEventListener("click", handleClickOutside));

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
  const avgDividends =
    validYears.reduce((sum, y) => sum + yearly[y], 0) / validYears.length;
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

        <div class="menu-container">
          <button class="menu-btn icon-btn" @click.stop="togglePortfolioMenu(portfolio.id)">⋯</button>
          <transition name="scale">
            <div v-if="activePortfolioMenu === portfolio.id" class="menu-dropdown">
              <button @click="clearPortfolio(portfolio.id)" class="menu-item">
                <span class="icon">🧹</span> Очистить
              </button>
              <button @click="deletePortfolio(portfolio.id)" class="menu-item danger">
                <span class="icon">🗑️</span> Удалить
              </button>
            </div>
          </transition>
        </div>
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
                    <span v-if="asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига')">
                      {{ asset.properties?.coupon_percent ? asset.properties.coupon_percent.toFixed(2) + '%' : '–' }}
                    </span>
                    <span v-else>
                      {{ getDividendYieldCurrentYear(asset).toFixed(2) }}%
                    </span>
                  </td>
                  <td class="col-right num-font">
                    <span v-if="asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига')"> – </span>
                    <span v-else> {{ getDividendYield5Y(asset).toFixed(2) }}% </span>
                  </td>
                  <td class="col-right num-font" :class="asset.last_price - asset.average_price >= 0 ? 'text-green' : 'text-red'">
                     {{ ((asset.last_price - asset.average_price) / asset.average_price * 100).toFixed(2) }}%
                  </td>
                  <td class="col-right num-font" :class="asset.daily_change >= 0 ? 'text-green' : 'text-red'">
                    {{ (asset.daily_change / asset.last_price * 100).toFixed(2) }}%
                  </td>
                  <td class="col-actions center">
                    <div class="menu-container">
                      <button class="menu-btn icon-btn" @click.stop="toggleAssetMenu(asset.portfolio_asset_id)">⋮</button>
                      <transition name="scale">
                        <div v-if="activeAssetMenu === asset.portfolio_asset_id" class="menu-dropdown asset-menu">
                          <button @click="addTransaction(asset)" class="menu-item">💰 Добавить транзакцию</button>
                          <button @click="addPrice(asset)" class="menu-item">📈 Изменить цену</button>
                          <div class="divider"></div>
                          <button class="menu-item danger" @click="removeAsset(asset.portfolio_asset_id)">🗑️ Удалить</button>
                        </div>
                      </transition>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="portfolio.children && portfolio.children.length" class="child-portfolios">
            <PortfolioTree
              :portfolios="portfolio.children"
              :expandedPortfolios="expandedPortfolios"
              :activePortfolioMenu="activePortfolioMenu"
              :updatingPortfolios="updatingPortfolios"
              @togglePortfolio="togglePortfolio"
              @togglePortfolioMenu="togglePortfolioMenu"
              @removeAsset="removeAsset"
              @deletePortfolio="deletePortfolio"
              @clearPortfolio="clearPortfolio"
              @addTransaction="addTransaction"
              @addPrice="addPrice"
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
.col-right { text-align: right; }
.col-actions { width: 40px; }
.col-name { min-width: 150px; text-align: left;}

/* Font Tweaks */
.num-font {
  font-family: 'SF Mono', 'Roboto Mono', Menlo, monospace;
  font-size: 12px;
  letter-spacing: -0.3px;
}
.bold { font-weight: 600; }

/* Colors */
.text-green { color: #10b981; }
.text-red { color: #ef4444; }

/* Asset Cell Specifics */
.cell-name {
  /* Keep name cell clean */
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

/* --- Menu & Dropdowns --- */
.menu-container {
  position: relative;
}
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

.menu-dropdown {
  position: absolute;
  right: 0;
  top: 100%;
  margin-top: 4px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 15px rgba(0,0,0,0.1);
  min-width: 180px;
  z-index: 50;
  padding: 4px;
  display: flex;
  flex-direction: column;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  padding: 8px 12px;
  font-size: 13px;
  color: #334155;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.1s;
}
.menu-item:hover {
  background: #f1f5f9;
}
.menu-item.danger {
  color: #ef4444;
}
.menu-item.danger:hover {
  background: #fef2f2;
}

.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 4px 0;
}

/* --- Child Portfolios Wrapper --- */
.child-portfolios {
  padding: 0 16px 16px 24px; /* Indent child portfolios */
  background: #ffffff;
}

/* --- Transitions --- */
.slide-fade-enter-active, .slide-fade-leave-active {
  transition: all 0.3s ease-out;
}
.slide-fade-enter-from, .slide-fade-leave-to {
  transform: translateY(-10px);
  opacity: 0;
}

.scale-enter-active, .scale-leave-active {
  transition: all 0.1s ease;
}
.scale-enter-from, .scale-leave-to {
  transform: scale(0.95);
  opacity: 0;
}
</style>