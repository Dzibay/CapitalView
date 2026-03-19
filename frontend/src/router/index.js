import { createRouter, createWebHistory } from 'vue-router';
import { authService } from '../services/authService';
import { useAuthStore } from '../stores/auth.store';

// Lazy loading: главная и логин — eager (быстрая первая загрузка)
const Home = () => import('../views/Home.vue');
const Login = () => import('../views/Login.vue');

// Остальные маршруты — lazy (загружаются по требованию)
const LegalDocument = () => import('../views/LegalDocument.vue');
const AuthCallback = () => import('../views/AuthCallback.vue');
const DashboardLayout = () => import('../layouts/DashboardLayout.vue');
const Dashboard = () => import('../views/Dashboard.vue');
const Analitics = () => import('../views/Analitics.vue');
const Assets = () => import('../views/Assets.vue');
const AssetDetail = () => import('../views/AssetDetail.vue');
const Transactions = () => import('../views/Transactions.vue');
const Dividends = () => import('../views/Dividends.vue');
const Settings = () => import('../views/Settings.vue');
const ErrorStatus = () => import('../views/errors/ErrorStatus.vue');
const NotFound404 = () => import('../views/errors/NotFound404.vue');

const routes = [
  { path: '/', component: Home },
  { path: '/privacy', component: LegalDocument },
  { path: '/terms', component: LegalDocument },
  {
    path: '/login',
    component: Login,
    meta: { requiresGuest: true }
  },
  { path: '/auth/callback', component: AuthCallback },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true },
    children: [
      { path: '/dashboard', component: Dashboard },
      { path: '/analitics', component: Analitics },
      { path: '/assets', component: Assets },
      { path: '/assets/:id', component: AssetDetail, props: true },
      { path: '/transactions', component: Transactions },
      { path: '/dividends', component: Dividends },
      { path: '/settings', component: Settings }
    ]
  },
  // Ошибки
  { path: '/error/:code', component: ErrorStatus },
  // Catch-all: всё остальное считаем 404
  { path: '/:pathMatch(.*)*', component: NotFound404 }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    }
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  }
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
      // ОПТИМИЗИРОВАНО: используем authStore для проверки токена, чтобы обновить store
      const authStore = useAuthStore()
      const user = await authStore.checkToken()
      if (!user) {
        // Токен недействителен
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
      // Токен валиден, разрешаем доступ
      next()
    } catch (error) {
      // Ошибка при проверке токена (кроме сетевых ошибок)
      if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNREFUSED') {
        console.error('Token check failed:', error)
        const authStore = useAuthStore()
        authStore.logout()
        next({ path: '/login', query: { redirect: to.fullPath } })
      } else {
        // При сетевой ошибке все равно разрешаем доступ (backend может быть временно недоступен)
        next()
      }
    }
  } 
  // Если маршрут только для гостей (например, /login)
  else if (to.meta.requiresGuest) {
    if (token) {
      // Есть токен - проверяем его валидность (но не блокируем доступ при ошибках)
      try {
        // ОПТИМИЗИРОВАНО: используем authStore для проверки токена
        const authStore = useAuthStore()
        const user = await authStore.checkToken()
        if (user) {
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

// SPA-страницы: отправляем "виртуальный просмотр" при смене маршрута.
// Ожидаем, что в index.html уже подключена Яндекс.Метрика и глобально доступна функция `ym`.
// ID счётчика задавайте через Vite переменную окружения: `VITE_YM_COUNTER_ID`.
const YM_COUNTER_ID = import.meta.env.VITE_YM_COUNTER_ID

router.afterEach((to) => {
  if (!YM_COUNTER_ID) return
  if (typeof window === 'undefined') return
  if (typeof window.ym !== 'function') return

  const url = `${window.location.origin}${to.fullPath}`
  // SPA: отправляем "просмотр страницы" вручную при смене маршрута.
  // Важно: для ym(..., 'hit') url передаём отдельным аргументом.
  window.ym(YM_COUNTER_ID, 'hit', url, {
    title: document.title,
    referer: document.referrer
  })
})

export default router;
