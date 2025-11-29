import { createRouter, createWebHistory } from 'vue-router';
import DashboardLayout from '../layouts/DashboardLayout.vue'
import Home from '../views/Home.vue'
import Login from '../views/Login.vue';
import Dashboard from '../views/Dashboard.vue';
import Assets from '../views/Assets.vue'
import Transactions from '../views/Transactions.vue';
import Analitics from '../views/Analitics.vue';
import Dividends from '../views/Dividends.vue';
import { authService } from '../services/authService';

const routes = [
  { path: '/', component: Home },
  { 
    path: '/login', 
    component: Login,
    meta: { requiresGuest: true } // Только для неавторизованных
  },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true }, // Требует авторизации
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

// Навигационный guard для защиты маршрутов
router.beforeEach(async (to, from, next) => {
  // Пропускаем проверку для маршрута логина при переходе с него (избегаем бесконечного цикла)
  if (to.path === '/login' && from.path === '/login') {
    next();
    return;
  }

  const token = localStorage.getItem('access_token');
  
  // Если маршрут требует авторизации
  if (to.meta.requiresAuth) {
    if (!token) {
      // Нет токена - перенаправляем на логин
      next({ path: '/login', query: { redirect: to.fullPath } });
      return;
    }
    
    // Проверяем валидность токена
    try {
      const user = await authService.checkToken();
      if (!user || !user.user) {
        // Токен недействителен
        authService.logout();
        next({ path: '/login', query: { redirect: to.fullPath } });
        return;
      }
      // Токен валиден, разрешаем доступ
      next();
    } catch (error) {
      // Ошибка при проверке токена (кроме сетевых ошибок)
      if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNREFUSED') {
        console.error('Token check failed:', error);
        authService.logout();
        next({ path: '/login', query: { redirect: to.fullPath } });
      } else {
        // При сетевой ошибке все равно разрешаем доступ (backend может быть временно недоступен)
        next();
      }
    }
  } 
  // Если маршрут только для гостей (например, /login)
  else if (to.meta.requiresGuest) {
    if (token) {
      // Есть токен - проверяем его валидность (но не блокируем доступ при ошибках)
      try {
        const user = await authService.checkToken();
        if (user && user.user) {
          // Токен валиден - перенаправляем на dashboard
          const redirectPath = from.query.redirect || '/dashboard';
          next(redirectPath);
          return;
        }
      } catch (error) {
        // Токен недействителен или ошибка сети - очищаем и разрешаем доступ к логину
        if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNREFUSED') {
          authService.logout();
        }
        next();
        return;
      }
    }
    // Нет токена или токен недействителен - разрешаем доступ к логину
    next();
  } 
  // Обычные маршруты без ограничений
  else {
    next();
  }
});

export default router;
