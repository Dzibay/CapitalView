import { createRouter, createWebHistory } from 'vue-router';
import { LAST_APP_PATH_KEY } from '../constants/lastAppPath';
import { defaultAuthenticatedPath } from '../utils/defaultAppPath';

const LAST_APP_PATH_REGEXES = [
  /^\/dashboard$/,
  /^\/admin$/,
  /^\/analitics$/,
  /^\/transactions$/,
  /^\/dividends$/,
  /^\/settings$/,
  /^\/assets$/,
  /^\/assets\/[^/]+$/
]

function isAllowedLastAppPath(path) {
  if (!path || typeof path !== 'string' || !path.startsWith('/')) return false
  const normalized = path.split('?')[0].split('#')[0]
  return LAST_APP_PATH_REGEXES.some((re) => re.test(normalized))
}

function getSavedAppPathOrDefault() {
  if (typeof localStorage === 'undefined') return '/dashboard'
  const raw = localStorage.getItem(LAST_APP_PATH_KEY)
  if (!raw) return '/dashboard'
  const pathOnly = raw.split('?')[0].split('#')[0]
  return isAllowedLastAppPath(pathOnly) ? pathOnly : '/dashboard'
}

function persistLastAppPathIfNeeded(to) {
  if (typeof localStorage === 'undefined') return
  if (!to.matched.some((r) => r.meta?.requiresAuth)) return
  if (!isAllowedLastAppPath(to.path)) return
  localStorage.setItem(LAST_APP_PATH_KEY, to.path)
}

function beforeEnterHomeAuthed(to, from, next) {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem('access_token') : null
  if (!token) {
    next()
    return
  }
  next({ path: getSavedAppPathOrDefault(), replace: true })
}

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
const Admin = () => import('../views/Admin.vue');
const ErrorStatus = () => import('../views/errors/ErrorStatus.vue');
const NotFound404 = () => import('../views/errors/NotFound404.vue');

const routes = [
  {
    path: '/',
    component: Home,
    beforeEnter: beforeEnterHomeAuthed,
    meta: {
      title: 'CapitalView — учёт инвестиций, аналитика портфеля и дивидендный календарь',
      robots: 'index, follow'
    }
  },
  {
    path: '/privacy',
    component: LegalDocument,
    meta: { title: 'Политика конфиденциальности — CapitalView', robots: 'noindex, follow' }
  },
  {
    path: '/terms',
    component: LegalDocument,
    meta: { title: 'Условия использования — CapitalView', robots: 'noindex, follow' }
  },
  {
    path: '/login',
    component: Login,
    meta: {
      requiresGuest: true,
      title: 'Вход и регистрация — CapitalView',
      robots: 'noindex, follow'
    }
  },
  { path: '/auth/callback', component: AuthCallback, meta: { robots: 'noindex, follow' } },
  {
    path: '/',
    component: DashboardLayout,
    meta: { requiresAuth: true, robots: 'noindex, follow' },
    children: [
      { path: '/dashboard', component: Dashboard, meta: { title: 'Дашборд — CapitalView' } },
      {
        path: '/admin',
        component: Admin,
        meta: { title: 'Администрирование — CapitalView', requiresAdmin: true },
      },
      { path: '/analitics', component: Analitics, meta: { title: 'Аналитика портфеля — CapitalView' } },
      {
        path: '/assets',
        component: Assets,
        meta: { title: 'Активы — CapitalView', robots: 'noindex, follow' }
      },
      {
        path: '/assets/:id',
        component: AssetDetail,
        props: true,
        meta: { title: 'Актив — CapitalView', robots: 'noindex, follow' }
      },
      { path: '/transactions', component: Transactions, meta: { title: 'Сделки — CapitalView' } },
      { path: '/dividends', component: Dividends, meta: { title: 'Дивиденды и купоны — CapitalView' } },
      { path: '/settings', component: Settings, meta: { title: 'Настройки — CapitalView' } }
    ]
  },
  {
    path: '/error/:code',
    component: ErrorStatus,
    meta: { title: 'Ошибка — CapitalView', robots: 'noindex, follow' }
  },
  {
    path: '/:pathMatch(.*)*',
    component: NotFound404,
    meta: { title: 'Страница не найдена — CapitalView', robots: 'noindex, follow' }
  }
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

let authDepsPromise = null

async function getAuthDeps() {
  if (!authDepsPromise) {
    authDepsPromise = Promise.all([
      import('../stores/auth.store'),
      import('../services/authService')
    ]).then(([authStoreModule, authServiceModule]) => ({
      useAuthStore: authStoreModule.useAuthStore,
      authService: authServiceModule.authService
    }))
  }
  return authDepsPromise
}

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
      const { useAuthStore } = await getAuthDeps()
      // ОПТИМИЗИРОВАНО: используем authStore для проверки токена, чтобы обновить store
      const authStore = useAuthStore()
      const user = await authStore.checkToken()
      if (!user) {
        // Токен недействителен
        next({ path: '/login', query: { redirect: to.fullPath } })
        return
      }
      if (to.matched.some((r) => r.meta?.requiresAdmin) && !user.is_admin) {
        next({ path: '/dashboard', replace: true })
        return
      }
      // Токен валиден, разрешаем доступ
      next()
    } catch (error) {
      const { useAuthStore } = await getAuthDeps()
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
        const { useAuthStore } = await getAuthDeps()
        // ОПТИМИЗИРОВАНО: используем authStore для проверки токена
        const authStore = useAuthStore()
        const user = await authStore.checkToken()
        if (user) {
          const raw = to.query.redirect
          const redirectPath =
            raw && String(raw).startsWith('/')
              ? String(raw)
              : defaultAuthenticatedPath(user)
          next(redirectPath)
          return
        }
      } catch (error) {
        // Токен недействителен или ошибка сети - очищаем и разрешаем доступ к логину
        if (error.code !== 'ERR_NETWORK' && error.code !== 'ECONNREFUSED') {
          const { authService } = await getAuthDeps()
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
// Если переменная не задана — используем ID из `frontend/index.html`, чтобы не терять pageview в SPA.
const YM_COUNTER_ID = import.meta.env.VITE_YM_COUNTER_ID || 108158122

const DEFAULT_TITLE = 'CapitalView — учёт инвестиций, аналитика портфеля и дивидендный календарь'

function setMetaRobots(content) {
  if (typeof document === 'undefined') return
  let el = document.querySelector('meta[name="robots"]')
  if (!el) {
    el = document.createElement('meta')
    el.setAttribute('name', 'robots')
    document.head.appendChild(el)
  }
  el.setAttribute('content', content)
}

router.afterEach((to) => {
  persistLastAppPathIfNeeded(to)

  const pageTitle = to.meta?.title || to.matched.find(r => r.meta?.title)?.meta?.title || DEFAULT_TITLE
  document.title = pageTitle

  const robots =
    [...to.matched].reverse().find((r) => r.meta?.robots)?.meta?.robots ?? 'index, follow'
  setMetaRobots(robots)

  if (!YM_COUNTER_ID) return
  if (typeof window === 'undefined') return
  if (typeof window.ym !== 'function') return

  const url = `${window.location.origin}${to.fullPath}`
  window.ym(YM_COUNTER_ID, 'hit', url, {
    title: pageTitle,
    referer: document.referrer
  })
})

export default router;
