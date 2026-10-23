<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Lock, Sparkles, PanelLeftClose, PanelLeftOpen, ArrowRight } from 'lucide-vue-next'
import { buildNavSections, isNavActive } from '../nav'
import { plural } from '../format'

const props = defineProps({
  user: { type: Object, default: null },
  collapsed: { type: Boolean, default: false },
})
const emit = defineEmits(['toggle'])

const route = useRoute()
const sections = computed(() => buildNavSections(props.user))

// ─── скользящая подложка активного пункта ────────────────────────────────
const navEl = ref(null)
const indicator = ref({ y: 0, h: 0, visible: false, ready: false })

function measure() {
  const nav = navEl.value
  const el = nav?.querySelector('.cv-nav__item.is-active')
  if (!nav || !el) {
    indicator.value = { ...indicator.value, visible: false }
    return
  }
  const top = el.getBoundingClientRect().top - nav.getBoundingClientRect().top + nav.scrollTop
  const wasVisible = indicator.value.visible
  indicator.value = { y: top, h: el.offsetHeight, visible: true, ready: wasVisible }
}

watch(() => route.path, () => nextTick(measure))
watch(() => [props.collapsed, sections.value], () => setTimeout(measure, 320))

let ro
onMounted(() => {
  nextTick(measure)
  ro = new ResizeObserver(() => measure())
  if (navEl.value) ro.observe(navEl.value)
})
onBeforeUnmount(() => ro?.disconnect())

// ─── подсказки в свёрнутом режиме ────────────────────────────────────────
const tip = ref(null)
function showTip(e, text) {
  if (!props.collapsed) return
  const r = e.currentTarget.getBoundingClientRect()
  tip.value = { text, y: r.top + r.height / 2 }
}
const hideTip = () => { tip.value = null }
watch(() => props.collapsed, hideTip)

// ─── промо подписки ──────────────────────────────────────────────────────
function daysUntil(iso) {
  if (!iso) return null
  const end = new Date(iso).getTime()
  if (Number.isNaN(end)) return null
  return Math.ceil((end - Date.now()) / 86400000)
}
const daysWord = (n) => `${Math.abs(n)} ${plural(n, 'день', 'дня', 'дней')}`

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
      // прогресс 14-дневного триала
      progress: left != null ? Math.max(0.04, Math.min(1, left / 14)) : null,
    }
  }
  if (sub.has_access && left != null && left <= 7) {
    return {
      tone: 'ending',
      title: left <= 0 ? 'Истекает сегодня' : `Осталось ${daysWord(left)}`,
      text: 'Продлите подписку заранее — доступ не прервётся.',
      cta: 'Продлить',
      progress: Math.max(0.04, Math.min(1, Math.max(0, left) / 7)),
    }
  }
  if (sub.has_access === false) {
    return {
      tone: 'expired',
      title: 'Доступ закрыт',
      text: 'Оформите подписку, чтобы снова открыть портфель.',
      cta: 'Оформить',
      progress: null,
    }
  }
  return null
})
</script>

<template>
  <aside class="cv-side" :class="{ 'is-collapsed': collapsed }">
    <div class="cv-side__brand">
      <router-link to="/dashboard" class="cv-side__logo" aria-label="CapitalView — на главную">
        <img src="/site-logo.webp" alt="" width="30" height="30" />
        <span class="cv-side__word">Capital<b>View</b></span>
      </router-link>
    </div>

    <nav ref="navEl" class="cv-nav" aria-label="Разделы кабинета">
      <span
        class="cv-nav__pill"
        :class="{ 'is-visible': indicator.visible, 'is-ready': indicator.ready }"
        :style="{ transform: `translateY(${indicator.y}px)`, height: `${indicator.h}px` }"
        aria-hidden="true"
      />
      <div v-for="section in sections" :key="section.title" class="cv-nav__section">
        <div class="cv-nav__title">{{ section.title }}</div>
        <template v-for="item in section.items" :key="item.link">
          <router-link
            :to="item.locked ? '/billing' : item.link"
            class="cv-nav__item"
            :class="{ 'is-active': !item.locked && isNavActive(item, route.path), 'is-locked': item.locked }"
            :aria-current="!item.locked && isNavActive(item, route.path) ? 'page' : undefined"
            @mouseenter="showTip($event, item.locked ? `${item.name} · по подписке` : item.name)"
            @mouseleave="hideTip"
          >
            <component :is="item.icon" :size="18" :stroke-width="1.9" class="cv-nav__icon" />
            <span class="cv-nav__name">{{ item.name }}</span>
            <Lock v-if="item.locked" :size="13" class="cv-nav__lock" />
          </router-link>
        </template>
      </div>
    </nav>

    <div class="cv-side__foot">
      <router-link
        v-if="promo && !collapsed"
        to="/billing"
        class="cv-promo"
        :class="`cv-promo--${promo.tone}`"
      >
        <div class="cv-promo__head">
          <span class="cv-promo__icon"><Sparkles :size="13" :stroke-width="2.25" /></span>
          <span class="cv-promo__title">{{ promo.title }}</span>
        </div>
        <div v-if="promo.progress != null" class="cv-promo__bar">
          <span :style="{ transform: `scaleX(${promo.progress})` }" />
        </div>
        <p class="cv-promo__text">{{ promo.text }}</p>
        <span class="cv-promo__cta">{{ promo.cta }} <ArrowRight :size="13" /></span>
      </router-link>
      <router-link
        v-else-if="promo"
        to="/billing"
        class="cv-promo-mini"
        :class="`cv-promo--${promo.tone}`"
        @mouseenter="showTip($event, promo.title)"
        @mouseleave="hideTip"
      >
        <Sparkles :size="16" :stroke-width="2.25" />
      </router-link>

      <button
        type="button"
        class="cv-side__toggle"
        :aria-label="collapsed ? 'Развернуть меню' : 'Свернуть меню'"
        @click="emit('toggle')"
        @mouseenter="showTip($event, 'Развернуть меню')"
        @mouseleave="hideTip"
      >
        <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" :size="17" :stroke-width="1.9" />
        <span class="cv-nav__name">Свернуть меню</span>
      </button>
    </div>

    <Transition name="cv-tipfade">
      <div v-if="tip" class="cv-side__tip" :style="{ top: `${tip.y}px` }" role="tooltip">{{ tip.text }}</div>
    </Transition>
  </aside>
</template>

<style scoped>
.cv-side {
  position: fixed; inset: 0 auto 0 0; z-index: 40;
  width: var(--cv-side-w);
  display: flex; flex-direction: column;
  background:
    radial-gradient(140% 40% at 0% 0%, rgba(91, 116, 255, .09), transparent 60%),
    var(--cv-bg);
  box-shadow: inset -1px 0 0 var(--cv-line);
  transition: width .32s var(--cv-ease);
  overflow: hidden;
}
.cv-side.is-collapsed { width: var(--cv-side-w-c); }

.cv-side__brand {
  height: var(--cv-head-h); flex: none;
  display: flex; align-items: center; padding: 0 22px;
}
.cv-side__logo { display: flex; align-items: center; gap: 11px; text-decoration: none; min-width: 0; }
.cv-side__logo img { width: 30px; height: 30px; flex: none; border-radius: 9px; }
.cv-side__word {
  font-family: var(--cv-display); font-size: 17px; font-weight: 600; letter-spacing: -0.02em;
  color: var(--cv-ink); white-space: nowrap;
  transition: opacity .2s, transform .3s var(--cv-ease);
}
.cv-side__word b {
  font-weight: 600;
  background: var(--cv-grad); -webkit-background-clip: text; background-clip: text; color: transparent;
}

/* навигация */
.cv-nav {
  position: relative; flex: 1; min-height: 0; overflow-y: auto; overflow-x: hidden;
  padding: 6px 14px 12px;
  scrollbar-width: none;
}
.cv-nav::-webkit-scrollbar { display: none; }
.cv-nav__section + .cv-nav__section { margin-top: 18px; }
.cv-nav__title {
  height: 26px; padding: 0 12px; display: flex; align-items: center;
  font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim);
  white-space: nowrap; transition: opacity .2s;
}

.cv-nav__pill {
  position: absolute; left: 14px; right: 14px; top: 0; z-index: 0;
  border-radius: 11px; pointer-events: none; opacity: 0;
  background: linear-gradient(90deg, rgba(91, 116, 255, .2), rgba(91, 116, 255, .07));
  box-shadow: inset 0 0 0 1px rgba(124, 142, 255, .22), 0 8px 24px -12px rgba(91, 116, 255, .55);
}
.cv-nav__pill::before {
  content: ''; position: absolute; left: -14px; top: 9px; bottom: 9px; width: 3px; border-radius: 0 3px 3px 0;
  background: linear-gradient(180deg, #8b9cff, #5b74ff); box-shadow: 0 0 12px rgba(91, 116, 255, .9);
}
.cv-nav__pill.is-visible { opacity: 1; }
.cv-nav__pill.is-ready { transition: transform .42s var(--cv-ease), height .3s var(--cv-ease), opacity .2s; }

.cv-nav__item, .cv-side__toggle {
  position: relative; z-index: 1;
  display: flex; align-items: center; gap: 12px; height: 40px; padding: 0 12px;
  border-radius: 11px; text-decoration: none; white-space: nowrap;
  color: var(--cv-mut); font-size: 13.5px; font-weight: 500;
  transition: color .2s, background .2s;
}
.cv-nav__item + .cv-nav__item { margin-top: 2px; }
.cv-nav__item:hover { color: var(--cv-ink); background: var(--cv-hover); }
.cv-nav__item.is-active { color: var(--cv-ink); background: transparent; }
.cv-nav__item.is-active .cv-nav__icon { color: var(--cv-accent-ink); }
.cv-nav__icon { flex: none; transition: transform .35s cubic-bezier(.34, 1.56, .64, 1), color .2s; }
.cv-nav__item:hover .cv-nav__icon { transform: translateX(1px) scale(1.08); }
.cv-nav__name { transition: opacity .2s; }
.cv-nav__lock { margin-left: auto; color: var(--cv-dim); }
.cv-nav__item.is-locked { color: var(--cv-dim); }

/* низ */
.cv-side__foot { flex: none; padding: 10px 14px 16px; display: flex; flex-direction: column; gap: 8px; }
.cv-side__toggle { width: 100%; border: 0; background: transparent; cursor: pointer; color: var(--cv-dim); }
.cv-side__toggle:hover { color: var(--cv-ink); background: var(--cv-hover); }

.cv-promo {
  position: relative; display: block; padding: 14px 14px 13px; border-radius: 16px; text-decoration: none;
  background:
    radial-gradient(120% 100% at 0% 0%, rgba(100, 116, 255, .1), transparent 62%),
    var(--cv-surface-2);
  box-shadow: inset 0 0 0 1px var(--cv-line-2), inset 0 1px 0 rgba(255, 255, 255, .04);
  transition: box-shadow .25s, transform .25s var(--cv-ease);
  overflow: hidden;
}
.cv-promo:hover { box-shadow: inset 0 0 0 1px var(--cv-accent-line), inset 0 1px 0 rgba(255, 255, 255, .05); transform: translateY(-1px); }
.cv-promo--ending { box-shadow: inset 0 0 0 1px rgba(251, 191, 36, .28); background: radial-gradient(120% 100% at 0% 0%, rgba(251, 191, 36, .14), transparent 60%), var(--cv-surface-2); }
.cv-promo--expired { box-shadow: inset 0 0 0 1px rgba(248, 113, 113, .3); background: radial-gradient(120% 100% at 0% 0%, rgba(248, 113, 113, .14), transparent 60%), var(--cv-surface-2); }
.cv-promo__head { display: flex; align-items: center; gap: 8px; }
.cv-promo__icon {
  display: grid; place-items: center; width: 22px; height: 22px; border-radius: 7px;
  color: var(--cv-accent-ink); background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line);
}
.cv-promo--ending .cv-promo__icon { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #1a1205; }
.cv-promo--expired .cv-promo__icon { background: linear-gradient(135deg, #f87171, #ef4444); }
.cv-promo__title { font-size: 13px; font-weight: 600; color: var(--cv-ink); }
.cv-promo__bar { height: 4px; margin: 11px 0 9px; border-radius: 4px; background: rgba(255, 255, 255, .08); overflow: hidden; }
.cv-promo__bar span { display: block; height: 100%; border-radius: inherit; background: var(--cv-grad); transform-origin: left; }
.cv-promo--ending .cv-promo__bar span { background: linear-gradient(90deg, #fbbf24, #f59e0b); }
.cv-promo__text { font-size: 12px; line-height: 1.45; color: var(--cv-mut); white-space: normal; }
.cv-promo__cta { display: inline-flex; align-items: center; gap: 5px; margin-top: 10px; font-size: 12.5px; font-weight: 600; color: var(--cv-accent-ink); }
.cv-promo:hover .cv-promo__cta svg { transform: translateX(2px); }
.cv-promo__cta svg { transition: transform .2s; }

.cv-promo-mini {
  display: grid; place-items: center; height: 40px; border-radius: 11px; color: var(--cv-accent-ink);
  background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line);
}

/* свёрнутый режим */
.cv-side.is-collapsed .cv-side__word,
.cv-side.is-collapsed .cv-nav__name,
.cv-side.is-collapsed .cv-nav__lock { opacity: 0; pointer-events: none; }
.cv-side.is-collapsed .cv-nav__title { opacity: 0; height: 10px; }
.cv-side.is-collapsed .cv-side__brand { padding: 0 23px; }
.cv-side.is-collapsed .cv-nav__item,
.cv-side.is-collapsed .cv-side__toggle { padding: 0 15px; }

.cv-side__tip {
  position: fixed; left: calc(var(--cv-side-w-c) - 4px); z-index: 60; transform: translateY(-50%);
  padding: 6px 10px; border-radius: 9px; font-size: 12.5px; font-weight: 500; color: var(--cv-ink); white-space: nowrap;
  background: var(--cv-elev-2); box-shadow: var(--cv-pop-shadow); pointer-events: none;
}
.cv-tipfade-enter-active, .cv-tipfade-leave-active { transition: opacity .15s, transform .2s var(--cv-ease); }
.cv-tipfade-enter-from, .cv-tipfade-leave-to { opacity: 0; transform: translate(-4px, -50%); }

@media (max-width: 768px) {
  .cv-side { display: none; }
}
</style>
