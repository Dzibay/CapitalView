import { createRouter, createWebHistory } from 'vue-router';
import DashboardLayout from '../layouts/DashboardLayout.vue'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue';
import Dashboard from '../views/Dashboard.vue';
import Assets from '../views/Assets.vue'
import Transactions from '../views/Transactions.vue';
import Analitics from '../views/Analitics.vue';
import Dividends from '../views/Dividends.vue';

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  {
    path: '/',
    component: DashboardLayout,
    children: [
      { path: '/dashboard', component: Dashboard },
      { path: '/analitics', component: Analitics },
      { path: '/assets', component: Assets },
      { path: '/transactions', component: Transactions},
      { path: '/dividends', component: Dividends}
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
