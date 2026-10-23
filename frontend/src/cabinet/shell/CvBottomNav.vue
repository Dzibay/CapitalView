<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  LayoutDashboard, BarChart3, Briefcase, Coins, ArrowLeftRight, Settings, Shield, MessageSquare, CreditCard, Headphones,
} from 'lucide-vue-next'
import { isLocked, isNavActive } from '../nav'

const props = defineProps({
  user: { type: Object, default: null },
})
const route = useRoute()

const items = computed(() => {
  const user = props.user
  if (user?.is_admin) {
    return [
      { link: '/admin', name: 'Админ', icon: Shield, exact: true },
      { link: '/admin/messages', name: 'Письма', icon: MessageSquare },
      { link: '/admin/billing', name: 'Биллинг', icon: CreditCard },
      { link: '/settings', name: 'Настройки', icon: Settings },
    ]
  }
  if (isLocked(user)) {
    return [
      { link: '/billing', name: 'Подписка', icon: CreditCard },
      { link: '/support', name: 'Поддержка', icon: Headphones },
      { link: '/settings', name: 'Настройки', icon: Settings },
      { link: '/dashboard', name: 'Дашборд', icon: LayoutDashboard, locked: true },
      { link: '/assets', name: 'Активы', icon: Briefcase, locked: true },
    ]
  }
  return [
    { link: '/dashboard', name: 'Дашборд', icon: LayoutDashboard },
    { link: '/analitics', name: 'Аналитика', icon: BarChart3 },
    { link: '/assets', name: 'Активы', icon: Briefcase },
    { link: '/dividends', name: 'Дивиденды', icon: Coins },
    { link: '/transactions', name: 'Операции', icon: ArrowLeftRight },
  ]
})

const activeIndex = computed(() => items.value.findIndex((it) => !it.locked && isNavActive(it, route.path)))
</script>

<template>
  <nav class="cv-bn" aria-label="Основное меню">
    <div class="cv-bn__bar" :style="{ '--n': items.length, '--i': activeIndex }">
      <span v-if="activeIndex >= 0" class="cv-bn__glow" aria-hidden="true" />
      <router-link
        v-for="item in items"
        :key="item.link"
        :to="item.locked ? '/billing' : item.link"
        class="cv-bn__item"
        :class="{ 'is-active': !item.locked && isNavActive(item, route.path), 'is-locked': item.locked }"
      >
        <component :is="item.icon" :size="21" :stroke-width="1.9" />
        <span>{{ item.name }}</span>
      </router-link>
    </div>
  </nav>
</template>

<style scoped>
.cv-bn { display: none; }

@media (max-width: 768px) {
  .cv-bn {
    display: block; position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
    padding: 0 10px calc(10px + env(safe-area-inset-bottom, 0px));
    pointer-events: none;
  }
  .cv-bn__bar {
    position: relative; pointer-events: auto;
    display: grid; grid-template-columns: repeat(var(--n), 1fr);
    height: 62px; padding: 0 4px; border-radius: 20px;
    background: rgba(17, 20, 29, .86);
    backdrop-filter: blur(20px) saturate(160%); -webkit-backdrop-filter: blur(20px) saturate(160%);
    box-shadow: var(--cv-pop-shadow);
  }
  .cv-bn__glow {
    position: absolute; top: 7px; bottom: 7px; left: 4px;
    width: calc((100% - 8px) / var(--n));
    transform: translateX(calc(100% * var(--i)));
    transition: transform .42s var(--cv-ease);
    pointer-events: none;
  }
  .cv-bn__glow::before {
    content: ''; position: absolute; inset: 0 6px; border-radius: 14px;
    background: linear-gradient(180deg, rgba(91, 116, 255, .24), rgba(91, 116, 255, .08));
    box-shadow: inset 0 0 0 1px rgba(124, 142, 255, .22);
  }
  .cv-bn__item {
    position: relative; z-index: 1;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px;
    min-width: 0; text-decoration: none; color: var(--cv-mut);
    font-size: 10.5px; font-weight: 550; letter-spacing: -0.01em;
    transition: color .2s;
    -webkit-tap-highlight-color: transparent;
  }
  .cv-bn__item span { max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cv-bn__item.is-active { color: var(--cv-ink); }
  .cv-bn__item.is-active svg { color: var(--cv-accent-ink); }
  .cv-bn__item svg { transition: transform .3s cubic-bezier(.34, 1.56, .64, 1); }
  .cv-bn__item:active svg { transform: scale(.88); }
  .cv-bn__item.is-locked { color: var(--cv-dim); }
}
</style>
