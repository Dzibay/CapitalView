<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Bell, Eye, EyeOff, Settings, CreditCard, Headphones, LogOut } from 'lucide-vue-next'
import { useDashboardStore } from '../../stores/dashboard.store'
import { useUIStore } from '../../stores/ui.store'
import { authService } from '../../services/authService.js'
import MissedPayoutsModal from '../../components/modals/MissedPayoutsModal.vue'
import PortfolioSwitcher from './PortfolioSwitcher.vue'
import { privacyMode, togglePrivacyMode } from '../../utils/privacyMode'
import { openPalette, missedPayoutsOpen, modKey } from '../state'
import { pageTitle } from '../nav'
import { userInitials } from '../portfolioTree'

const props = defineProps({
  user: { type: Object, default: null },
})

const route = useRoute()
const router = useRouter()
const dashboardStore = useDashboardStore()
const uiStore = useUIStore()

const isAdmin = computed(() => Boolean(props.user?.is_admin))
const title = computed(() => pageTitle(route))
const portfolios = computed(() => dashboardStore.portfolios ?? [])
const missedCount = computed(() => dashboardStore.missedPayoutsCount || 0)

// ─── тень шапки при прокрутке ────────────────────────────────────────────
const scrolled = ref(false)
const onScroll = () => { scrolled.value = window.scrollY > 4 }
/** на главной заголовок дублирует приветствие — показываем его, только когда страница прокручена */
const quietTitle = computed(() => route.path === '/dashboard' && !scrolled.value)

// ─── меню профиля ────────────────────────────────────────────────────────
const menuOpen = ref(false)
const menuRoot = ref(null)
function onDocDown(e) {
  if (menuOpen.value && menuRoot.value && !menuRoot.value.contains(e.target)) menuOpen.value = false
}
function onKey(e) {
  if (e.key === 'Escape') menuOpen.value = false
}

onMounted(() => {
  onScroll()
  window.addEventListener('scroll', onScroll, { passive: true })
  document.addEventListener('pointerdown', onDocDown)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  document.removeEventListener('pointerdown', onDocDown)
  document.removeEventListener('keydown', onKey)
})

const subLabel = computed(() => {
  const sub = props.user?.subscription
  if (isAdmin.value) return 'Администратор'
  if (!sub) return ''
  if (sub.status === 'trial' && sub.has_access) return 'Пробный период'
  if (sub.has_access === false) return 'Доступ закрыт'
  return sub.plan_name || 'Подписка активна'
})

function go(path) {
  menuOpen.value = false
  router.push(path)
}
function logout() {
  menuOpen.value = false
  authService.logout()
  router.push('/login')
}

// ─── неполученные выплаты ────────────────────────────────────────────────
function closeMissed() {
  missedPayoutsOpen.value = false
  dashboardStore.fetchDashboard(true, false)
}
const refreshDashboard = () => dashboardStore.fetchDashboard(true, false)
</script>

<template>
  <header class="cv-head" :class="{ 'is-scrolled': scrolled }">
    <router-link to="/dashboard" class="cv-head__logo" aria-label="CapitalView">
      <img src="/site-logo.webp" alt="" width="28" height="28" />
    </router-link>

    <div class="cv-head__title" :class="{ 'is-quiet': quietTitle }">
      <Transition name="cv-title" mode="out-in">
        <h1 :key="title">{{ title }}</h1>
      </Transition>
    </div>

    <button type="button" class="cv-head__search" @click="openPalette">
      <Search :size="15" />
      <span class="cv-head__search-text">Поиск активов, разделов и действий</span>
      <span class="cv-head__keys"><kbd class="cv-kbd">{{ modKey }}</kbd><kbd class="cv-kbd">K</kbd></span>
    </button>

    <div class="cv-head__right">
      <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-head__search-icon" aria-label="Поиск" @click="openPalette">
        <Search :size="18" />
      </button>

      <PortfolioSwitcher
        v-if="!isAdmin && portfolios.length > 0"
        :portfolios="portfolios"
        :model-value="uiStore.selectedPortfolioId"
        @update:model-value="uiStore.setSelectedPortfolioId"
      />

      <button
        type="button"
        class="cv-btn cv-btn--ghost cv-btn--icon"
        :class="{ 'is-on': privacyMode }"
        :aria-pressed="privacyMode"
        :title="privacyMode ? 'Показать суммы' : 'Скрыть суммы'"
        @click="togglePrivacyMode"
      >
        <Transition name="cv-swap" mode="out-in">
          <EyeOff v-if="privacyMode" key="off" :size="18" />
          <Eye v-else key="on" :size="18" />
        </Transition>
      </button>

      <button
        v-if="!isAdmin"
        type="button"
        class="cv-btn cv-btn--ghost cv-btn--icon cv-head__bell"
        :class="{ 'has-dot': missedCount > 0 }"
        :title="missedCount > 0 ? `Неполученные выплаты: ${missedCount}` : 'Неполученные выплаты'"
        @click="missedPayoutsOpen = true"
      >
        <Bell :size="18" />
        <span v-if="missedCount > 0" class="cv-head__badge cv-num">{{ missedCount > 99 ? '99+' : missedCount }}</span>
      </button>

      <div ref="menuRoot" class="cv-head__user">
        <button
          type="button"
          class="cv-head__avatar"
          :aria-expanded="menuOpen"
          aria-haspopup="menu"
          aria-label="Меню профиля"
          @click="menuOpen = !menuOpen"
        >
          {{ userInitials(user) }}
        </button>
        <Transition name="cv-pop">
          <div v-if="menuOpen" class="cv-head__menu cv-pop" role="menu">
            <div class="cv-head__me">
              <span class="cv-head__avatar cv-head__avatar--lg">{{ userInitials(user) }}</span>
              <span class="cv-head__me-text">
                <b>{{ user?.name || 'Профиль' }}</b>
                <span>{{ user?.email }}</span>
              </span>
            </div>
            <div v-if="subLabel" class="cv-head__plan">{{ subLabel }}</div>
            <div class="cv-head__sep" />
            <button type="button" class="cv-menu-item" role="menuitem" @click="go('/settings')"><Settings :size="16" /> Настройки</button>
            <button v-if="!isAdmin" type="button" class="cv-menu-item" role="menuitem" @click="go('/billing')"><CreditCard :size="16" /> Подписка</button>
            <button v-if="!isAdmin" type="button" class="cv-menu-item" role="menuitem" @click="go('/support')"><Headphones :size="16" /> Поддержка</button>
            <div class="cv-head__sep" />
            <button type="button" class="cv-menu-item cv-head__logout" role="menuitem" @click="logout"><LogOut :size="16" /> Выйти</button>
          </div>
        </Transition>
      </div>
    </div>

    <MissedPayoutsModal
      v-if="!isAdmin"
      :show="missedPayoutsOpen"
      @close="closeMissed"
      @payouts-added="refreshDashboard"
      @payouts-ignored="refreshDashboard"
    />
  </header>
</template>

<style scoped>
.cv-head {
  position: sticky; top: 0; z-index: 30;
  height: var(--cv-head-h);
  display: flex; align-items: center; gap: 14px;
  padding: 0 var(--cv-pad);
  background: rgba(8, 9, 11, .72);
  backdrop-filter: blur(18px) saturate(140%); -webkit-backdrop-filter: blur(18px) saturate(140%);
  box-shadow: inset 0 -1px 0 transparent;
  transition: box-shadow .25s, background .25s;
}
.cv-head.is-scrolled { box-shadow: inset 0 -1px 0 var(--cv-line); background: rgba(8, 9, 11, .82); }

.cv-head__logo { display: none; }
.cv-head__logo img { display: block; border-radius: 8px; }

.cv-head__title { min-width: 0; flex: 0 1 auto; transition: opacity .3s var(--cv-ease), transform .3s var(--cv-ease); }
.cv-head__title.is-quiet { opacity: 0; transform: translateY(4px); pointer-events: none; }
.cv-head__title h1 {
  font-family: var(--cv-display); font-size: 18px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cv-title-enter-active, .cv-title-leave-active { transition: opacity .2s, transform .3s var(--cv-ease); }
.cv-title-enter-from { opacity: 0; transform: translateY(6px); }
.cv-title-leave-to { opacity: 0; transform: translateY(-6px); }

.cv-head__search {
  display: flex; align-items: center; gap: 10px; height: 38px; width: min(380px, 34vw); margin-left: 18px; padding: 0 8px 0 12px;
  border: 0; border-radius: 11px; cursor: text; color: var(--cv-dim);
  background: rgba(255, 255, 255, .035); box-shadow: inset 0 0 0 1px var(--cv-line);
  transition: background .2s, box-shadow .2s, color .2s;
}
.cv-head__search:hover { background: rgba(255, 255, 255, .055); box-shadow: inset 0 0 0 1px var(--cv-line-2); color: var(--cv-mut); }
.cv-head__search-text { flex: 1; text-align: left; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-head__keys { display: inline-flex; gap: 3px; }
.cv-head__search-icon { display: none; }

.cv-head__right { margin-left: auto; display: flex; align-items: center; gap: 6px; }

.cv-head__bell { position: relative; }
.cv-head__bell.has-dot svg { animation: cv-ring 2.8s ease-in-out 1.2s 2; transform-origin: 50% 10%; }
@keyframes cv-ring {
  0%, 20%, 100% { transform: rotate(0); }
  4% { transform: rotate(14deg); } 8% { transform: rotate(-12deg); } 12% { transform: rotate(8deg); } 16% { transform: rotate(-4deg); }
}
.cv-head__badge {
  position: absolute; top: 3px; right: 2px; min-width: 16px; height: 16px; padding: 0 4px;
  display: grid; place-items: center; border-radius: 99px;
  font-size: 10px; font-weight: 700; color: #fff; background: #ef4444;
  box-shadow: 0 0 0 2px var(--cv-bg), 0 0 12px rgba(239, 68, 68, .6);
}

.cv-head__user { position: relative; margin-left: 4px; }
.cv-head__avatar {
  display: grid; place-items: center; width: 36px; height: 36px; border: 0; border-radius: 12px; cursor: pointer;
  font-size: 13px; font-weight: 700; letter-spacing: .02em; color: #fff;
  background: linear-gradient(135deg, #5b74ff 0%, #8b5cf6 60%, #7dd3fc 130%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .3), 0 0 0 1px rgba(255, 255, 255, .08);
  transition: transform .2s var(--cv-ease), box-shadow .2s;
}
.cv-head__avatar:hover { transform: translateY(-1px); box-shadow: inset 0 1px 0 rgba(255, 255, 255, .3), 0 0 0 1px rgba(255, 255, 255, .14), 0 8px 20px -8px rgba(91, 116, 255, .8); }
.cv-head__avatar--lg { width: 40px; height: 40px; flex: none; cursor: default; }
.cv-head__menu { position: absolute; top: calc(100% + 8px); right: 0; z-index: 50; width: 264px; transform-origin: top right; }
.cv-head__me { display: flex; align-items: center; gap: 11px; padding: 8px 8px 6px; }
.cv-head__me-text { display: flex; flex-direction: column; min-width: 0; line-height: 1.3; }
.cv-head__me-text b { font-size: 13.5px; font-weight: 600; color: var(--cv-ink); }
.cv-head__me-text span { font-size: 12px; color: var(--cv-mut); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cv-head__plan {
  margin: 4px 8px 6px; padding: 6px 10px; border-radius: 9px; font-size: 12px; font-weight: 550; color: var(--cv-accent-ink);
  background: var(--cv-accent-soft);
}
.cv-head__sep { height: 1px; margin: 6px 4px; background: var(--cv-line); }
.cv-head__logout:hover { color: var(--cv-down); }
.cv-head__logout:hover svg { color: var(--cv-down); }

.cv-swap-enter-active, .cv-swap-leave-active { transition: opacity .15s, transform .2s var(--cv-ease); }
.cv-swap-enter-from { opacity: 0; transform: scale(.7) rotate(-20deg); }
.cv-swap-leave-to { opacity: 0; transform: scale(.7) rotate(20deg); }

@media (max-width: 1100px) {
  .cv-head__search { width: 44px; padding: 0; justify-content: center; margin-left: 4px; }
  .cv-head__search-text, .cv-head__keys { display: none; }
}
@media (max-width: 768px) {
  .cv-head { padding: 0 12px; gap: 8px; height: 58px; }
  .cv-head__logo { display: block; flex: none; }
  .cv-head__title { display: none; }
  .cv-head__search { display: none; }
  .cv-head__search-icon { display: inline-flex; }
  .cv-head__right { gap: 2px; }
  .cv-head__avatar { width: 32px; height: 32px; border-radius: 10px; font-size: 12px; }
}
</style>
