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
const selectAsset = (asset) => emit("selectAsset", asset);
const deletePortfolio = (id) => emit("deletePortfolio", id);

const handleClickOutside = (event) => {
  if (!event.target.closest(".menu")) {
    activeAssetMenu.value = null;
    emit("togglePortfolioMenu", null);
  }
};

onMounted(() => document.addEventListener("click", handleClickOutside));
onBeforeUnmount(() => document.removeEventListener("click", handleClickOutside));
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
                <th>Тикер</th>
                <th>Количество</th>
                <th>Средняя цена</th>
                <th>Текущая цена</th>
                <th>Стоимость (₽)</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="asset in portfolio.assets" :key="asset.portfolio_asset_id">
                <td>
                    {{ asset.name }}
                    <span v-if="asset.leverage && asset.leverage > 1" class="leveraged">💹×{{ asset.leverage }}</span>
                </td>
                <td>{{ asset.ticker }}</td>
                <td class="right">{{ asset.quantity }}</td>
                <td class="right">{{ asset.average_price.toFixed(2) }}</td>
                <td class="right">{{ asset.last_price || '-' }}</td>
                <td class="right">
                    {{
                        Math.max(
                        0,
                        (asset.quantity * asset.last_price / asset.leverage) * asset.currency_rate_to_rub
                        ).toFixed(2)
                    }}
                </td>

                <td class="center">
                  <div class="menu">
                    <button class="menu-btn" @click.stop="toggleAssetMenu(asset.portfolio_asset_id)">⋯</button>
                    <div v-if="activeAssetMenu === asset.portfolio_asset_id" class="menu-dropdown">
                      <button @click="selectAsset(asset)">💰 Добавить транзакцию</button>
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
              @selectAsset="selectAsset"
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
  background: #fafafa;
}
.asset-table td.right {
  text-align: right;
}
.asset-table td.center {
  text-align: center;
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
</style>
