<script setup>
import { ref, onMounted } from 'vue';
import { mockData } from '../data/mockData.js';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

// Компоненты макета
import AppSidebar from '../components/AppSidebar.vue';
import AppHeader from '../components/AppHeader.vue';

// Компоненты виджетов
import TotalCapitalWidget from '../components/widgets/TotalCapitalWidget.vue';
import AssetAllocationWidget from '../components/widgets/AssetAllocationWidget.vue';
import GoalProgressWidget from '../components/widgets/GoalProgressWidget.vue';
import PortfolioChartWidget from '../components/widgets/PortfolioChartWidget.vue';
import RecentTransactionsWidget from '../components/widgets/RecentTransactionsWidget.vue';
import TopAssetsWidget from '../components/widgets/TopAssetsWidget.vue';

const user = ref(null);
const router = useRouter();

onMounted(async () => {
  try {
    const u = await authService.checkToken();
    console.log("Профиль")
    console.log(u)
    if (!u) {
      router.push('/login');
    } else {
      user.value = u;
    }
  } catch {
    authService.logout();
    router.push('/login');
  }
});


const isSidebarVisible = ref(true);

function toggleSidebar() {
  isSidebarVisible.value = !isSidebarVisible.value;
}
</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :class="{ 'sidebar-hidden': !isSidebarVisible }" />

    <main class="main-content" :class="{ 'full-width': !isSidebarVisible }">
      <AppHeader :user="mockData.user" @toggle-sidebar="toggleSidebar" />
      
      <div class="widgets-grid">
        <TotalCapitalWidget 
          :total-amount="mockData.totalCapital.totalAmount" 
          :monthly-change="mockData.totalCapital.monthlyChange" 
        />
        <RecentTransactionsWidget :transactions="mockData.recentTransactions" />
        <TopAssetsWidget :assets="mockData.topAssets" />
        <AssetAllocationWidget :assets-data="mockData.assetAllocation" />
        
        
        <PortfolioChartWidget :chart-data="mockData.portfolioChart" />
        <GoalProgressWidget :goal-data="mockData.investmentGoal" />
        
        
        
      </div>
    </main>
  </div>
</template>

<style scoped>
.dashboard-layout {
  display: flex;
  background-color: #f9fafb;
}

.sidebar-hidden {
  transform: translateX(-100%);
}

.main-content {
  flex-grow: 1;
  margin-left: 260px; /* Ширина сайдбара */
  transition: margin-left 0.3s ease-in-out;
  min-height: 100vh;
}

.main-content.full-width {
  margin-left: 0;
}

.widgets-grid {
  padding: 2rem;
  display: grid;
  gap: 1.5rem;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
}
</style>