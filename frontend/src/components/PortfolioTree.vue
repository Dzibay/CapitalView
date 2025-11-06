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
  if (!event.target.closest(".menu")) {
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

  // Сумма всех дивидендов с датой фиксации за текущий год
  const totalDividends = asset.dividends
    .filter(d => new Date(d.record_date).getFullYear() === currentYear)
    .reduce((sum, d) => sum + (parseFloat(d.value) || 0), 0);

  return (totalDividends / asset.last_price) * 100;
};

// 📊 Средняя дивидендная доходность за последние 5 лет (%)
const getDividendYield5Y = (asset) => {
  if (!asset.dividends || !asset.last_price) return 0;

  // Группируем по году
  const yearly = {};
  for (const d of asset.dividends) {
    if (!d.record_date || !d.value) continue;
    const year = new Date(d.record_date).getFullYear();
    yearly[year] = (yearly[year] || 0) + parseFloat(d.value);
  }

  // Определяем последние 5 календарных лет
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
  <div class="portfolio-tree">
    <div
      v-for="portfolio in sortedPortfolios"
      :key="portfolio.id"
      class="portfolio"
    >
      <!-- Заголовок портфеля -->
      <div class="portfolio-header">
        <div class="portfolio-title" @click="togglePortfolio(portfolio.id)">
          <span>{{ expandedPortfolios.includes(portfolio.id) ? '▼' : '▶' }}</span>
          <span class="name">{{ portfolio.name }}</span>
          <span v-if="portfolio.total_value > 0"> (стоимость: {{ portfolio.total_value.toFixed(2) }} ₽)</span>
          <span v-if="updatingPortfolios && unref(updatingPortfolios).has(portfolio.id)" class="spinner">⏳</span>

        </div>

        <div class="menu">
          <button class="menu-btn" @click.stop="togglePortfolioMenu(portfolio.id)">⋯</button>
          <div v-if="activePortfolioMenu === portfolio.id" class="menu-dropdown">
            <button @click="clearPortfolio(portfolio.id)">🧹 Очистить</button>
            <button @click="deletePortfolio(portfolio.id)" class="danger">🗑️ Удалить</button>
          </div>
        </div>
      </div>

      <!-- Активы -->
      <transition name="fade">
        <div v-if="expandedPortfolios.includes(portfolio.id)" class="portfolio-body">
          <p v-if="!portfolio.assets || portfolio.assets.length === 0" class="empty">
            Активов нет
          </p>

          <table v-else class="asset-table">
            <thead>
              <tr>
                <th>Название</th>
                <th>Количество</th>
                <th>Средняя цена</th>
                <th>Текущая цена</th>
                <th>Стоимость (₽)</th>
                <th>Див. доходность (год)</th>
                <th>Див. доходность (5 лет)</th>
                <th>За все время</th>
                <th>За день</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="asset in portfolio.assets" :key="asset.portfolio_asset_id">
                <td>
                    <span>{{ asset.name }}</span><br>
                    <span class="asset_ticker">{{ asset.ticker }}</span>
                    <span v-if="asset.leverage && asset.leverage > 1" class="leveraged">💹×{{ asset.leverage }}</span>
                </td>
                <td>{{ asset.quantity }}</td>
                <td>{{ asset.average_price.toFixed(2) }}</td>
                <td>{{ asset.last_price || '-' }}</td>
                <td>{{ Math.max(0, (asset.quantity * asset.last_price / asset.leverage) * asset.currency_rate_to_rub).toFixed(2) }}</td>
                <td>
                  <!-- 💰 Див. доходность (год) -->
                  <span v-if="asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига')">
                    {{ asset.properties?.coupon_percent ? asset.properties.coupon_percent.toFixed(2) + '%' : '–' }}
                  </span>
                  <span v-else>
                    {{ getDividendYieldCurrentYear(asset).toFixed(2) }}%
                  </span>
                </td>

                <td>
                  <!-- 📆 Див. доходность (5 лет) -->
                  <span v-if="asset.type.toLowerCase().includes('bond') || asset.type.toLowerCase().includes('облига')">
                    –
                  </span>
                  <span v-else>
                    {{ getDividendYield5Y(asset).toFixed(2) }}%
                  </span>
                </td>
                
                <td :class="{ 
                  'positive': asset.last_price - asset.average_price > 0, 
                  'negative': asset.last_price - asset.average_price < 0 
                  }">
                  {{ ((asset.last_price - asset.average_price) / asset.average_price * 100).toFixed(2) }}%
                </td>
                <td :class="{ 
                  'positive': asset.daily_change > 0, 
                  'negative': asset.daily_change < 0 
                  }">
                  {{ (asset.daily_change / asset.last_price * 100).toFixed(2) }}%
                </td>
                <td></td>

                <td class="center">
                  <div class="menu">
                    <button class="menu-btn" @click.stop="toggleAssetMenu(asset.portfolio_asset_id)">⋯</button>
                    <div v-if="activeAssetMenu === asset.portfolio_asset_id" class="menu-dropdown">
                      <button @click="addTransaction(asset)">💰 Добавить транзакцию</button>
                      <button @click="addPrice(asset)">💰 Добавить изменение цены</button>
                      <button class="danger" @click="removeAsset(asset.portfolio_asset_id)">🗑️ Удалить актив</button>
                    </div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>

          <!-- Вложенные портфели -->
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
.portfolio {
  border: 1px solid #ddd;
  border-radius: 6px;
  margin-bottom: 12px;
  background: #fff;
}
.portfolio-header {
  display: flex;
  justify-content: space-between;
  padding: 10px 14px;
  background: #f7f7f7;
  align-items: center;
  cursor: pointer;
}
.portfolio-title {
  display: flex;
  gap: 6px;
  font-weight: bold;
}
.portfolio-body {
  padding: 10px 14px;
}
.asset-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.asset-table th,
.asset-table td {
  border-bottom: 1px solid #ddd;
  padding: 8px;
}
.asset-table th {
  text-align: left;
  background: #fafafa;
}
.asset-table td.right {
  text-align: right;
}
.asset-table td.center {
  text-align: center;
}
.asset-table td.positive {
  color: var(--positiveColor);
}
.asset-table td.negative {
  color: var(--negativeColor);
}
.menu {
  position: relative;
  display: inline-block;
}
.menu-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
}
.menu-dropdown {
  position: absolute;
  right: 0;
  top: 24px;
  background: white;
  border: 1px solid #ccc;
  border-radius: 6px;
  box-shadow: 0 2px 5px rgba(0,0,0,0.1);
  min-width: 160px;
  z-index: 10;
}
.menu-dropdown button {
  display: block;
  width: 100%;
  text-align: left;
  border: none;
  background: none;
  padding: 8px 12px;
  cursor: pointer;
}
.menu-dropdown button:hover {
  background: #f2f2f2;
}
.menu-dropdown .danger {
  color: #c00;
}
.child-portfolios {
  margin-left: 20px;
  border-left: 2px solid #ddd;
  padding-left: 10px;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.leveraged {
  color: #e67e22;
  font-weight: bold;
  margin-left: 4px;
}

.asset_ticker {
  color: grey;
  font-weight: 300;
}
</style>
