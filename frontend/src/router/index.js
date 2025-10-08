import { createRouter, createWebHistory } from 'vue-router';
import DashboardLayout from '../layouts/DashboardLayout.vue'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Dashboard from '../views/Dashboard.vue';
import Assets from '../views/Assets.vue'

const routes = [
  { path: '/', component: Home },
  {
    path: '/',
    component: DashboardLayout,
    children: [
      { path: '/dashboard', component: Dashboard },
      { path: '/assets', component: Assets },
    ]
  },
  // Страницы без layout
  { path: '/login', component: Login },
  { path: '/register', component: Register },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
