import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/Home.vue'
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Dashboard from '../views/Dashboard.vue';
import Assets from '../views/Assets.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/dashboard', component: Dashboard },
  { path: '/assets', component: Assets },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
