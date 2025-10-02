import { createRouter, createWebHistory } from 'vue-router';
import Login from '../views/Login.vue';
import Register from '../views/Register.vue';
import Profile from '../views/Profile.vue';
import Assets from '../views/Assets.vue'

const routes = [
  { path: '/', redirect: '/profile' },
  { path: '/login', component: Login },
  { path: '/register', component: Register },
  { path: '/profile', component: Profile },
  { path: '/assets', component: Assets },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

export default router;
