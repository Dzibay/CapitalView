<script setup>
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useUIStore } from '../stores/ui.store';
import { authService } from '../services/authService.js';
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  Coins,
  ArrowLeftRight,
  Settings,
  Shield,
  MessageSquare,
  Headphones,
  CreditCard,
  Sparkles,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();
const uiStore = useUIStore();

const props = defineProps({
  collapsed: {
    type: Boolean,
    default: false
  },
  mobileOpen: {
    type: Boolean,
    default: false
  },
  user: {
    type: Object,
    required: true,
  },
});

const logout = () => {
  authService.logout();
  router.push('/login');
};

// Для hover эффектов иконок
const hoveredItem = ref(null);

// Картинка логотипа для сайдбара.
// Ожидается в `frontend/public`
const logoSrc = ref('/site-logo.webp');

function daysWord(n) {
  const abs = Math.abs(n)
  const mod10 = abs % 10
  const mod100 = abs % 100
  let unit = 'дней'
  if (mod10 === 1 && mod100 !== 11) unit = 'день'
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) unit = 'дня'
  return `${abs} ${unit}`
}

function daysUntil(iso) {
  if (!iso) return null
  const end = new Date(iso).getTime()
  if (Number.isNaN(end)) return null
  return Math.ceil((end - Date.now()) / 86400000)
}

const promo = computed(() => {
  const user = props.user
  if (!user || user.is_admin) return null
  const sub = user.subscription
  if (!sub) return null

  const endsAt = sub.access_ends_at || sub.trial_ends_at || sub.current_period_ends_at
  const left = daysUntil(endsAt)

  if (sub.status === 'trial' && sub.has_access) {
    return {
      tone: 'trial',
      title: 'Пробный период',
      text: left != null && left > 0
        ? `Ещё ${daysWord(left)}. Оформите тариф без паузы в доступе.`
        : 'Оформите тариф, чтобы сохранить доступ к портфелю.',
      cta: 'К тарифам',
    }
  }

  if (sub.has_access && left != null && left <= 7) {
    return {
      tone: 'ending',
      title: left <= 0 ? 'Истекает сегодня' : `Осталось ${daysWord(left)}`,
      text: 'Продлите подписку заранее — доступ не прервётся.',
      cta: 'Продлить',
    }
  }

  if (sub.has_access === false) {
    return {
      tone: 'expired',
      title: 'Доступ закрыт',
      text: 'Оформите подписку, чтобы снова открыть портфель.',
      cta: 'Оформить',
    }
  }

  return null
})

const showPromoExpanded = computed(() => Boolean(promo.value) && (!props.collapsed || props.mobileOpen))
const showPromoCollapsed = computed(() => Boolean(promo.value) && props.collapsed && !props.mobileOpen)

function buildMenuSections(user) {
  const locked = Boolean(user && !user.is_admin && user.subscription && user.subscription.has_access === false)

  if (user?.is_admin) {
    return [
      {
        title: 'АДМИН',
        items: [
          { name: 'Статистика', link: '/admin', icon: Shield, exact: true },
          { name: 'Сообщения', link: '/admin/messages', icon: MessageSquare },
          { name: 'Биллинг', link: '/admin/billing', icon: CreditCard },
        ],
      },
      {
        title: 'АККАУНТ',
        items: [{ name: 'Настройки', link: '/settings', icon: Settings }],
      },
    ]
  }
  return [
    {
      title: 'МЕНЮ',
      items: [
        { name: 'Дашборд', link: '/dashboard', icon: LayoutDashboard, locked },
        { name: 'Аналитика', link: '/analitics', icon: BarChart3, locked },
      ],
    },
    {
      title: 'ФИНАНСЫ',
      items: [
        { name: 'Активы', link: '/assets', icon: Briefcase, locked },
        { name: 'Дивиденды', link: '/dividends', icon: Coins, locked },
        { name: 'Операции', link: '/transactions', icon: ArrowLeftRight, locked },
      ],
    },
    {
      title: 'ДОПОЛНИТЕЛЬНО',
      items: [
        { name: 'Подписка', link: '/billing', icon: CreditCard },
        { name: 'Поддержка', link: '/support', icon: Headphones },
        { name: 'Настройки', link: '/settings', icon: Settings },
      ],
    },
  ]
}

const menuSections = ref(buildMenuSections(null));

const updateActiveMenu = () => {
  menuSections.value.forEach((section) => {
    section.items.forEach((item) => {
      item.active = item.exact
        ? route.path === item.link
        : route.path === item.link || route.path.startsWith(`${item.link}/`);
    });
  });
};

function syncMenuFromUser() {
  menuSections.value = buildMenuSections(props.user);
  updateActiveMenu();
}

syncMenuFromUser();

watch(
  () => props.user,
  () => syncMenuFromUser(),
  { deep: true },
);

watch(route, () => {
  updateActiveMenu();
  uiStore.setMobileMenuOpen(false);
});
</script>


<template>
  <!-- Основной контейнер боковой панели. Класс 'sidebar--collapsed' добавляется динамически -->
  <aside class="sidebar" :class="{ 'sidebar--collapsed': collapsed, 'sidebar--mobile-open': mobileOpen }">
    <!-- Верхний блок: Логотип и название -->
    <div class="sidebar__header">
      <div class="sidebar__logo-icon">
        <!-- Иконка логотипа с градиентом -->
        <img
            :src="logoSrc"
            class="logo-img"
            alt="CapitalView logo"
            @error="handleLogoError"
          />
        
      </div>
      <!-- Название сайта (скрыто при свёрнутом сайдбаре; на мобильном показываем при открытом меню) -->
      <Transition name="fade-slide">
        <h1 v-if="!collapsed || mobileOpen" class="sidebar__title">
          <span class="title-part">Capital</span><span class="title-part title-part--accent">View</span>
        </h1>
      </Transition>
    </div>

    <!-- Основная навигация -->
    <nav class="sidebar__nav">
      <div class="sidebar__nav-content">
        <!-- Цикл по секциям меню -->
        <div v-for="section in menuSections" :key="section.title" class="sidebar__section">
          <!-- Заголовок секции -->
          <Transition name="fade">
            <div v-if="!collapsed || mobileOpen" class="sidebar__section-title">
              {{ section.title }}
            </div>
          </Transition>
          
          <!-- Элементы секции -->
      <ul class="sidebar__nav-list">
            <li v-for="item in section.items" :key="item.name">
          <router-link
            v-if="!item.locked"
            :to="item.link"
            class="sidebar__nav-item"
            :class="{ 'sidebar__nav-item--active': item.active }"
                @mouseenter="hoveredItem = item.name"
                @mouseleave="hoveredItem = null"
              >
                <!-- Активный индикатор -->
                <div v-if="item.active" class="sidebar-active-indicator"></div>
                
                <!-- Иконка элемента меню с анимацией -->
                <div 
                  class="sidebar__item-icon"
                  :style="{
                    transform: hoveredItem === item.name ? 'scale(1.15) rotate(5deg)' : 'scale(1) rotate(0deg)',
                    transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)'
                  }"
                >
                  <component :is="item.icon" :size="20" :class="{ 'icon-active': item.active }" />
                </div>
                
                <!-- Название элемента меню (на мобильном всегда видно при открытом меню) -->
                <Transition name="fade">
                  <span v-if="!collapsed || mobileOpen" class="sidebar__item-name">{{ item.name }}</span>
                </Transition>
          </router-link>
          <div
            v-else
            class="sidebar__nav-item sidebar__nav-item--locked"
            :title="'Доступно после оформления подписки'"
            aria-disabled="true"
          >
            <div class="sidebar__item-icon">
              <component :is="item.icon" :size="20" />
            </div>
            <Transition name="fade">
              <span v-if="!collapsed || mobileOpen" class="sidebar__item-name">{{ item.name }}</span>
            </Transition>
          </div>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <div v-if="showPromoExpanded" class="sidebar__promo" :class="`sidebar__promo--${promo.tone}`">
      <div class="sidebar__promo-icon">
        <Sparkles :size="14" :stroke-width="2.25" />
      </div>
      <p class="sidebar__promo-title">{{ promo.title }}</p>
      <p class="sidebar__promo-text">{{ promo.text }}</p>
      <router-link to="/billing" class="sidebar__promo-cta">{{ promo.cta }}</router-link>
    </div>

    <router-link
      v-else-if="showPromoCollapsed"
      to="/billing"
      class="sidebar__promo-mini"
      :class="`sidebar__promo-mini--${promo.tone}`"
      :title="promo.title"
    >
      <Sparkles :size="16" :stroke-width="2.25" />
    </router-link>

  </aside>
</template>

<style>
/* Institutional ink — матовый сайдбар без glass/glow */
:root {
  --sidebar-bg-color: #12151a;
  --sidebar-item-hover-bg: #1c2128;
  --sidebar-text-color: #a8b0ba;
  --sidebar-text-color-hover: #f2f4f6;
  --sidebar-primary: #2f5f8f;
  --sidebar-accent: #e8eef4;
  --sidebar-border: rgba(255, 255, 255, 0.08);
}

.sidebar__item-icon svg, .sidebar__submenu-toggle svg, .sidebar__logout-icon svg {
    width: 1.25rem;
    height: 1.25rem;
}
.sidebar__submenu-toggle svg {
    width: 1.125rem;
    height: 1.125rem;
}
.logo-svg {
    width: 2rem;
    height: 2rem;
    color: white;
}
.sidebar__logout-icon svg {
    color: white;
}

.sidebar {
  display: flex;
  position: fixed;
  height: 100%;
  flex-direction: column;
  background: var(--sidebar-bg-color);
  color: var(--sidebar-text-color);
  width: var(--sidebarWidth);
  transition: width 0.25s ease;
  z-index: 1000;
  overflow: visible;
  border-right: 1px solid var(--sidebar-border);
}

.sidebar--collapsed {
  width: var(--sidebarWidthCollapsed);
}

.sidebar--collapsed .sidebar__title,
.sidebar--collapsed .sidebar__item-name,
.sidebar--collapsed .sidebar__section-title,
.sidebar--collapsed .sidebar__submenu-toggle,
.sidebar--collapsed .sidebar__logout-icon {
  opacity: 0;
  pointer-events: none;
  width: 0;
  overflow: hidden;
}
.sidebar--collapsed .sidebar__user-info {
    width: 0;
    opacity: 0;
}

.sidebar__header {
  display: flex;
  align-items: center;
  gap: 0;
  height: var(--headerHeight);
  padding: 0 1.25rem;
  border-bottom: 1px solid var(--sidebar-border);
}

.sidebar__logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 40px;
}

.logo-img {
  width: 40px;
  height: 40px;
  object-fit: cover;
  object-position: center;
  display: block;
}

.sidebar__title {
  display: flex;
  align-items: center;
  gap: 0;
  font-size: 1.0625rem;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: -0.03em;
}

.title-part {
  color: #f2f4f6;
  transition: opacity 0.2s ease;
}

.title-part--accent {
  color: #8eb0d0;
  background: none;
  -webkit-text-fill-color: unset;
}

.sidebar__nav {
  flex-grow: 1;
  padding: 1.25rem 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar__nav-content {
  display: flex;
  flex-direction: column;
  gap: 1.75rem;
}

.sidebar__section {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.sidebar__section-title {
  padding: 0 1.25rem;
  font-size: 0.625rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: rgba(255, 255, 255, 0.32);
  margin-bottom: 0.375rem;
}

.sidebar__nav-list {
  list-style: none;
  padding: 0 0.625rem;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.sidebar__nav-list > li {
  position: relative;
}

.sidebar__nav-item {
  display: flex;
  align-items: center;
  position: relative;
  height: 2.5rem;
  border-radius: var(--radius-sm, 6px);
  color: rgba(255, 255, 255, 0.62);
  text-decoration: none;
  transition: background-color 0.15s ease, color 0.15s ease;
  cursor: pointer;
  padding: 0 0.75rem;
  font-size: 0.8125rem;
  font-weight: 500;
  letter-spacing: -0.01em;
}

.sidebar__nav-item:hover {
  background: var(--sidebar-item-hover-bg);
  color: rgba(255, 255, 255, 0.9);
}

.sidebar__nav-item--active {
  background: rgba(47, 95, 143, 0.22);
  color: #f2f4f6;
  font-weight: 600;
}

.sidebar__nav-item--locked {
  opacity: 0.38;
  cursor: not-allowed;
  pointer-events: none;
  filter: grayscale(0.4);
  color: var(--sidebar-text-color);
}

.sidebar-active-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 2px;
  height: 1.125rem;
  border-radius: 0;
  background: var(--sidebar-primary);
  box-shadow: none;
}

.sidebar__item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  position: relative;
  color: inherit;
}

.sidebar__item-icon svg {
  width: 18px;
  height: 18px;
  stroke-width: 1.75;
  color: inherit;
}

.sidebar__nav-item--active .sidebar__item-icon {
  color: #c5d6e8;
}

.sidebar__nav-item:not(.sidebar__nav-item--active) .sidebar__item-icon {
  color: rgba(255, 255, 255, 0.5);
}

.sidebar__item-name {
  white-space: nowrap;
  transition: opacity 0.2s ease;
  margin-left: 6px;
}

.sidebar__submenu-toggle {
  margin-left: auto;
  margin-right: 0.75rem;
  transition: transform 0.25s, opacity 0.2s;
}

.sidebar__submenu-toggle--open {
  transform: rotate(180deg);
}

.sidebar__submenu {
  list-style: none;
  padding: 0;
  margin: 0;
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.25s ease;
  z-index: 20000;
}

.sidebar:not(.sidebar--collapsed) .sidebar__submenu--open {
  max-height: 24rem;
}

.sidebar__submenu-item {
  display: block;
  padding: 0.5rem 1rem;
  border-radius: var(--radius-sm, 6px);
  font-size: 0.8125rem;
  color: var(--sidebar-text-color);
  text-decoration: none;
  transition: background-color 0.15s, color 0.15s;
  white-space: nowrap;
}

.sidebar__submenu-item:hover {
  background-color: var(--sidebar-item-hover-bg);
  color: var(--sidebar-text-color-hover);
}

.sidebar--collapsed .sidebar__submenu {
  position: absolute;
  left: 100%;
  top: 0;
  z-index: 9999;
  margin-left: 0.5rem;
  padding: 0.375rem;
  min-width: 180px;
  background-color: var(--sidebar-bg-color);
  border: 1px solid var(--sidebar-border);
  border-radius: var(--radius-md, 8px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
  max-height: none;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.15s ease, visibility 0.15s ease;
}

.sidebar--collapsed .sidebar__nav-list > li:hover > .sidebar__submenu {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}

.sidebar__user-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-sm, 6px);
  object-fit: cover;
}

.sidebar__user-info {
  margin-left: 0.75rem;
  overflow: hidden;
  white-space: nowrap;
  transition: width 0.2s, opacity 0.2s;
}

.sidebar__user-name {
  font-weight: 600;
  font-size: 0.8125rem;
  color: #f2f4f6;
}

.sidebar__user-role {
  font-size: 0.6875rem;
  color: #7a8490;
}

.sidebar__logout {
  background: none;
  border: none;
  margin-left: auto;
  transition: opacity 0.2s;
}
.sidebar__logout:hover {
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.sidebar__promo {
  margin: 0 0.75rem 0.875rem;
  padding: 0.875rem 0.875rem 0.75rem;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(165deg, rgba(47, 95, 143, 0.28), rgba(28, 33, 40, 0.9));
}

.sidebar__promo--ending {
  background: linear-gradient(165deg, rgba(196, 138, 26, 0.22), rgba(28, 33, 40, 0.92));
  border-color: rgba(196, 138, 26, 0.22);
}

.sidebar__promo--expired {
  background: linear-gradient(165deg, rgba(209, 67, 67, 0.2), rgba(28, 33, 40, 0.92));
  border-color: rgba(209, 67, 67, 0.2);
}

.sidebar__promo-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-bottom: 0.5rem;
  border-radius: 7px;
  background: rgba(255, 255, 255, 0.08);
  color: #c5d6e8;
}

.sidebar__promo--ending .sidebar__promo-icon {
  color: #f0d29a;
}

.sidebar__promo--expired .sidebar__promo-icon {
  color: #f0b4b4;
}

.sidebar__promo-title {
  margin: 0 0 0.25rem;
  font-size: 0.8125rem;
  font-weight: 650;
  color: #f2f4f6;
  letter-spacing: -0.01em;
}

.sidebar__promo-text {
  margin: 0 0 0.75rem;
  font-size: 0.6875rem;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.58);
}

.sidebar__promo-cta {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 0.5rem 0.625rem;
  border-radius: 8px;
  background: #2f5f8f;
  color: #fff;
  text-decoration: none;
  font-size: 0.75rem;
  font-weight: 650;
  transition: background 0.15s ease;
}

.sidebar__promo-cta:hover {
  background: #3a6fa3;
}

.sidebar__promo--ending .sidebar__promo-cta {
  background: #a87a1c;
}

.sidebar__promo--ending .sidebar__promo-cta:hover {
  background: #c48a1a;
}

.sidebar__promo--expired .sidebar__promo-cta {
  background: #b83c3c;
}

.sidebar__promo--expired .sidebar__promo-cta:hover {
  background: #d14343;
}

.sidebar__promo-mini {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  margin: 0 auto 0.875rem;
  border-radius: 10px;
  background: rgba(47, 95, 143, 0.35);
  color: #c5d6e8;
  text-decoration: none;
  transition: background 0.15s ease;
}

.sidebar__promo-mini:hover {
  background: rgba(47, 95, 143, 0.55);
}

.sidebar__promo-mini--ending {
  background: rgba(196, 138, 26, 0.28);
  color: #f0d29a;
}

.sidebar__promo-mini--expired {
  background: rgba(209, 67, 67, 0.28);
  color: #f0b4b4;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateX(-6px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}

@media (max-width: 768px) {
  .sidebar {
    display: none !important;
  }
}
</style>
