<script setup>
import { nextTick, onMounted, onUnmounted, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import LandingIcon from './LandingIcon.vue'
import LandingHero from './LandingHero.vue'
import LandingFlow from './LandingFlow.vue'
import LandingBento from './LandingBento.vue'
import LandingAssets3D from './LandingAssets3D.vue'
import LandingRebalancer from './LandingRebalancer.vue'
import { useSmoothScroll, useLandingFonts, prefersReducedMotion } from './useLandingMotion'
import { securityTabs, pricingFeatures, faq } from '../../content/home/landingData'
import { billingService } from '../../../services/billingService'

gsap.registerPlugin(ScrollTrigger)
useLandingFonts('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Inter+Tight:wght@500;600;700&display=swap')
const { scrollTo } = useSmoothScroll()

const navLinks = [
  { href: '#flow', t: 'Как работает' },
  { href: '#features', t: 'Возможности' },
  { href: '#build', t: 'Конструктор' },
  { href: '#security', t: 'Безопасность' },
  { href: '#faq', t: 'Вопросы' }
]
const headerSolid = ref(false)
const headerDark = ref(true)
const menuOpen = ref(false)
function go(href) {
  menuOpen.value = false
  scrollTo(href)
}
// прямой заход по якорю (/#pricing, редирект с /pricing): роутер скроллит раньше,
// чем hero закрепит первый экран, поэтому переходим сами, когда разметка готова
function onHeroReady() {
  if (location.hash.length > 1) scrollTo(location.hash, { immediate: true })
  onScroll()
}

const stats = [
  { v: 60, suffix: ' сек', t: 'от регистрации до готового дашборда' },
  { v: 6, suffix: '', t: 'классов активов в одном дашборде' },
  { v: 100, suffix: '%', t: 'операций загружаются из брокера сами' },
  { v: 152, prefix: '', suffix: '-ФЗ', t: 'хранение персональных данных' }
]

const manifesto = 'CapitalView собирает все счета, сделки и выплаты в одну картину — и честно считает, сколько вы на самом деле заработали. Без таблиц. Без ручного ввода. Без догадок.'
const manifestoWords = manifesto.split(' ')

const secIcons = { readonly: 'eye', encryption: 'lock', api: 'plug', privacy: 'eye-off' }
const priceList = [...pricingFeatures, 'Мультивалютность и курсы ЦБ', 'Конструктор портфеля']

// пробный период и тарифы — из биллинга (как было в старом HomePage)
const trialDays = ref(14)
const tariffs = ref([])
function daysLabel(n) {
  const d = Number(n) || 0
  if (d % 10 === 1 && d % 100 !== 11) return `${d} день`
  if (d % 10 >= 2 && d % 10 <= 4 && (d % 100 < 10 || d % 100 >= 20)) return `${d} дня`
  return `${d} дней`
}
const formatPrice = (v) => Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
billingService.fetchPublic().then((data) => {
  trialDays.value = data.trial_days
  tariffs.value = data.tariffs
}).catch(() => {
  // лендинг работает и с дефолтным пробным периодом
})
const openFaq = ref(0)

const root = ref(null)
let ctx = null

function onScroll() {
  headerSolid.value = window.scrollY > 24
  // над тёмным первым экраном шапка тоже тёмная
  const hero = root.value?.querySelector('.hx')
  headerDark.value = !!hero && hero.getBoundingClientRect().bottom > 40
}
function magnet(e) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  gsap.to(el, { x: (e.clientX - r.left - r.width / 2) * 0.25, y: (e.clientY - r.top - r.height / 2) * 0.35, duration: 0.5, ease: 'power3.out' })
}
function magnetLeave(e) { gsap.to(e.currentTarget, { x: 0, y: 0, duration: 0.9, ease: 'elastic.out(1, 0.45)' }) }

onMounted(async () => {
  await nextTick()
  window.addEventListener('scroll', onScroll, { passive: true })
  onScroll()
  const reduced = prefersReducedMotion()

  ctx = gsap.context(() => {
    // заголовки секций и общие появления
    gsap.utils.toArray('[data-reveal]').forEach((el) => {
      if (reduced) return
      gsap.from(el, { y: 40, opacity: 0, duration: 1.2, ease: 'expo.out', scrollTrigger: { trigger: el, start: 'top 88%', once: true } })
    })
    gsap.utils.toArray('.lp-head').forEach((el) => {
      if (reduced) return
      gsap.from(el.children, { y: 30, opacity: 0, duration: 1.1, ease: 'expo.out', stagger: 0.08, scrollTrigger: { trigger: el, start: 'top 85%', once: true } })
    })
    // иконки «дорисовываются» при появлении
    gsap.utils.toArray('[data-draw]').forEach((el) => {
      ScrollTrigger.create({ trigger: el, start: 'top 85%', once: true, onEnter: () => el.classList.add('is-in') })
    })

    // счётчики
    gsap.utils.toArray('.lp-stat__num').forEach((el) => {
      const to = Number(el.dataset.to)
      const o = { v: reduced ? to : 0 }
      const render = () => { el.textContent = Math.round(o.v) }
      render()
      if (!reduced) gsap.to(o, { v: to, duration: 1.8, ease: 'expo.out', onUpdate: render, scrollTrigger: { trigger: el, start: 'top 90%', once: true } })
    })

    // манифест: слова проявляются по мере скролла
    gsap.fromTo('.lp-manifesto__w', { opacity: 0.14 }, {
      opacity: 1, ease: 'none', stagger: 0.1,
      scrollTrigger: { trigger: '.lp-manifesto', start: 'top 75%', end: 'bottom 45%', scrub: true }
    })

    if (reduced) return

    // безопасность: кольца радара и центральный замок
    gsap.from('.lp-radar', {
      scale: 0.7, opacity: 0, duration: 1.6, ease: 'expo.out',
      scrollTrigger: { trigger: '.lp-sec', start: 'top 70%', once: true }
    })

    // тариф: карточка выезжает с лёгким наклоном
    gsap.from('.lp-price__card', {
      y: 80, rotateX: 12, opacity: 0, duration: 1.5, ease: 'expo.out',
      scrollTrigger: { trigger: '.lp-price', start: 'top 75%', once: true }
    })

    // финальный блок раскрывается из скруглённой карточки
    gsap.fromTo('.lp-final__card', { clipPath: 'inset(8% 6% 8% 6% round 40px)' }, {
      clipPath: 'inset(0% 0% 0% 0% round 32px)', ease: 'none',
      scrollTrigger: { trigger: '.lp-final', start: 'top 90%', end: 'top 25%', scrub: true }
    })
  }, root.value)

  document.fonts?.ready.then(() => ScrollTrigger.refresh())
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
  ctx?.revert()
})
</script>

<template>
  <div ref="root" class="lp">
    <!-- HEADER -->
    <header class="lp-header" :class="{ 'is-solid': headerSolid || menuOpen, 'is-open': menuOpen, 'is-dark': headerDark && !menuOpen }">
      <div class="lp-header__in">
        <router-link to="/" class="lp-logo"><img src="/site-logo.webp" alt="" width="26" height="26" />CapitalView</router-link>
        <nav class="lp-nav">
          <a v-for="l in navLinks" :key="l.href" :href="l.href" @click.prevent="go(l.href)">{{ l.t }}</a>
        </nav>
        <div class="lp-header__actions">
          <router-link to="/login" class="lp-header__login">Войти</router-link>
          <router-link to="/login" class="lp-btn lp-btn--dark lp-btn--sm">Начать бесплатно</router-link>
          <button type="button" class="lp-burger" :aria-expanded="menuOpen" aria-label="Меню" @click="menuOpen = !menuOpen">
            <LandingIcon :name="menuOpen ? 'close' : 'menu'" :size="22" />
          </button>
        </div>
      </div>
      <nav class="lp-mnav" :aria-hidden="!menuOpen">
        <a v-for="l in navLinks" :key="l.href" :href="l.href" @click.prevent="go(l.href)">{{ l.t }}<LandingIcon name="arrow" :size="18" /></a>
        <router-link to="/login" class="lp-btn lp-btn--dark lp-btn--lg">Войти или создать аккаунт</router-link>
      </nav>
    </header>

    <main>
      <LandingHero @demo="go('#flow')" @ready="onHeroReady" />

      <!-- STATS -->
      <section class="lp-stats">
        <div class="lp-container lp-stats__grid">
          <div v-for="s in stats" :key="s.t" class="lp-stat" data-reveal>
            <b><span class="lp-stat__num" :data-to="s.v">{{ s.v }}</span>{{ s.suffix }}</b>
            <span>{{ s.t }}</span>
          </div>
        </div>
      </section>

      <!-- MANIFESTO -->
      <section class="lp-manifesto">
        <div class="lp-container">
          <p class="lp-manifesto__text">
            <template v-for="(w, i) in manifestoWords" :key="i"><span class="lp-manifesto__w">{{ w }}</span>{{ ' ' }}</template>
          </p>
        </div>
      </section>

      <LandingAssets3D />

      <LandingFlow />

      <LandingBento />

      <!-- BUILDER -->
      <section id="build" class="lp-build">
        <div class="lp-container">
          <header class="lp-head lp-head--center">
            <span class="lp-eyebrow">Конструктор</span>
            <h2 class="lp-h2">Соберите портфель <span class="lp-grad">своей мечты</span></h2>
            <p class="lp-sub">Подвигайте ползунки и посмотрите, как меняются риск и ожидаемая доходность. В CapitalView то же самое — на ваших реальных данных.</p>
          </header>
          <LandingRebalancer class="lp-build__tool" data-reveal />
        </div>
      </section>

      <!-- SECURITY -->
      <section id="security" class="lp-sec">
        <div class="lp-container">
          <header class="lp-head lp-head--center">
            <span class="lp-eyebrow lp-eyebrow--dark">Безопасность</span>
            <h2 class="lp-h2">Только чтение.<br /><span class="lp-dim">Ни одной сделки без вас.</span></h2>
          </header>

          <div class="lp-radar" aria-hidden="true">
            <span v-for="n in 4" :key="n" class="lp-radar__ring" :style="{ '--n': n }" />
            <span class="lp-radar__pulse" />
            <span class="lp-radar__pulse lp-radar__pulse--2" />
            <span class="lp-radar__orbit"><i /></span>
            <span class="lp-radar__orbit lp-radar__orbit--2"><i /></span>
            <span class="lp-radar__core" data-draw><LandingIcon name="shield" class="is-draw" :size="44" :stroke="1.2" /></span>
          </div>

          <div class="lp-sec__grid">
            <article v-for="(s, i) in securityTabs" :key="s.id" class="lp-sec__item" data-draw :style="{ '--d': `${i * 0.12}s` }">
              <LandingIcon :name="secIcons[s.id]" class="is-draw" :size="26" :stroke="1.4" />
              <h3>{{ s.label }}</h3>
              <p>{{ s.heading }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- PRICING -->
      <section id="pricing" class="lp-price">
        <div class="lp-container lp-price__grid">
          <header class="lp-head">
            <span class="lp-eyebrow">Стоимость</span>
            <h2 class="lp-h2">Все функции.<br /><span class="lp-grad">{{ daysLabel(trialDays) }} бесплатно.</span></h2>
            <p class="lp-sub">Пробный период — полный доступ ко всем функциям без ограничений по числу портфелей. Дальше — подписка по удобному тарифу.</p>
          </header>
          <div class="lp-price__wrap">
            <div class="lp-price__card">
              <div class="lp-price__top">
                <span class="lp-price__plan">Полный доступ</span>
                <span class="lp-price__badge">Пробный период</span>
              </div>
              <div class="lp-price__amount"><b>0 ₽</b><span>первые {{ daysLabel(trialDays) }}</span></div>
              <ul class="lp-price__list">
                <li v-for="f in priceList" :key="f"><span><LandingIcon name="check" :size="13" :stroke="2.2" /></span>{{ f }}</li>
              </ul>
              <ul v-if="tariffs.length" class="lp-price__tariffs">
                <li v-for="t in tariffs" :key="t.id"><span>{{ t.name }}</span><b>{{ formatPrice(t.price_rub) }} ₽ <small>/ {{ t.period_days }} дн.</small></b></li>
              </ul>
              <router-link to="/login" class="lp-btn lp-btn--dark lp-btn--lg lp-btn--block">
                Попробовать бесплатно <LandingIcon name="arrow" :size="18" :stroke="1.8" />
              </router-link>
            </div>
          </div>
        </div>
      </section>

      <!-- FAQ -->
      <section id="faq" class="lp-faq">
        <div class="lp-container lp-faq__grid">
          <header class="lp-head">
            <span class="lp-eyebrow">Вопросы</span>
            <h2 class="lp-h2">Частые вопросы</h2>
            <p class="lp-sub">Не нашли ответ? <router-link to="/support">Напишите в поддержку</router-link> — отвечаем быстро.</p>
          </header>
          <div class="lp-faq__list" data-reveal>
            <div v-for="(q, i) in faq" :key="i" class="lp-faq__item" :class="{ 'is-open': openFaq === i }">
              <button type="button" :aria-expanded="openFaq === i" @click="openFaq = openFaq === i ? -1 : i">
                <span>{{ q.question }}</span>
                <i class="lp-faq__pm" aria-hidden="true" />
              </button>
              <div class="lp-faq__a"><div><p>{{ q.answer }}</p></div></div>
            </div>
          </div>
        </div>
      </section>

      <!-- FINAL -->
      <section class="lp-final">
        <div class="lp-final__card">
          <div class="lp-final__glow" aria-hidden="true"><i /><i /><i /></div>
          <div class="lp-final__noise" aria-hidden="true" />
          <div class="lp-final__body">
            <span class="lp-eyebrow lp-eyebrow--dark">Начните сегодня</span>
            <h2 class="lp-h2">Ваш капитал<br />заслуживает ясности.</h2>
            <p>Подключение занимает минуту. Первая аналитика — сразу после.</p>
            <div class="lp-final__cta">
              <router-link to="/login" class="lp-btn lp-btn--light lp-btn--xl" @mousemove="magnet" @mouseleave="magnetLeave">
                Начать бесплатно <LandingIcon name="arrow" :size="20" :stroke="1.8" />
              </router-link>
            </div>
            <ul class="lp-final__trust">
              <li><LandingIcon name="lock" :size="15" /> Только чтение</li>
              <li><LandingIcon name="shield" :size="15" /> 152-ФЗ</li>
              <li><LandingIcon name="spark" :size="15" /> Без карты</li>
            </ul>
          </div>
        </div>
      </section>
    </main>

    <footer class="lp-footer">
      <div class="lp-container lp-footer__grid">
        <div class="lp-footer__brand">
          <router-link to="/" class="lp-logo"><img src="/site-logo.webp" alt="" width="26" height="26" />CapitalView</router-link>
          <p>Учёт инвестиций, аналитика портфеля и дивидендный календарь — в одном месте.</p>
        </div>
        <div class="lp-footer__col">
          <b>Продукт</b>
          <a v-for="l in navLinks" :key="l.href" :href="l.href" @click.prevent="go(l.href)">{{ l.t }}</a>
        </div>
        <div class="lp-footer__col">
          <b>Компания</b>
          <router-link to="/support">Поддержка</router-link>
          <router-link to="/privacy">Конфиденциальность</router-link>
          <router-link to="/terms">Условия использования</router-link>
        </div>
      </div>
      <div class="lp-container lp-footer__bottom">
        <span>© {{ new Date().getFullYear() }} CapitalView</span>
        <span>Не является индивидуальной инвестиционной рекомендацией.</span>
      </div>
    </footer>
  </div>
</template>

<style>
/* ===== дизайн-токены и общие элементы лендинга ===== */
.lp {
  --lp-bg: #ffffff;
  --lp-bg-2: #f5f5f7;
  --lp-ink: #0b0d12;
  --lp-ink-2: #3a3f4b;
  --lp-muted: #6b7180;
  --lp-line: rgba(11, 13, 18, 0.08);
  --lp-blue: #3d5afe;
  --lp-violet: #8b5cf6;
  --lp-green: #0f9f63;
  --lp-red: #e5484d;
  --lp-ease: cubic-bezier(.22, 1, .36, 1);
  --lp-display: 'Inter Tight', 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --lp-text: 'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif;
  --lp-max: 1200px;
  --lp-pad: clamp(20px, 4vw, 48px);
  --lp-section: clamp(96px, 13vw, 168px);

  font-family: var(--lp-text);
  color: var(--lp-ink);
  background: var(--lp-bg);
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
  overflow-x: clip;
}
.lp :where(h1, h2, h3, p) { font-size: inherit; font-weight: inherit; color: inherit; margin: 0; }
.lp ::selection { background: rgba(61, 90, 254, .18); }
.lp :where(a) { color: inherit; }
.lp-container { max-width: var(--lp-max); margin: 0 auto; padding: 0 var(--lp-pad); }

.lp-eyebrow {
  display: inline-flex; align-items: center; gap: 8px;
  font-size: 13px; font-weight: 600; letter-spacing: .01em; color: var(--lp-blue);
}
.lp-eyebrow--dark { color: #a5b4ff; }
.lp-h2 {
  font-family: var(--lp-display); font-weight: 600;
  font-size: clamp(34px, 4.6vw, 64px); line-height: 1.04; letter-spacing: -0.042em; color: var(--lp-ink);
}
.lp-dim { color: #a1a6b2; }
.lp-grad {
  background: linear-gradient(100deg, #3d5afe 10%, #8b5cf6 55%, #22b8cf 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  padding-bottom: .06em;
}
.lp-sub { font-size: clamp(16px, 1.3vw, 19px); line-height: 1.6; color: var(--lp-muted); max-width: 560px; }
.lp-sub a { color: var(--lp-blue); text-decoration: none; }
.lp-sub a:hover { text-decoration: underline; }
.lp-head { display: grid; gap: 18px; justify-items: start; }
.lp-head--center { justify-items: center; text-align: center; }
.lp-head--center .lp-sub { margin: 0 auto; }

.lp-btn {
  position: relative; display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  border: 0; border-radius: 999px; font: 500 15px/1 var(--lp-text); text-decoration: none; cursor: pointer;
  white-space: nowrap; transition: background .3s, color .3s, box-shadow .4s var(--lp-ease), transform .4s var(--lp-ease);
}
.lp-btn .lp-icon { transition: transform .4s var(--lp-ease); }
.lp-btn:hover .lp-icon { transform: translateX(3px); }
.lp-btn--sm { height: 36px; padding: 0 16px; font-size: 14px; }
.lp-btn--lg { height: 52px; padding: 0 24px; font-size: 16px; }
.lp-btn--xl { height: 64px; padding: 0 34px; font-size: 18px; }
.lp-btn--block { width: 100%; }
.lp-btn--dark {
  background: var(--lp-ink); color: #fff;
  box-shadow: 0 1px 0 rgba(255,255,255,.12) inset, 0 8px 20px -8px rgba(11,13,18,.5);
}
.lp-btn--dark:hover { background: #22252e; box-shadow: 0 1px 0 rgba(255,255,255,.12) inset, 0 14px 28px -10px rgba(11,13,18,.55); }
.lp-btn--ghost { background: rgba(255,255,255,.7); color: var(--lp-ink); box-shadow: inset 0 0 0 1px rgba(11,13,18,.12); backdrop-filter: blur(10px); }
.lp-btn--ghost:hover { background: #fff; box-shadow: inset 0 0 0 1px rgba(11,13,18,.22); }
.lp-btn--light { background: #fff; color: var(--lp-ink); box-shadow: 0 20px 50px -12px rgba(120,140,255,.55); }
.lp-btn--light:hover { box-shadow: 0 26px 60px -12px rgba(120,140,255,.75); }
.lp-btn:focus-visible { outline: 2px solid var(--lp-blue); outline-offset: 3px; }

.lp-live {
  position: relative; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #12b76a;
}
.lp-live::after {
  content: ''; position: absolute; inset: -4px; border-radius: 50%; border: 1.5px solid #12b76a;
  animation: lp-live 2s var(--lp-ease) infinite;
}
@keyframes lp-live { from { transform: scale(.4); opacity: 1; } to { transform: scale(1.4); opacity: 0; } }

/* ===== header ===== */
.lp-header { position: fixed; inset: 0 0 auto; z-index: 50; transition: background .4s, box-shadow .4s, backdrop-filter .4s; }
.lp-header.is-solid {
  background: rgba(255,255,255,.72);
  backdrop-filter: saturate(1.8) blur(20px); -webkit-backdrop-filter: saturate(1.8) blur(20px);
  box-shadow: 0 1px 0 var(--lp-line);
}
.lp-header__in {
  max-width: calc(var(--lp-max) + var(--lp-pad) * 2); margin: 0 auto; padding: 0 var(--lp-pad);
  height: 64px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 24px;
}
.lp-logo { display: inline-flex; align-items: center; gap: 10px; font: 600 17px var(--lp-display); letter-spacing: -0.02em; color: var(--lp-ink); text-decoration: none; }
.lp-logo img { border-radius: 7px; }
.lp-nav { display: flex; gap: 4px; }
.lp-nav a {
  padding: 8px 14px; border-radius: 99px; font-size: 14px; color: var(--lp-ink-2); text-decoration: none;
  transition: background .25s, color .25s;
}
.lp-nav a:hover { background: rgba(11,13,18,.05); color: var(--lp-ink); }
.lp-header__actions { display: flex; justify-content: flex-end; align-items: center; gap: 8px; }
.lp-header__login { padding: 8px 12px; font-size: 14px; color: var(--lp-ink-2); text-decoration: none; }
.lp-header__login:hover { color: var(--lp-ink); }
.lp-burger { display: none; border: 0; background: none; padding: 6px; color: var(--lp-ink); cursor: pointer; }
.lp-mnav { display: none; }
.lp-header.is-dark .lp-logo { color: #fff; }
.lp-header.is-dark .lp-nav a { color: rgba(255,255,255,.66); }
.lp-header.is-dark .lp-nav a:hover { background: rgba(255,255,255,.08); color: #fff; }
.lp-header.is-dark .lp-header__login { color: rgba(255,255,255,.72); }
.lp-header.is-dark .lp-header__login:hover { color: #fff; }
.lp-header.is-dark .lp-header__actions > .lp-btn--dark { background: #fff; color: var(--lp-ink); box-shadow: 0 0 0 1px rgba(255,255,255,.2), 0 8px 24px -10px rgba(140,160,255,.6); }
.lp-header.is-dark .lp-burger { color: #fff; }
.lp-header.is-dark.is-solid {
  background: rgba(8,9,14,.62);
  box-shadow: 0 1px 0 rgba(255,255,255,.06);
}

/* ===== stats ===== */
.lp-stats { padding: clamp(40px, 6vw, 72px) 0 0; }
.lp-stats__grid { display: grid; grid-template-columns: repeat(4, 1fr); border-top: 1px solid var(--lp-line); }
.lp-stat { padding: 32px 24px 0 0; display: grid; gap: 8px; }
.lp-stat + .lp-stat { padding-left: 24px; border-left: 1px solid var(--lp-line); }
.lp-stat b { font-family: var(--lp-display); font-size: clamp(30px, 3.2vw, 44px); font-weight: 600; letter-spacing: -0.04em; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.lp-stat > span { font-size: 14px; line-height: 1.45; color: var(--lp-muted); max-width: 220px; }

/* ===== manifesto ===== */
.lp-manifesto { padding: var(--lp-section) 0; }
.lp-manifesto__text {
  font-family: var(--lp-display); font-weight: 600;
  font-size: clamp(28px, 4vw, 56px); line-height: 1.16; letter-spacing: -0.035em; color: var(--lp-ink);
  max-width: 1080px;
}
.lp-manifesto__w { display: inline; }

/* ===== builder ===== */
.lp-build { padding: var(--lp-section) 0; background: linear-gradient(180deg, var(--lp-bg) 0%, var(--lp-bg-2) 100%); }
.lp-build__tool { margin-top: 64px; }

/* ===== security ===== */
.lp-sec { position: relative; padding: var(--lp-section) 0; background: #07080b; color: #fff; overflow: hidden; }
.lp-sec::before {
  content: ''; position: absolute; left: 50%; top: 38%; width: 900px; height: 900px; translate: -50% -50%;
  background: radial-gradient(circle, rgba(61,90,254,.22), transparent 60%); pointer-events: none;
}
.lp-sec .lp-h2 { color: #fff; }
.lp-sec .lp-dim { color: #5d6372; }
.lp-radar { position: relative; width: min(420px, 80vw); aspect-ratio: 1; margin: 56px auto 24px; }
.lp-radar__ring {
  position: absolute; inset: calc((var(--n) - 1) * 12.5%); border-radius: 50%;
  border: 1px solid rgba(165,180,255, calc(.28 - var(--n) * .05));
}
.lp-radar__pulse {
  position: absolute; inset: 37.5%; border-radius: 50%; border: 1px solid rgba(165,180,255,.6);
  animation: lp-pulse 4s cubic-bezier(.2,.6,.3,1) infinite;
}
.lp-radar__pulse--2 { animation-delay: 2s; }
@keyframes lp-pulse { from { transform: scale(1); opacity: .9; } to { transform: scale(2.65); opacity: 0; } }
.lp-radar__orbit { position: absolute; inset: 12.5%; border-radius: 50%; animation: lp-spin 14s linear infinite; }
.lp-radar__orbit--2 { inset: 25%; animation-duration: 9s; animation-direction: reverse; }
.lp-radar__orbit i {
  position: absolute; top: -4px; left: 50%; width: 8px; height: 8px; margin-left: -4px; border-radius: 50%;
  background: #a5b4ff; box-shadow: 0 0 16px 4px rgba(120,140,255,.7);
}
@keyframes lp-spin { to { transform: rotate(360deg); } }
.lp-radar__core {
  position: absolute; inset: 37.5%; border-radius: 50%; display: grid; place-items: center; color: #fff;
  background: radial-gradient(circle at 30% 25%, #2a3170, #10132a 70%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.18), 0 0 0 1px rgba(165,180,255,.3), 0 20px 60px -10px rgba(61,90,254,.6);
}
.lp-sec__grid { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 40px; }
.lp-sec__item { padding: 28px 28px 0 0; display: grid; gap: 12px; align-content: start; border-top: 1px solid rgba(255,255,255,.1); }
.lp-sec__item + .lp-sec__item { padding-left: 28px; border-left: 1px solid rgba(255,255,255,.1); }
.lp-sec__item .lp-icon { color: #a5b4ff; }
.lp-sec__item h3 { font-family: var(--lp-display); font-size: 18px; font-weight: 600; letter-spacing: -0.015em; color: #fff; }
.lp-sec__item p { font-size: 14.5px; line-height: 1.55; color: #8d93a1; }

/* ===== pricing ===== */
.lp-price { padding: var(--lp-section) 0; }
.lp-price__grid { display: grid; grid-template-columns: 1fr 1fr; gap: 64px; align-items: center; }
.lp-price__wrap { perspective: 1200px; }
.lp-price__card {
  position: relative; padding: 36px; border-radius: 32px; isolation: isolate;
  background: linear-gradient(180deg, #fff, #fafbff);
  box-shadow: inset 0 1px 0 #fff, 0 1px 2px rgba(11,13,18,.05), 0 40px 80px -30px rgba(61,90,254,.35), 0 0 0 1px var(--lp-line);
}
.lp-price__card::after {
  content: ''; position: absolute; inset: 8% 6% -6%; z-index: -2; border-radius: inherit; pointer-events: none;
  background: conic-gradient(from var(--lp-angle, 0deg), #3d5afe, #8b5cf6, #22b8cf, #ffc2a1, #3d5afe);
  filter: blur(60px); opacity: .32; animation: lp-angle 6s linear infinite;
}
.lp-price__card::before {
  content: ''; position: absolute; inset: -1.5px; border-radius: inherit; z-index: -1; padding: 1.5px;
  background: conic-gradient(from var(--lp-angle, 0deg), #3d5afe, #8b5cf6, #22b8cf, #ffc2a1, #3d5afe);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  animation: lp-angle 6s linear infinite;
}
@property --lp-angle { syntax: '<angle>'; initial-value: 0deg; inherits: false; }
@keyframes lp-angle { to { --lp-angle: 360deg; } }
.lp-price__top { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
.lp-price__plan { font-weight: 600; font-size: 16px; color: var(--lp-ink); }
.lp-price__badge { padding: 5px 11px; border-radius: 99px; font-size: 12px; font-weight: 600; color: var(--lp-blue); background: rgba(61,90,254,.08); }
.lp-price__amount { display: flex; align-items: baseline; gap: 10px; margin: 26px 0 28px; }
.lp-price__amount b { font-family: var(--lp-display); font-size: clamp(64px, 7vw, 96px); font-weight: 600; letter-spacing: -0.06em; line-height: .9; color: var(--lp-ink); }
.lp-price__amount span { font-size: 16px; color: var(--lp-muted); }
.lp-price__list { list-style: none; margin: 0 0 32px; padding: 24px 0 0; border-top: 1px solid var(--lp-line); display: grid; gap: 14px; }
.lp-price__list li { display: flex; align-items: center; gap: 12px; font-size: 15px; color: var(--lp-ink-2); }
.lp-price__tariffs { list-style: none; margin: -12px 0 28px; padding: 0; display: grid; gap: 8px; }
.lp-price__tariffs li { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; padding: 12px 16px; border-radius: 14px; background: rgba(11,13,18,.035); font-size: 14px; color: var(--lp-ink-2); }
.lp-price__tariffs b { font-weight: 600; color: var(--lp-ink); font-variant-numeric: tabular-nums; white-space: nowrap; }
.lp-price__tariffs small { font-weight: 400; color: var(--lp-muted); }
.lp-price__list li span { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; background: rgba(15,159,99,.1); color: var(--lp-green); flex: none; }

/* ===== faq ===== */
.lp-faq { padding: var(--lp-section) 0; background: var(--lp-bg-2); }
.lp-faq__grid { display: grid; grid-template-columns: 1fr 1.5fr; gap: 64px; align-items: start; }
.lp-faq__grid .lp-head { position: sticky; top: 120px; }
.lp-faq__item {
  margin-bottom: 10px; padding: 0 24px; border-radius: 20px;
  background: linear-gradient(180deg, #fff, #fbfbfd);
  box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(11,13,18,.05), 0 8px 20px -14px rgba(30,40,90,.18);
  transition: box-shadow .5s var(--lp-ease), transform .5s var(--lp-ease);
}
.lp-faq__item:hover { box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(61,90,254,.16), 0 14px 30px -16px rgba(30,40,90,.25); }
.lp-faq__item.is-open { box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(61,90,254,.2), 0 24px 50px -24px rgba(61,90,254,.35); }
.lp-faq__item button {
  width: 100%; display: flex; justify-content: space-between; align-items: center; gap: 24px;
  padding: 24px 0; border: 0; background: none; text-align: left; cursor: pointer;
  font: 500 17px/1.4 var(--lp-text); color: var(--lp-ink);
}
.lp-faq__item button:hover span { color: var(--lp-blue); }
.lp-faq__item button span { transition: color .25s; }
.lp-faq__pm { position: relative; width: 28px; height: 28px; flex: none; border-radius: 50%; background: #fff; box-shadow: 0 0 0 1px var(--lp-line); transition: background .3s, transform .5s var(--lp-ease); }
.lp-faq__pm::before, .lp-faq__pm::after {
  content: ''; position: absolute; left: 50%; top: 50%; width: 11px; height: 1.5px; margin: -.75px 0 0 -5.5px; border-radius: 2px;
  background: var(--lp-ink); transition: transform .5s var(--lp-ease), background .3s;
}
.lp-faq__pm::after { transform: rotate(90deg); }
.lp-faq__item.is-open .lp-faq__pm { background: var(--lp-ink); transform: rotate(180deg); }
.lp-faq__item.is-open .lp-faq__pm::before, .lp-faq__item.is-open .lp-faq__pm::after { background: #fff; }
.lp-faq__item.is-open .lp-faq__pm::after { transform: rotate(0deg); }
.lp-faq__a { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .55s var(--lp-ease); }
.lp-faq__a > div { overflow: hidden; }
.lp-faq__a p { padding: 0 48px 24px 0; font-size: 15.5px; line-height: 1.65; color: var(--lp-muted); opacity: 0; transform: translateY(-6px); transition: opacity .4s, transform .5s var(--lp-ease); }
.lp-faq__item.is-open .lp-faq__a { grid-template-rows: 1fr; }
.lp-faq__item.is-open .lp-faq__a p { opacity: 1; transform: none; transition-delay: .1s; }

/* ===== final ===== */
.lp-final { padding: var(--lp-section) var(--lp-pad) 40px; }
.lp-final__card {
  position: relative; overflow: hidden; isolation: isolate; max-width: 1360px; margin: 0 auto;
  border-radius: 32px; background: #07080b; color: #fff;
  padding: clamp(80px, 12vw, 160px) var(--lp-pad);
}
.lp-final__glow { position: absolute; inset: 0; z-index: -2; filter: blur(80px); opacity: .8; }
.lp-final__glow i { position: absolute; border-radius: 50%; mix-blend-mode: screen; }
.lp-final__glow i:nth-child(1) { width: 55%; aspect-ratio: 1; left: -10%; bottom: -62%; background: #3d5afe; animation: lp-drift 16s ease-in-out infinite alternate; }
.lp-final__glow i:nth-child(2) { width: 45%; aspect-ratio: 1; right: -8%; bottom: -58%; background: #8b5cf6; animation: lp-drift 19s ease-in-out infinite alternate-reverse; }
.lp-final__glow i:nth-child(3) { width: 30%; aspect-ratio: 1; left: 38%; bottom: -42%; background: #22b8cf; opacity: .7; animation: lp-drift 13s ease-in-out infinite alternate; }
@keyframes lp-drift { to { transform: translate(8%, -12%) scale(1.15); } }
.lp-final__noise {
  position: absolute; inset: 0; z-index: -1; opacity: .18; mix-blend-mode: overlay; pointer-events: none;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
}
.lp-final__body { display: grid; justify-items: center; text-align: center; gap: 22px; }
.lp-final .lp-h2 { color: #fff; font-size: clamp(40px, 6.4vw, 92px); }
.lp-final__body > p { font-size: clamp(16px, 1.4vw, 20px); color: rgba(255,255,255,.65); }
.lp-final__cta { margin-top: 18px; }
.lp-final__trust { display: flex; flex-wrap: wrap; justify-content: center; gap: 10px 24px; margin: 10px 0 0; padding: 0; list-style: none; }
.lp-final__trust li { display: flex; align-items: center; gap: 7px; font-size: 13.5px; color: rgba(255,255,255,.6); }

/* ===== footer ===== */
.lp-footer { padding: 56px 0 40px; }
.lp-footer__grid { display: grid; grid-template-columns: 2fr 1fr 1fr; gap: 40px; }
.lp-footer__brand p { margin-top: 14px; max-width: 340px; font-size: 14px; line-height: 1.6; color: var(--lp-muted); }
.lp-footer__col { display: grid; gap: 10px; align-content: start; }
.lp-footer__col b { font-size: 13px; font-weight: 600; color: var(--lp-ink); margin-bottom: 4px; }
.lp-footer__col a { font-size: 14px; color: var(--lp-muted); text-decoration: none; transition: color .2s; }
.lp-footer__col a:hover { color: var(--lp-ink); }
.lp-footer__bottom { display: flex; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--lp-line); font-size: 12.5px; color: var(--lp-muted); }

/* ===== адаптив ===== */
@media (max-width: 1023px) {
  .lp-nav { display: none; }
  .lp-header__in { grid-template-columns: 1fr auto; }
  .lp-stats__grid { grid-template-columns: repeat(2, 1fr); }
  .lp-stat:nth-child(3) { padding-left: 0; border-left: 0; }
  .lp-stat { padding-bottom: 8px; }
  .lp-sec__grid { grid-template-columns: repeat(2, 1fr); }
  .lp-sec__item:nth-child(3) { padding-left: 0; border-left: 0; }
  .lp-sec__item { padding-bottom: 28px; }
  .lp-price__grid, .lp-faq__grid { grid-template-columns: 1fr; gap: 48px; }
  .lp-faq__grid .lp-head { position: static; }
}
@media (max-width: 680px) {
  .lp-header__login, .lp-header__actions > .lp-btn { display: none; }
  .lp-burger { display: block; }
  .lp-header.is-open { background: rgba(255,255,255,.96); }
  .lp-mnav {
    display: grid; gap: 4px; padding: 0 var(--lp-pad); max-height: 0; overflow: hidden;
    transition: max-height .6s var(--lp-ease), padding .6s var(--lp-ease);
  }
  .lp-header.is-open .lp-mnav { max-height: 520px; padding-bottom: 24px; }
  .lp-mnav a:not(.lp-btn) {
    display: flex; justify-content: space-between; align-items: center; padding: 16px 0;
    font: 600 22px var(--lp-display); letter-spacing: -0.02em; color: var(--lp-ink); text-decoration: none;
    border-bottom: 1px solid var(--lp-line);
  }
  .lp-mnav .lp-btn { margin-top: 16px; }
  .lp-stats__grid { grid-template-columns: 1fr 1fr; }
  .lp-stat { padding: 22px 12px 4px 0; }
  .lp-stat + .lp-stat { padding-left: 12px; }
  .lp-stat:nth-child(3) { padding-left: 0; }
  .lp-stat > span { font-size: 13px; }
  .lp-sec__grid { grid-template-columns: 1fr; }
  .lp-sec__item, .lp-sec__item + .lp-sec__item { padding: 24px 0; border-left: 0; }
  .lp-build__tool { margin-top: 40px; }
  .lp-price__card { padding: 26px; border-radius: 26px; }
  .lp-faq__item button { font-size: 16px; padding: 20px 0; }
  .lp-faq__a p { padding-right: 0; }
  .lp-final { padding-left: 12px; padding-right: 12px; }
  .lp-final__card { border-radius: 26px; }
  .lp-footer__grid { grid-template-columns: 1fr 1fr; }
  .lp-footer__brand { grid-column: 1 / -1; }
}
@media (prefers-reduced-motion: reduce) {
  .lp *, .lp *::before, .lp *::after { animation: none !important; transition-duration: .01ms !important; }
}
</style>
