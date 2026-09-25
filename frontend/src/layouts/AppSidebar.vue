<script setup>
import { ref, watch } from 'vue';
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

function buildMenuSections(user) {
  if (user?.is_admin) {
    return [
      {
        title: 'АДМИН',
        items: [
          { name: 'Статистика', link: '/admin', icon: Shield, exact: true },
          { name: 'Сообщения', link: '/admin/messages', icon: MessageSquare },
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
        { name: 'Дашборд', link: '/dashboard', icon: LayoutDashboard },
        { name: 'Аналитика', link: '/analitics', icon: BarChart3 },
      ],
    },
    {
      title: 'ФИНАНСЫ',
      items: [
        { name: 'Активы', link: '/assets', icon: Briefcase },
        { name: 'Дивиденды', link: '/dividends', icon: Coins },
        { name: 'Операции', link: '/transactions', icon: ArrowLeftRight },
      ],
    },
    {
      title: 'ДОПОЛНИТЕЛЬНО',
      items: [
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
            </li>
          </ul>
        </div>
      </div>
    </nav>

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
