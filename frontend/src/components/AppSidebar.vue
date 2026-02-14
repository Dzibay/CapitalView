<script setup>
import { ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authService } from '../services/authService.js';
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  Coins,
  ArrowLeftRight,
  Settings,
  Sparkles,
} from 'lucide-vue-next';

const route = useRoute();
const router = useRouter();

// Свойство для управления состоянием меню из родительского компонента
defineProps({
  collapsed: {
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

// Структура меню с сегментацией
const menuSections = ref([
  {
    title: 'MENU',
    items: [
      { name: 'Дашборд', link: '/dashboard', icon: LayoutDashboard },
      { name: 'Аналитика', link: '/analitics', icon: BarChart3 },
    ]
  },
  {
    title: 'FINANCIAL',
    items: [
      { name: 'Активы', link: '/assets', icon: Briefcase },
      { name: 'Дивиденды', link: '/dividends', icon: Coins },
      { name: 'Операции', link: '/transactions', icon: ArrowLeftRight },
    ]
  },
  {
    title: 'TOOLS',
    items: [
      { name: 'Настройки', link: '/settings', icon: Settings },
    ]
  }
]);

// Обновление активного пункта меню по текущему маршруту
const updateActiveMenu = () => {
  menuSections.value.forEach(section => {
    section.items.forEach(item => {
    item.active = route.path.startsWith(item.link);
    });
  });
};

// Инициализация
updateActiveMenu();

// Слежение за изменением маршрута
watch(route, () => {
  updateActiveMenu();
});
</script>


<template>
  <!-- Основной контейнер боковой панели. Класс 'sidebar--collapsed' добавляется динамически -->
  <aside class="sidebar" :class="{ 'sidebar--collapsed': collapsed }">
    <!-- Верхний блок: Логотип и название -->
    <div class="sidebar__header">
      <div class="sidebar__logo-icon">
        <!-- Иконка логотипа с градиентом -->
        <div class="logo-wrapper">
          <Sparkles :size="20" class="logo-icon" />
        </div>
      </div>
      <!-- Название сайта, которое плавно исчезает -->
      <Transition name="fade-slide">
        <h1 v-if="!collapsed" class="sidebar__title">
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
            <div v-if="!collapsed" class="sidebar__section-title">
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
                
                <!-- Название элемента меню -->
                <Transition name="fade">
                  <span v-if="!collapsed" class="sidebar__item-name">{{ item.name }}</span>
                </Transition>
          </router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>

    <!-- Нижний блок: Профиль пользователя -->
    <div class="sidebar__footer">
      <!-- Аватар -->
      <!-- <img
        src="https://placehold.co/40x40/ffffff/333333?text=PS"
        alt="User Avatar"
        class="sidebar__user-avatar"
      />

      <div class="sidebar__user-info" v-if="user">
        <p class="sidebar__user-name">{{ user.name }}</p>
        <p class="sidebar__user-role">{{ user.email }}</p>
      </div>

      <button @click="logout" class="sidebar__logout" >
        <span v-html="icons.logout" class="sidebar__logout-icon"></span>
      </button> -->
    </div>
  </aside>
</template>

<style>
/* Глобальные переменные и стили для иконок */
:root {
  --sidebar-bg-color: #11101d;
  --sidebar-item-hover-bg: #1d1b31;
  --sidebar-text-color: #d1d5db;
  --sidebar-text-color-hover: #ffffff;
  --sidebar-primary: #527de5;
  --sidebar-primary-gradient: linear-gradient(135deg, #527de5, #6b91ea);
  --sidebar-accent: hsl(245, 58%, 96%);
}

/* Применение размеров к SVG иконкам через CSS, а не классы */
.sidebar__item-icon svg, .sidebar__submenu-toggle svg, .sidebar__logout-icon svg {
    width: 1.5rem; /* 24px */
    height: 1.5rem; /* 24px */
}
.sidebar__submenu-toggle svg {
    width: 1.25rem; /* 20px */
    height: 1.25rem; /* 20px */
}
.logo-svg {
    width: 2rem; /* 32px */
    height: 2rem; /* 32px */
    color: white;
}
.sidebar__logout-icon svg {
    color: white;
}


/* Основной контейнер */
.sidebar {
  display: flex;
  position: fixed;
  height: 100%;
  flex-direction: column;
  background: rgba(17, 16, 29, 0.95);
  backdrop-filter: blur(24px);
  -webkit-backdrop-filter: blur(24px);
  color: var(--sidebar-text-color);
  width: var(--sidebarWidth);
  transition: width 0.3s ease-in-out;
  z-index: 1000;
  overflow: visible;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 4px 0 40px -8px rgba(0, 0, 0, 0.4);
}

.sidebar--collapsed {
  width: var(--sidebarWidthCollapsed);
}

/* Утилиты для скрытия текста */
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

/* Шапка */
.sidebar__header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  height: var(--headerHeight);
  padding: 0 1.5rem; /* 24px */
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.sidebar__logo-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 52px;
}

.logo-wrapper {
  width: 40px;
  height: 40px;
  border-radius: 1rem;
  background: var(--sidebar-primary-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 6px 20px -4px rgba(82, 125, 229, 0.4);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.logo-wrapper:hover {
  transform: rotate(180deg) scale(1.1);
  box-shadow: 0 8px 24px -4px rgba(82, 125, 229, 0.5);
}

.logo-icon {
  color: white;
  width: 20px;
  height: 20px;
}

.sidebar__title {
  display: flex;
  align-items: center;
  gap: 0;
  font-size: 1.25rem; /* 20px */
  font-weight: 800;
  white-space: nowrap;
  letter-spacing: -0.02em;
}

.title-part {
  color: white;
  transition: opacity 0.2s ease-in-out;
}

.title-part--accent {
  background: var(--sidebar-primary-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* Навигация */
.sidebar__nav {
  flex-grow: 1;
  padding: 1.5rem 0;
  overflow-y: auto;
  overflow-x: hidden;
}

.sidebar__nav-content {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.sidebar__section {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.sidebar__section-title {
  padding: 0 1.5rem;
  font-size: 0.6875rem; /* 11px */
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.4);
  margin-bottom: 0.25rem;
}

.sidebar__nav-list {
  list-style: none;
  padding: 0 0.75rem; /* 12px */
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.375rem; /* 6px */
}

/* NEW: Added for positioning context */
.sidebar__nav-list > li {
  position: relative;
}

.sidebar__nav-item {
  display: flex;
  align-items: center;
  position: relative;
  height: 2.75rem; /* 44px */
  border-radius: 0.875rem; /* 14px */
  color: rgba(255, 255, 255, 0.7);
  text-decoration: none;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  padding: 0 0.75rem;
  font-size: 0.875rem; /* 14px */
  font-weight: 500;
}

.sidebar__nav-item:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(255, 255, 255, 0.9);
  transform: translateX(2px);
}

.sidebar__nav-item--active {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.sidebar-active-indicator {
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 1.5rem;
  border-radius: 0 4px 4px 0;
  background: var(--sidebar-primary-gradient);
  box-shadow: 0 0 12px 2px hsla(245, 58%, 58%, 0.4);
}

.sidebar__item-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  position: relative;
  color: inherit;
}

.sidebar__item-icon svg {
  width: 20px;
  height: 20px;
  stroke-width: 2;
  color: inherit;
}

.sidebar__nav-item--active .sidebar__item-icon {
  color: #ffffff;
}

.sidebar__nav-item:not(.sidebar__nav-item--active) .sidebar__item-icon {
  color: rgba(255, 255, 255, 0.7);
}

.sidebar__item-name {
  white-space: nowrap;
  transition: opacity 0.2s ease-in-out;
  margin-left: 5px;
}

/* Подменю */
.sidebar__submenu-toggle {
  margin-left: auto;
  margin-right: 1rem;
  transition: transform 0.3s, opacity 0.2s;
}

.sidebar__submenu-toggle--open {
  transform: rotate(180deg);
}

.sidebar__submenu {
  list-style: none;
  margin: 0.5rem 0 0 2rem; /* 8px 0 0 32px */
  padding: 0;
  margin: 0;
  overflow: hidden;
  max-height: 0;
  transition: max-height 0.3s ease-in-out;
  z-index: 20000;
}

/* MODIFIED: This now only applies when the sidebar is NOT collapsed */
.sidebar:not(.sidebar--collapsed) .sidebar__submenu--open {
  max-height: 24rem; /* Достаточно большое значение */
}

.sidebar__submenu-item {
  display: block;
  padding: 0.5rem 1rem; /* 8px 16px */
  border-radius: 0.5rem; /* 8px */
  font-size: 0.875rem; /* 14px */
  color: var(--sidebar-text-color);
  text-decoration: none;
  transition: background-color 0.2s, color 0.2s;
  white-space: nowrap;
}

.sidebar__submenu-item:hover {
  background-color: var(--sidebar-item-hover-bg);
  color: var(--sidebar-text-color-hover);
}

/* NEW: Fly-out menu styles for collapsed state */
.sidebar--collapsed .sidebar__submenu {
  position: absolute;
  left: 100%;
  top: 0;
  z-index: 9999; /* Повышаем приоритет */
  margin-left: 0.75rem; /* 12px gap */
  padding: 0.5rem;
  min-width: 190px;
  background-color: var(--sidebar-item-hover-bg);
  border-radius: 0.5rem;
  box-shadow: 0 5px 10px rgba(0, 0, 0, 0.2);
  
  
  /* Override styles from expanded mode */
  max-height: none; 
  
  /* Hide by default */
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transition: opacity 0.2s ease, visibility 0.2s ease;
}

/* NEW: Show fly-out menu on parent hover */
.sidebar--collapsed .sidebar__nav-list > li:hover > .sidebar__submenu {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}


/* Подвал */
.sidebar__footer {
  display: flex;
  align-items: center;
  height: 5rem; /* 80px */
  padding: 0 1.25rem; /* 20px */
  background-color: var(--sidebar-item-hover-bg);
  transition: all 0.3s;
}

.sidebar__user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 0.5rem; /* 8px */
  object-fit: cover;
}

.sidebar__user-info {
  margin-left: 0.75rem; /* 12px */
  overflow: hidden;
  white-space: nowrap;
  transition: width 0.2s, opacity 0.2s;
}

.sidebar__user-name {
  font-weight: 700;
  font-size: 0.875rem; /* 14px */
  color: white;
}

.sidebar__user-role {
  font-size: 0.75rem; /* 12px */
  color: #a0aec0;
}

.sidebar__logout {
  background: none;
  border: none;
  margin-left: auto;
  transition: opacity 0.3s;
}
.sidebar__logout:hover {
  border: 1px solid grey;
}

/* Transitions */
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
  transform: translateX(-10px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

</style>
