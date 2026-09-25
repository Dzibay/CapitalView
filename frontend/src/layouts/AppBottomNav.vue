<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  Coins,
  ArrowLeftRight,
  Settings,
  Shield,
  MessageSquare,
} from 'lucide-vue-next'

const route = useRoute()
const authStore = useAuthStore()

const items = computed(() => {
  if (authStore.user?.is_admin) {
    return [
      { to: '/admin', label: 'Админ', icon: Shield },
      { to: '/admin/messages', label: 'Письма', icon: MessageSquare },
      { to: '/settings', label: 'Настройки', icon: Settings },
    ]
  }
  return [
    { to: '/dashboard', label: 'Дашборд', icon: LayoutDashboard },
    { to: '/analitics', label: 'Аналитика', icon: BarChart3 },
    { to: '/assets', label: 'Активы', icon: Briefcase },
    { to: '/dividends', label: 'Дивиденды', icon: Coins },
    { to: '/transactions', label: 'Операции', icon: ArrowLeftRight },
    { to: '/settings', label: 'Настройки', icon: Settings },
  ]
})

function isActive(link) {
  if (link === '/admin') {
    return route.path === '/admin'
  }
  return route.path === link || route.path.startsWith(`${link}/`)
}
</script>

<template>
  <nav class="bottom-nav" aria-label="Основное меню">
    <div class="bottom-nav__inner">
      <router-link
        v-for="item in items"
        :key="item.to"
        :to="item.to"
        class="bottom-nav__item"
        :class="{ 'bottom-nav__item--active': isActive(item.to) }"
      >
        <span class="bottom-nav__icon-wrap">
          <component :is="item.icon" :size="22" class="bottom-nav__icon" stroke-width="2" />
        </span>
        <span class="bottom-nav__label">{{ item.label }}</span>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: none;
}

@media (max-width: 768px) {
  .bottom-nav {
    display: block;
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    z-index: 1002;
    width: 100%;
    max-width: 100%;
    box-sizing: border-box;
    padding-left: env(safe-area-inset-left, 0px);
    padding-right: env(safe-area-inset-right, 0px);
    padding-bottom: 0;
    overflow-x: hidden;
    pointer-events: none;
  }

  .bottom-nav__inner {
    pointer-events: auto;
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    gap: 2px;
    margin: 0;
    width: 100%;
    max-width: 100%;
    min-width: 0;
    padding: 6px 4px calc(8px + env(safe-area-inset-bottom, 0px));
    min-height: calc(var(--bottomNavHeight) - 4px);
    box-sizing: border-box;
    background: #12151a;
    border-radius: 0;
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: none;
  }

  .bottom-nav__item {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    padding: 4px 2px;
    text-decoration: none;
    color: rgba(255, 255, 255, 0.45);
    font-size: 0.625rem;
    font-weight: 500;
    letter-spacing: 0.01em;
    border-radius: var(--radius-sm, 6px);
    transition: color 0.15s ease, background 0.15s ease;
    -webkit-tap-highlight-color: transparent;
  }

  .bottom-nav__item:active {
    transform: none;
    opacity: 0.85;
  }

  .bottom-nav__item--active {
    color: #e8eef4;
    background: rgba(47, 95, 143, 0.28);
    box-shadow: none;
  }

  .bottom-nav__icon-wrap {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 28px;
  }

  .bottom-nav__icon {
    flex-shrink: 0;
    color: currentColor;
  }

  .bottom-nav__label {
    line-height: 1.1;
    text-align: center;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    padding: 0 1px;
  }
}

@media (max-width: 380px) {
  .bottom-nav {
    padding-left: calc(6px + env(safe-area-inset-left, 0px));
    padding-right: calc(6px + env(safe-area-inset-right, 0px));
  }

  .bottom-nav__inner {
    margin: 0;
    padding: 6px 4px calc(8px + env(safe-area-inset-bottom, 0px));
    gap: 0;
    border-radius: 0;
  }

  .bottom-nav__item {
    font-size: 0.5625rem;
    gap: 2px;
  }

  .bottom-nav__icon-wrap {
    width: 36px;
    height: 26px;
  }
}
</style>
