<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { Draggable } from 'gsap/Draggable'
import { InertiaPlugin } from 'gsap/InertiaPlugin'
import { ArrowRight, ArrowUpRight, Lock, ShieldCheck, Zap, Eye } from 'lucide-vue-next'
import LandingFlow from './LandingFlow.vue'
import LandingRebalancer from './LandingRebalancer.vue'
import { useSmoothScroll, useLandingFonts, formatRub, prefersReducedMotion } from './useLandingMotion'
import { securityTabs, pricingFeatures, faq } from '../../content/landingData'

gsap.registerPlugin(ScrollTrigger, Draggable, InertiaPlugin)
useLandingFonts('https://fonts.googleapis.com/css2?family=Inter+Tight:wght@200..900&family=JetBrains+Mono:wght@400;500;600&display=swap')
const { scrollTo } = useSmoothScroll()

/* ---------- hero: перетаскиваемые кристаллы ---------- */
const assets = [
  { id: 'btc', name: 'Bitcoin', cls: 'Крипто', value: 420000, img: '/landing/hero-blocks/0.webp', x: 4, y: 14, r: -12 },
  { id: 'eth', name: 'Ethereum', cls: 'Крипто', value: 180000, img: '/landing/hero-blocks/1.webp', x: 33, y: 2, r: 8 },
  { id: 'usd', name: 'Доллар', cls: 'Валюта', value: 250000, img: '/landing/hero-blocks/2.webp', x: 63, y: 6, r: -6 },
  { id: 'luk', name: 'Лукойл', cls: 'Акции', value: 310000, img: '/landing/hero-blocks/3.webp', x: 86, y: 18, r: 10 },
  { id: 'sber', name: 'Сбербанк', cls: 'Акции', value: 220000, img: '/landing/hero-blocks/4.webp', x: 18, y: 50, r: 6 },
  { id: 'home', name: 'Квартира', cls: 'Недвижимость', value: 1900000, img: '/landing/hero-blocks/5.webp', x: 52, y: 44, r: -8 }
]
const CLASS_COLORS = { 'Акции': '#2f5bff', 'Валюта': '#c8f560', 'Крипто': '#ff8a5c', 'Недвижимость': '#111111' }
const holdings = reactive({ 'Акции': 600000, 'Валюта': 400000, 'Крипто': 250000, 'Недвижимость': 0 })
const log = ref([])
const hot = ref(false)
const drops = ref(0)
const total = computed(() => Object.values(holdings).reduce((a, b) => a + b, 0))
const shownTotal = reactive({ v: 1250000 })
const C = 2 * Math.PI * 42
const donut = computed(() => {
  let off = 0
  return Object.entries(holdings).map(([k, v]) => {
    const len = (v / total.value) * C
    const s = { k, c: CLASS_COLORS[k], dash: `${Math.max(len - 3, 0)} ${C}`, off: -off, pct: Math.round((v / total.value) * 100) }
    off += len
    return s
  })
})

const heroRef = ref(null)
const dropRef = ref(null)
const crystalEls = ref([])
let drags = []

function absorb(i) {
  const el = crystalEls.value[i]
  const d = drags[i]
  if (!el || el.dataset.busy) return
  el.dataset.busy = '1'
  d.tween?.kill?.()
  d.disable()
  hot.value = false
  const a = assets[i]
  const er = el.getBoundingClientRect()
  const dr = dropRef.value.getBoundingClientRect()
  const dx = dr.left + dr.width * 0.28 - (er.left + er.width / 2)
  const dy = dr.top + dr.height * 0.42 - (er.top + er.height / 2)
  gsap.to(el, {
    x: `+=${dx}`, y: `+=${dy}`, scale: 0.15, rotation: '+=180', opacity: 0, duration: 0.55, ease: 'power3.in',
    onComplete() {
      holdings[a.cls] += a.value
      drops.value++
      log.value = [{ id: Date.now(), text: `+ ${a.name}`, v: formatRub(a.value) }, ...log.value].slice(0, 3)
      gsap.to(shownTotal, { v: total.value, duration: 1.2, ease: 'power3.out' })
      gsap.fromTo(dropRef.value, { scale: 1.04 }, { scale: 1, duration: 0.8, ease: 'elastic.out(1, 0.4)' })
      gsap.delayedCall(1.3, () => {
        gsap.set(el, { x: 0, y: 0, rotation: 0 })
        gsap.fromTo(el, { scale: 0, opacity: 0 }, {
          scale: 1, opacity: 1, duration: 0.9, ease: 'elastic.out(1, 0.5)',
          onComplete() { delete el.dataset.busy; d.enable(); d.update() }
        })
      })
    }
  })
}

function initCrystals() {
  drags = crystalEls.value.map((el, i) =>
    Draggable.create(el, {
      type: 'x,y',
      bounds: heroRef.value,
      inertia: true,
      edgeResistance: 0.7,
      zIndexBoost: true,
      onPress() { gsap.to(el, { scale: 1.12, duration: 0.3 }) },
      onRelease() { gsap.to(el, { scale: 1, duration: 0.4 }) },
      onDrag() { hot.value = this.hitTest(dropRef.value, '25%') },
      onDragEnd() { if (this.hitTest(dropRef.value, '25%')) absorb(i); else hot.value = false },
      onThrowUpdate() { if (this.hitTest(dropRef.value, '35%')) absorb(i) }
    })[0]
  )
}

/* ---------- заголовок с «живым» весом шрифта ---------- */
const titleLines = ['Капитал', 'под контролем']
const charEls = []
let weightSetters = []
function setChar(el) { if (el && !charEls.includes(el)) charEls.push(el) }
function onHeroMove(e) {
  bg?.setPointer(e.clientX, e.clientY)
  if (!weightSetters.length) return
  charEls.forEach((el, i) => {
    const r = el.getBoundingClientRect()
    const d = Math.hypot(e.clientX - (r.left + r.width / 2), e.clientY - (r.top + r.height / 2))
    weightSetters[i](850 - 650 * Math.max(0, 1 - d / 260))
  })
}
function onHeroLeave() {
  bg?.clearPointer()
  weightSetters.forEach((s) => s(850))
}

/* ---------- прочее ---------- */
const features = [
  { n: '01', t: 'Реальная доходность', d: 'XIRR с учётом комиссий, налогов и пополнений. Без самообмана.', kind: 'spark', tone: 'ink' },
  { n: '02', t: 'Дивидендный календарь', d: 'Все будущие выплаты и купоны — по дням и месяцам.', kind: 'cal', tone: 'blue' },
  { n: '03', t: 'Структура портфеля', d: 'Классы, секторы и валюты. Видно перекосы сразу.', kind: 'bars', tone: 'lime' },
  { n: '04', t: 'Сделки автоматически', d: 'Импорт истории из брокера — ничего не нужно вводить руками.', kind: 'rows', tone: 'paper' },
  { n: '05', t: 'Любые активы', d: 'Недвижимость, вклады, крипта — добавьте вручную за секунду.', kind: 'crystal', tone: 'ink' },
  { n: '06', t: 'Несколько портфелей', d: 'ИИС, брокерский, семейный — отдельно и вместе.', kind: 'stack', tone: 'blue' }
]
const calMonths = ['Я', 'Ф', 'М', 'А', 'М', 'И', 'И', 'А', 'С', 'О', 'Н', 'Д']
const calHits = [1, 0, 2, 1, 1, 3, 3, 1, 0, 2, 1, 2]
const secIcons = { Lock, ShieldCheck, Zap, Eye }
const openFaq = ref(0)
const headerSolid = ref(false)

const bgCanvas = ref(null)
const rootRef = ref(null)
const hTrack = ref(null)
let bg = null
let ctx = null
let mm = null

function magnet(e) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  gsap.to(el, { x: (e.clientX - r.left - r.width / 2) * 0.3, y: (e.clientY - r.top - r.height / 2) * 0.4, duration: 0.4 })
}
function magnetLeave(e) { gsap.to(e.currentTarget, { x: 0, y: 0, duration: 0.8, ease: 'elastic.out(1, 0.4)' }) }
function onResize() { bg?.resize() }
function onScroll() {
  headerSolid.value = window.scrollY > 40
  if (bg) bg.uniforms.uScroll.value = Math.min(window.scrollY / document.body.scrollHeight, 1)
}

onMounted(async () => {
  await nextTick()
  const reduced = prefersReducedMotion()
  // фон грузится отдельным чанком (three.js), чтобы не задерживать первый рендер
  import('./fluidBg')
    .then(({ createFluidBg }) => {
      if (!bgCanvas.value) return
      bg = createFluidBg(bgCanvas.value)
      bg.start()
    })
    .catch(() => { bg = null })
  window.addEventListener('resize', onResize)
  window.addEventListener('scroll', onScroll, { passive: true })
  initCrystals()

  ctx = gsap.context(() => {
    weightSetters = charEls.map((el) => gsap.quickTo(el, 'fontWeight', { duration: 0.6, ease: 'power3.out' }))

    if (!reduced) {
      gsap.from(charEls, { yPercent: 110, rotate: 6, duration: 1.1, ease: 'expo.out', stagger: 0.035, delay: 0.1 })
      gsap.from('.pb-hero__meta > *, .pb-hero__bottom > *', { y: 30, opacity: 0, duration: 0.9, ease: 'power3.out', stagger: 0.08, delay: 0.5 })
      gsap.from('.pb-crystal', { scale: 0, opacity: 0, duration: 1.1, ease: 'elastic.out(1, 0.55)', stagger: 0.08, delay: 0.7 })
      gsap.utils.toArray('.pb-crystal__float').forEach((el, i) => {
        gsap.to(el, { y: i % 2 ? 14 : -14, rotation: i % 2 ? 4 : -4, duration: 2.4 + i * 0.3, ease: 'sine.inOut', repeat: -1, yoyo: true })
      })
    }

    mm = gsap.matchMedia()
    mm.add('(hover: none)', () => {
      // на тач-экранах «дышит» сам заголовок
      const tl = gsap.timeline({ repeat: -1, yoyo: true, delay: 1.4 })
      tl.to(charEls, { fontWeight: 250, duration: 0.9, ease: 'sine.inOut', stagger: { each: 0.07, from: 'start' } })
      return () => tl.kill()
    })

    // параллакс кристаллов при уходе из hero
    gsap.to('.pb-crystals', {
      yPercent: -30, ease: 'none',
      scrollTrigger: { trigger: heroRef.value, start: 'top top', end: 'bottom top', scrub: true }
    })

    // marquee, реагирующий на скорость скролла
    const rows = gsap.utils.toArray('.pb-marquee__row')
    const loops = rows.map((row, i) =>
      gsap.to(row, { xPercent: i ? 0 : -50, startAt: { xPercent: i ? -50 : 0 }, duration: 26, ease: 'none', repeat: -1 })
    )
    let skew = gsap.quickTo('.pb-marquee', 'skewY', { duration: 0.4 })
    ScrollTrigger.create({
      trigger: '.pb-marquee', start: 'top bottom', end: 'bottom top',
      onUpdate(self) {
        const v = self.getVelocity()
        loops.forEach((l) => gsap.to(l, { timeScale: (self.direction) * (1 + Math.min(Math.abs(v) / 300, 6)), duration: 0.3, overwrite: true }))
        skew(gsap.utils.clamp(-4, 4, v / -400))
        gsap.delayedCall(0.2, () => skew(0))
      }
    })

    // горизонтальная лента возможностей
    const track = hTrack.value
    const distance = () => track.scrollWidth - window.innerWidth
    const hTween = gsap.to(track, {
      x: () => -distance(), ease: 'none',
      scrollTrigger: {
        trigger: '.pb-hscroll', start: 'top top', end: () => `+=${distance()}`,
        pin: true, scrub: 0.8, invalidateOnRefresh: true
      }
    })
    gsap.utils.toArray('.pb-fcard').forEach((card) => {
      gsap.from(card.querySelector('.pb-fcard__viz'), {
        scale: 0.6, rotation: -8, opacity: 0, ease: 'back.out(1.6)',
        scrollTrigger: { trigger: card, containerAnimation: hTween, start: 'left 85%', end: 'left 45%', scrub: true }
      })
    })

    // общие reveal-ы
    gsap.utils.toArray('[data-reveal]').forEach((el) => {
      gsap.from(el, { y: 60, opacity: 0, duration: 1, ease: 'power3.out', scrollTrigger: { trigger: el, start: 'top 85%' } })
    })
    gsap.utils.toArray('.pb-split').forEach((el) => {
      gsap.from(el.querySelectorAll('.pb-split__w > span'), {
        yPercent: 110, duration: 1, ease: 'expo.out', stagger: 0.04,
        scrollTrigger: { trigger: el, start: 'top 85%' }
      })
    })

    // «0 ₽» заливается по скроллу
    gsap.fromTo('.pb-price__zero', { backgroundSize: '0% 100%' }, {
      backgroundSize: '100% 100%', ease: 'none',
      scrollTrigger: { trigger: '.pb-price', start: 'top 70%', end: 'center 45%', scrub: true }
    })

    // финальный блок раскрывается из скруглённой карточки
    gsap.fromTo('.pb-final__card', { clipPath: 'inset(12% 8% 12% 8% round 48px)' }, {
      clipPath: 'inset(0% 0% 0% 0% round 0px)', ease: 'none',
      scrollTrigger: { trigger: '.pb-final', start: 'top 85%', end: 'top 15%', scrub: true }
    })
  }, rootRef.value)

  document.fonts?.ready.then(() => ScrollTrigger.refresh())
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  window.removeEventListener('scroll', onScroll)
  drags.forEach((d) => d.kill())
  mm?.revert()
  ctx?.revert()
  bg?.dispose()
})

function words(text) { return text.split(' ') }
</script>

<template>
  <div ref="rootRef" class="pb">
    <canvas ref="bgCanvas" class="pb-bg" aria-hidden="true" />

    <header class="pb-header" :class="{ 'is-solid': headerSolid }">
      <router-link to="/" class="pb-logo"><img src="/site-logo.webp" alt="" width="24" height="24" />CapitalView</router-link>
      <nav class="pb-nav">
        <a href="#flow" @click.prevent="scrollTo('#flow')">Как работает</a>
        <a href="#features" @click.prevent="scrollTo('#features')">Возможности</a>
        <a href="#build" @click.prevent="scrollTo('#build')">Конструктор</a>
        <a href="#faq" @click.prevent="scrollTo('#faq')">FAQ</a>
      </nav>
      <div class="pb-header__actions">
        <router-link to="/login" class="pb-link">Войти</router-link>
        <router-link to="/login" class="pb-btn pb-btn--sm">Начать <ArrowUpRight :size="16" /></router-link>
      </div>
    </header>

    <main>
      <!-- HERO -->
      <section ref="heroRef" class="pb-hero" @pointermove="onHeroMove" @pointerleave="onHeroLeave">
        <div class="pb-hero__meta">
          <span class="pb-mono">[ 001 ] Учёт инвестиций</span>
          <span class="pb-mono pb-hide-m">Т-Инвестиции · ручной ввод · кастомные активы</span>
          <span class="pb-mono pb-tag">✦ Бесплатно</span>
        </div>

        <h1 class="pb-hero__title" aria-label="Капитал под контролем">
          <span v-for="(line, li) in titleLines" :key="li" class="pb-hero__line">
            <template v-for="(w, wi) in line.split(' ')" :key="wi">
              <span v-if="wi" class="pb-hero__mask is-sp">&nbsp;</span>
              <span class="pb-hero__word">
                <span v-for="(ch, ci) in w" :key="ci" class="pb-hero__mask"><span :ref="setChar" class="pb-hero__char">{{ ch }}</span></span>
              </span>
            </template>
          </span>
        </h1>

        <div class="pb-crystals">
          <div
            v-for="(a, i) in assets"
            :key="a.id"
            :ref="(el) => (crystalEls[i] = el)"
            class="pb-crystal"
            :style="{ left: a.x + '%', top: a.y + '%' }"
            :title="`Перетащите ${a.name} в портфель`"
          >
            <div class="pb-crystal__float" :style="{ rotate: a.r + 'deg' }">
              <img :src="a.img" :alt="a.name" draggable="false" />
              <span class="pb-crystal__tag">{{ a.name }}</span>
            </div>
          </div>
        </div>

        <div class="pb-hero__bottom">
          <div class="pb-hero__lead">
            <p>Все брокерские счета, сделки и дивиденды — на одном живом дашборде. Подключение за минуту, доступ только на чтение.</p>
            <div class="pb-hero__cta">
              <router-link to="/login" class="pb-btn pb-btn--lg" @mousemove="magnet" @mouseleave="magnetLeave">
                Создать аккаунт <ArrowRight :size="18" />
              </router-link>
              <span class="pb-hint">
                <svg width="38" height="22" viewBox="0 0 38 22" fill="none"><path d="M1 4c10 14 24 16 34 8m0 0-6-1m6 1-1 6" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" /></svg>
                {{ drops ? 'Ещё! Кидайте всё ✦' : 'Перетащите кристалл в портфель' }}
              </span>
            </div>
          </div>

          <div ref="dropRef" class="pb-drop" :class="{ 'is-hot': hot }">
            <div class="pb-drop__head">
              <span class="pb-mono">Мой портфель</span>
              <span class="pb-live"><i />live</span>
            </div>
            <div class="pb-drop__body">
              <svg viewBox="0 0 100 100" class="pb-drop__donut">
                <circle cx="50" cy="50" r="42" fill="none" stroke="#ece8df" stroke-width="12" />
                <circle
                  v-for="s in donut"
                  :key="s.k"
                  cx="50" cy="50" r="42" fill="none" stroke-width="12"
                  :stroke="s.c" :stroke-dasharray="s.dash" :stroke-dashoffset="s.off"
                  class="pb-drop__seg"
                />
              </svg>
              <div class="pb-drop__info">
                <b class="pb-drop__total">{{ formatRub(shownTotal.v) }}</b>
                <ul>
                  <li v-for="s in donut" :key="s.k" :class="{ 'is-zero': !s.pct }"><i :style="{ background: s.c }" />{{ s.k }}<em>{{ s.pct }}%</em></li>
                </ul>
              </div>
            </div>
            <TransitionGroup name="pb-log" tag="ul" class="pb-drop__log">
              <li v-for="l in log" :key="l.id"><span>{{ l.text }}</span><b>{{ l.v }}</b></li>
            </TransitionGroup>
            <div class="pb-drop__zone">Бросьте сюда</div>
          </div>
        </div>
      </section>

      <!-- MARQUEE -->
      <section class="pb-marquee" aria-hidden="true">
        <div class="pb-marquee__row"><span v-for="n in 2" :key="n">Акции ✦ Облигации ✦ Фонды ✦ Дивиденды ✦ Купоны ✦ Валюта ✦ Крипта ✦ Недвижимость ✦&nbsp;</span></div>
        <div class="pb-marquee__row pb-marquee__row--solid"><span v-for="n in 2" :key="n">Один экран — весь капитал → Один экран — весь капитал →&nbsp;</span></div>
      </section>

      <!-- FLOW -->
      <LandingFlow />

      <!-- HORIZONTAL FEATURES -->
      <section id="features" class="pb-hscroll">
        <div ref="hTrack" class="pb-hscroll__track">
          <div class="pb-hscroll__intro">
            <span class="pb-mono">[ 003 ] Возможности</span>
            <h2 class="pb-h2">Всё, что нужно инвестору.<br /><span class="pb-dim">Ничего лишнего.</span></h2>
            <span class="pb-mono pb-scrollhint">Листайте →</span>
          </div>
          <article v-for="f in features" :key="f.n" class="pb-fcard" :class="`pb-fcard--${f.tone}`">
            <div class="pb-fcard__top">
              <span class="pb-mono">{{ f.n }}</span>
              <ArrowUpRight :size="22" />
            </div>
            <div class="pb-fcard__viz">
              <svg v-if="f.kind === 'spark'" viewBox="0 0 200 80" class="pb-viz-spark">
                <path d="M0,70 L20,62 L40,66 L60,48 L80,52 L100,36 L120,40 L140,24 L160,28 L180,12 L200,6" />
                <circle cx="200" cy="6" r="5" />
              </svg>
              <div v-else-if="f.kind === 'cal'" class="pb-viz-cal">
                <span v-for="(m, i) in calMonths" :key="i"><b>{{ m }}</b><i v-for="k in calHits[i]" :key="k" /></span>
              </div>
              <div v-else-if="f.kind === 'bars'" class="pb-viz-bars">
                <i style="flex: 42; background: #111" /><i style="flex: 26; background: #2f5bff" /><i style="flex: 14; background: #fff" /><i style="flex: 18; background: #ff8a5c" />
              </div>
              <ul v-else-if="f.kind === 'rows'" class="pb-viz-rows">
                <li><b>SBER</b><span>+ 20 шт</span></li>
                <li><b>LKOH</b><span>дивиденд</span></li>
                <li><b>ОФЗ</b><span>купон</span></li>
              </ul>
              <div v-else-if="f.kind === 'crystal'" class="pb-viz-crystal">
                <img src="/landing/hero-blocks/5.webp" alt="" /><img src="/landing/hero-blocks/0.webp" alt="" />
              </div>
              <div v-else class="pb-viz-stack"><i /><i /><i /></div>
            </div>
            <h3>{{ f.t }}</h3>
            <p>{{ f.d }}</p>
          </article>
        </div>
      </section>

      <!-- REBALANCER -->
      <section id="build" class="pb-section">
        <div class="pb-container">
          <div class="pb-section__head">
            <span class="pb-mono">[ 004 ] Конструктор</span>
            <h2 class="pb-h2 pb-split">
              <span v-for="(w, i) in words('Соберите портфель мечты')" :key="i" class="pb-split__w"><span>{{ w }}&nbsp;</span></span>
            </h2>
            <p class="pb-sub">Двигайте ползунки — посмотрите, как меняются риск и ожидаемая доходность. В CapitalView то же самое, но на ваших реальных данных.</p>
          </div>
          <LandingRebalancer data-reveal />
        </div>
      </section>

      <!-- SECURITY -->
      <section class="pb-section">
        <div class="pb-container">
          <div class="pb-section__head">
            <span class="pb-mono">[ 005 ] Безопасность</span>
            <h2 class="pb-h2 pb-split">
              <span v-for="(w, i) in words('Только чтение. Ни одной сделки без вас.')" :key="i" class="pb-split__w"><span>{{ w }}&nbsp;</span></span>
            </h2>
          </div>
          <div class="pb-sec">
            <article v-for="(s, i) in securityTabs" :key="s.id" class="pb-sec__card" data-reveal>
              <span class="pb-mono">0{{ i + 1 }}</span>
              <component :is="secIcons[s.icon]" :size="34" :stroke-width="1.6" class="pb-sec__icon" />
              <h3>{{ s.label }}</h3>
              <p>{{ s.heading }}</p>
            </article>
          </div>
        </div>
      </section>

      <!-- PRICE -->
      <section class="pb-section pb-price">
        <div class="pb-container">
          <span class="pb-mono">[ 006 ] Стоимость</span>
          <div class="pb-price__zero">0&nbsp;₽</div>
          <div class="pb-price__row">
            <p>Сервис временно полностью бесплатный. Все функции — без ограничений.</p>
            <ul><li v-for="f in pricingFeatures" :key="f">✦ {{ f }}</li></ul>
          </div>
        </div>
      </section>

      <!-- FAQ -->
      <section id="faq" class="pb-section">
        <div class="pb-container pb-faq">
          <div>
            <span class="pb-mono">[ 007 ] FAQ</span>
            <h2 class="pb-h2">Частые<br />вопросы</h2>
          </div>
          <div>
            <div v-for="(q, i) in faq" :key="i" class="pb-faq__item" :class="{ 'is-open': openFaq === i }">
              <button type="button" class="pb-faq__q" @click="openFaq = openFaq === i ? -1 : i">
                <span class="pb-mono">0{{ i + 1 }}</span>{{ q.question }}<span class="pb-faq__plus" />
              </button>
              <div class="pb-faq__a"><div><p>{{ q.answer }}</p></div></div>
            </div>
          </div>
        </div>
      </section>

      <!-- FINAL -->
      <section class="pb-final">
        <div class="pb-final__card">
          <div class="pb-final__orbit" aria-hidden="true">
            <img v-for="(a, i) in assets" :key="a.id" :src="a.img" alt="" :style="{ '--i': i }" />
          </div>
          <h2 class="pb-final__title">Начните<br />сегодня</h2>
          <p>Подключение за минуту. Бесплатно.</p>
          <router-link to="/login" class="pb-btn pb-btn--lime pb-btn--lg" @mousemove="magnet" @mouseleave="magnetLeave">
            Создать аккаунт <ArrowRight :size="18" />
          </router-link>
        </div>
      </section>
    </main>

    <footer class="pb-footer">
      <span>© 2026 CapitalView</span>
      <router-link to="/privacy">Конфиденциальность</router-link>
      <router-link to="/terms">Условия</router-link>
    </footer>
  </div>
</template>

<style scoped>
.pb {
  --ink: #111111;
  --paper: #f3f0e9;
  --blue: #2f5bff;
  --lime: #c8f560;
  --mut: #6f6b63;
  position: relative;
  min-height: 100vh;
  color: var(--ink);
  font-family: 'Inter Tight', 'Manrope', sans-serif;
  background: var(--paper);
  overflow-x: clip;
}
.pb :deep(.pb-mono) { font: 500 12px / 1.3 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.04em; color: var(--mut); }
.pb-bg { position: fixed; inset: 0; width: 100%; height: 100%; z-index: 0; display: block; }
main, .pb-footer { position: relative; z-index: 1; }

/* header */
.pb-header {
  position: fixed; top: 0; left: 0; right: 0; z-index: 50;
  display: flex; align-items: center; gap: 24px;
  padding: 16px clamp(16px, 4vw, 56px);
  transition: background 0.4s, backdrop-filter 0.4s, padding 0.4s;
}
.pb-header.is-solid { background: rgba(243, 240, 233, 0.72); backdrop-filter: blur(14px); padding-top: 10px; padding-bottom: 10px; }
.pb-logo { display: flex; align-items: center; gap: 8px; font-weight: 800; font-size: 18px; letter-spacing: -0.02em; color: var(--ink); text-decoration: none; }
.pb-nav { display: flex; gap: 28px; margin: 0 auto; }
.pb-nav a { color: var(--ink); text-decoration: none; font-weight: 500; font-size: 15px; position: relative; }
.pb-nav a::after { content: ''; position: absolute; left: 0; right: 0; bottom: -4px; height: 1.5px; background: var(--ink); transform: scaleX(0); transform-origin: right; transition: transform 0.4s; }
.pb-nav a:hover::after { transform: scaleX(1); transform-origin: left; }
.pb-header__actions { display: flex; align-items: center; gap: 16px; }
.pb-link { color: var(--ink); text-decoration: none; font-weight: 600; }

.pb-btn {
  display: inline-flex; align-items: center; gap: 10px;
  background: var(--ink); color: #fff; text-decoration: none;
  padding: 14px 24px; border-radius: 999px; font-weight: 700; font-size: 16px;
  transition: background 0.3s, color 0.3s, box-shadow 0.3s;
  will-change: transform;
}
.pb-btn:hover { background: var(--blue); box-shadow: 0 16px 40px -14px rgba(47, 91, 255, 0.7); }
.pb-btn--sm { padding: 10px 18px; font-size: 14px; }
.pb-btn--lg { padding: 20px 32px; font-size: 18px; }
.pb-btn--lime { background: var(--lime); color: var(--ink); }
.pb-btn--lime:hover { background: #fff; color: var(--ink); box-shadow: 0 16px 50px -10px rgba(200, 245, 96, 0.7); }

/* hero */
.pb-hero {
  position: relative; min-height: 100vh; min-height: 100svh;
  padding: 92px clamp(16px, 4vw, 56px) 36px;
  display: flex; flex-direction: column;
  box-sizing: border-box;
}
.pb-hero__meta { display: flex; justify-content: space-between; gap: 16px; padding-bottom: 14px; border-bottom: 1.5px solid var(--ink); }
.pb-tag { background: var(--lime); color: var(--ink) !important; padding: 3px 8px; border-radius: 6px; }
.pb-hero__title {
  margin: clamp(12px, 3vh, 32px) 0 0;
  font-weight: 850; font-size: clamp(56px, 11.2vw, 210px); line-height: 0.84; letter-spacing: -0.055em;
  text-transform: uppercase; color: var(--ink);
  user-select: none;
}
.pb-hero__line { display: block; white-space: nowrap; }
.pb-hero__line + .pb-hero__line { text-align: right; }
.pb-hero__mask { display: inline-block; overflow: hidden; vertical-align: top; padding-bottom: 0.04em; }
.pb-hero__mask.is-sp { width: 0.3em; }
.pb-hero__word { display: inline-block; white-space: nowrap; }
.pb-hero__char { display: inline-block; font-weight: 850; will-change: transform; }

.pb-crystals { position: absolute; inset: 120px clamp(16px, 4vw, 56px) 0; pointer-events: none; z-index: 5; }
.pb-crystal { position: absolute; width: clamp(64px, 8vw, 118px); pointer-events: auto; cursor: grab; touch-action: none; }
.pb-crystal:active { cursor: grabbing; }
.pb-crystal__float { position: relative; }
.pb-crystal img { width: 100%; display: block; filter: drop-shadow(0 18px 24px rgba(47, 91, 255, 0.28)); user-select: none; -webkit-user-drag: none; }
.pb-crystal__tag {
  position: absolute; left: 50%; bottom: -6px; transform: translate(-50%, 6px);
  font: 600 11px 'JetBrains Mono', monospace; background: var(--ink); color: #fff; padding: 3px 8px; border-radius: 6px;
  opacity: 0; transition: opacity 0.25s, transform 0.25s; white-space: nowrap; pointer-events: none;
}
.pb-crystal:hover .pb-crystal__tag { opacity: 1; transform: translate(-50%, 0); }

.pb-hero__bottom { margin-top: auto; display: grid; grid-template-columns: 1fr minmax(320px, 400px); gap: 32px; align-items: end; padding-top: 28px; }
.pb-hero__lead p { max-width: 460px; font-size: clamp(16px, 1.3vw, 19px); line-height: 1.5; color: #3d3a35; margin: 0 0 24px; }
.pb-hero__cta { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
.pb-hint { display: inline-flex; align-items: center; gap: 8px; font: 500 13px 'JetBrains Mono', monospace; color: var(--blue); }

.pb-drop {
  position: relative; z-index: 3;
  background: rgba(255, 255, 255, 0.86); border: 1.5px solid rgba(17, 17, 17, 0.1);
  border-radius: 24px; padding: 16px 18px;
  backdrop-filter: blur(14px);
  box-shadow: 0 40px 80px -40px rgba(17, 17, 17, 0.5);
  transition: border-color 0.3s, box-shadow 0.3s;
}
.pb-drop.is-hot { border-color: var(--blue); box-shadow: 0 0 0 6px rgba(47, 91, 255, 0.15), 0 40px 80px -40px rgba(47, 91, 255, 0.6); }
.pb-drop__head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.pb-live { display: inline-flex; align-items: center; gap: 6px; font: 600 11px 'JetBrains Mono', monospace; color: #1f9d55; }
.pb-live i { width: 7px; height: 7px; border-radius: 50%; background: #1f9d55; animation: pb-pulse 1.6s infinite; }
@keyframes pb-pulse { 50% { box-shadow: 0 0 0 5px rgba(31, 157, 85, 0.2); } }
.pb-drop__body { display: flex; gap: 16px; align-items: center; }
.pb-drop__donut { width: 96px; flex: none; transform: rotate(-90deg); }
.pb-drop__seg { transition: stroke-dasharray 0.9s cubic-bezier(0.3, 1.4, 0.4, 1), stroke-dashoffset 0.9s cubic-bezier(0.3, 1.4, 0.4, 1); }
.pb-drop__info { min-width: 0; flex: 1; }
.pb-drop__total { display: block; font-weight: 850; font-size: 28px; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; margin-bottom: 6px; }
.pb-drop__info ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 3px 12px; font-size: 12px; color: #55524c; }
.pb-drop__info li { display: flex; align-items: center; gap: 5px; transition: opacity 0.3s; }
.pb-drop__info li.is-zero { opacity: 0.35; }
.pb-drop__info li i { width: 7px; height: 7px; border-radius: 2px; flex: none; }
.pb-drop__info li em { margin-left: auto; font-style: normal; font-weight: 700; color: var(--ink); }
.pb-drop__log { list-style: none; margin: 10px 0 0; padding: 0; display: grid; gap: 4px; }
.pb-drop__log:empty { display: none; }
.pb-drop__log li { display: flex; justify-content: space-between; font: 500 12px 'JetBrains Mono', monospace; padding: 6px 10px; border-radius: 8px; background: rgba(200, 245, 96, 0.45); }
.pb-log-enter-from { opacity: 0; transform: translateY(-10px) scale(0.95); }
.pb-log-enter-active, .pb-log-leave-active, .pb-log-move { transition: all 0.5s cubic-bezier(0.2, 0.9, 0.3, 1.2); }
.pb-log-leave-to { opacity: 0; }
.pb-log-leave-active { position: absolute; }
.pb-drop__zone {
  position: absolute; inset: -1.5px; border-radius: 24px; border: 2px dashed var(--blue);
  display: grid; place-items: end center; padding-bottom: 8px;
  font: 600 11px 'JetBrains Mono', monospace; color: var(--blue); text-transform: uppercase;
  opacity: 0; transition: opacity 0.3s; pointer-events: none;
}
.pb-drop.is-hot .pb-drop__zone { opacity: 1; }

/* marquee */
.pb-marquee { padding: 40px 0; overflow: hidden; border-block: 1.5px solid var(--ink); background: rgba(243, 240, 233, 0.6); }
.pb-marquee__row { display: flex; width: max-content; font-weight: 850; text-transform: uppercase; letter-spacing: -0.04em; font-size: clamp(48px, 9vw, 140px); line-height: 1; white-space: nowrap; color: transparent; -webkit-text-stroke: 1.5px var(--ink); }
.pb-marquee__row--solid { color: var(--blue); -webkit-text-stroke: 0; font-size: clamp(28px, 4.5vw, 64px); margin-top: 10px; }

/* sections */
.pb-section { padding: clamp(80px, 12vw, 160px) 0; }
.pb-container { width: min(1280px, 100% - 2 * clamp(16px, 4vw, 56px)); margin: 0 auto; }
.pb-section__head { margin-bottom: clamp(32px, 5vw, 64px); }
.pb-h2 { margin: 14px 0 0; font-weight: 850; font-size: clamp(40px, 6.6vw, 104px); line-height: 0.92; letter-spacing: -0.05em; color: var(--ink); text-transform: uppercase; }
.pb-dim { color: rgba(17, 17, 17, 0.28); }
.pb-split__w { display: inline-block; overflow: hidden; vertical-align: top; }
.pb-split__w > span { display: inline-block; }
.pb-sub { max-width: 560px; margin: 20px 0 0; font-size: 18px; line-height: 1.5; color: #3d3a35; }

/* horizontal */
.pb-hscroll { height: 100vh; height: 100svh; overflow: hidden; display: flex; align-items: center; }
.pb-hscroll__track { display: flex; gap: 20px; padding: 0 clamp(16px, 4vw, 56px); align-items: stretch; will-change: transform; }
.pb-hscroll__intro { flex: none; width: min(560px, 82vw); display: flex; flex-direction: column; justify-content: center; padding-right: 40px; }
.pb-scrollhint { margin-top: 28px; color: var(--blue) !important; }
.pb-fcard {
  flex: none; width: clamp(280px, 30vw, 420px); height: min(560px, 70vh);
  border-radius: 28px; padding: 26px; box-sizing: border-box;
  display: flex; flex-direction: column;
  border: 1.5px solid var(--ink);
}
.pb-fcard--ink { background: var(--ink); color: #fff; }
.pb-fcard--blue { background: var(--blue); color: #fff; border-color: var(--blue); }
.pb-fcard--lime { background: var(--lime); }
.pb-fcard--paper { background: #fff; }
.pb-fcard--ink :deep(.pb-mono), .pb-fcard--blue :deep(.pb-mono) { color: rgba(255, 255, 255, 0.6); }
.pb-fcard__top { display: flex; justify-content: space-between; align-items: center; }
.pb-fcard__viz { flex: 1; display: grid; place-items: center; min-height: 0; }
.pb-fcard h3 { margin: 0 0 10px; font-weight: 800; font-size: clamp(24px, 2.4vw, 34px); letter-spacing: -0.03em; line-height: 1; color: inherit; }
.pb-fcard p { margin: 0; color: inherit; opacity: 0.75; line-height: 1.45; }
.pb-viz-spark { width: 90%; overflow: visible; }
.pb-viz-spark path { fill: none; stroke: var(--lime); stroke-width: 4; stroke-linejoin: round; }
.pb-viz-spark circle { fill: var(--lime); }
.pb-viz-cal { display: grid; grid-template-columns: repeat(6, 1fr); gap: 8px; width: 90%; }
.pb-viz-cal span { aspect-ratio: 1; border-radius: 12px; background: rgba(255, 255, 255, 0.14); display: flex; flex-wrap: wrap; align-content: flex-start; gap: 3px; padding: 7px; }
.pb-viz-cal b { width: 100%; font: 600 11px 'JetBrains Mono', monospace; opacity: 0.7; }
.pb-viz-cal i { width: 8px; height: 8px; border-radius: 50%; background: var(--lime); }
.pb-viz-bars { display: flex; gap: 4px; width: 90%; height: 54px; }
.pb-viz-bars i { border-radius: 10px; border: 1.5px solid var(--ink); }
.pb-viz-rows { list-style: none; margin: 0; padding: 0; width: 90%; display: grid; gap: 8px; }
.pb-viz-rows li { display: flex; justify-content: space-between; padding: 12px 14px; border-radius: 12px; background: var(--paper); font-family: 'JetBrains Mono', monospace; font-size: 13px; }
.pb-viz-crystal { position: relative; width: 70%; aspect-ratio: 1.3; }
.pb-viz-crystal img { position: absolute; width: 60%; filter: drop-shadow(0 20px 30px rgba(47, 91, 255, 0.4)); }
.pb-viz-crystal img:first-child { left: 0; top: 0; }
.pb-viz-crystal img:last-child { right: 0; bottom: 0; width: 45%; }
.pb-viz-stack { position: relative; width: 60%; aspect-ratio: 1.4; }
.pb-viz-stack i { position: absolute; inset: 0; border-radius: 16px; background: rgba(255, 255, 255, 0.95); border: 1.5px solid var(--ink); }
.pb-viz-stack i:nth-child(1) { transform: translate(-14%, -14%) rotate(-8deg); opacity: 0.5; }
.pb-viz-stack i:nth-child(2) { transform: translate(-7%, -7%) rotate(-4deg); opacity: 0.75; }

/* security */
.pb-sec { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0; border-top: 1.5px solid var(--ink); border-left: 1.5px solid var(--ink); }
.pb-sec__card { padding: 28px 24px 36px; border-right: 1.5px solid var(--ink); border-bottom: 1.5px solid var(--ink); background: rgba(255, 255, 255, 0.4); transition: background 0.35s, color 0.35s; }
.pb-sec__card:hover { background: var(--ink); color: #fff; }
.pb-sec__icon { display: block; margin: 40px 0 24px; color: var(--blue); transition: transform 0.5s cubic-bezier(0.3, 1.6, 0.4, 1); }
.pb-sec__card:hover .pb-sec__icon { transform: scale(1.25) rotate(-8deg); color: var(--lime); }
.pb-sec__card h3 { margin: 0 0 10px; font-weight: 800; font-size: 22px; letter-spacing: -0.02em; color: inherit; }
.pb-sec__card p { margin: 0; color: inherit; line-height: 1.5; opacity: 0.75; }

/* price */
.pb-price__zero {
  font-weight: 900; font-size: clamp(160px, 34vw, 520px); line-height: 0.8; letter-spacing: -0.07em;
  margin: 20px 0 30px;
  color: transparent;
  background: linear-gradient(var(--blue), var(--blue)) no-repeat 0 0 / 0% 100%, rgba(17, 17, 17, 0.08);
  -webkit-background-clip: text; background-clip: text;
}
.pb-price__row { display: grid; grid-template-columns: 1fr 1fr; gap: 40px; border-top: 1.5px solid var(--ink); padding-top: 24px; }
.pb-price__row p { margin: 0; font-size: 22px; font-weight: 600; letter-spacing: -0.01em; line-height: 1.35; }
.pb-price__row ul { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-weight: 600; }

/* faq */
.pb-faq { display: grid; grid-template-columns: 1fr 1.7fr; gap: 60px; }
.pb-faq__item { border-bottom: 1.5px solid var(--ink); }
.pb-faq__item:first-child { border-top: 1.5px solid var(--ink); }
.pb-faq__q { width: 100%; display: flex; gap: 18px; align-items: baseline; background: none; border: 0; text-align: left; padding: 22px 0; font: 700 clamp(17px, 1.5vw, 21px) / 1.3 'Inter Tight', sans-serif; color: var(--ink); cursor: pointer; letter-spacing: -0.01em; }
.pb-faq__plus { position: relative; width: 18px; height: 18px; flex: none; margin-left: auto; align-self: center; }
.pb-faq__plus::before, .pb-faq__plus::after { content: ''; position: absolute; top: 8px; left: 0; width: 18px; height: 2px; background: var(--ink); transition: transform 0.4s; }
.pb-faq__plus::after { transform: rotate(90deg); }
.pb-faq__item.is-open .pb-faq__plus::after { transform: rotate(0); }
.pb-faq__a { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.5s cubic-bezier(0.7, 0, 0.2, 1); }
.pb-faq__a > div { overflow: hidden; }
.pb-faq__item.is-open .pb-faq__a { grid-template-rows: 1fr; }
.pb-faq__a p { margin: 0 0 24px 52px; color: #3d3a35; line-height: 1.65; }

/* final */
.pb-final { padding: 0; }
.pb-final__card {
  position: relative; overflow: hidden;
  min-height: 100vh; min-height: 100svh;
  background: var(--ink); color: #fff;
  display: grid; place-content: center; justify-items: center; text-align: center; gap: 22px;
  padding: 80px 20px;
}
.pb-final__title { margin: 0; font-weight: 900; font-size: clamp(64px, 15vw, 260px); line-height: 0.82; letter-spacing: -0.065em; text-transform: uppercase; color: #fff; position: relative; z-index: 1; }
.pb-final__card > p { margin: 0; font-size: 18px; color: #a6a29a; position: relative; z-index: 1; }
.pb-final__card .pb-btn { position: relative; z-index: 1; }
.pb-final__orbit { position: absolute; inset: 0; display: grid; place-items: center; animation: pb-spin 40s linear infinite; }
.pb-final__orbit img {
  position: absolute; width: clamp(56px, 7vw, 110px); opacity: 0.9;
  transform: rotate(calc(var(--i) * 60deg)) translateX(clamp(170px, 38vw, 560px)) rotate(calc(var(--i) * -60deg));
  filter: drop-shadow(0 20px 40px rgba(47, 91, 255, 0.5));
}
@keyframes pb-spin { to { rotate: 360deg; } }

.pb-footer { display: flex; gap: 24px; padding: 28px clamp(16px, 4vw, 56px); background: var(--ink); color: #8b877f; font-size: 14px; border-top: 1px solid #2a2a2a; }
.pb-footer a { color: #8b877f; text-decoration: none; }
.pb-footer a:hover { color: #fff; }

@media (max-width: 899px) {
  .pb-nav, .pb-link, .pb-hide-m { display: none; }
  .pb-header__actions { margin-left: auto; }
  .pb-hero { padding-top: 80px; }
  .pb-hero__title { font-size: clamp(40px, 13.5vw, 120px); line-height: 0.9; }
  .pb-hero__line { white-space: normal; }
  .pb-hero__bottom { grid-template-columns: 1fr; gap: 20px; }
  .pb-crystals { inset: 120px 8px auto; height: 300px; }
  .pb-crystal { width: 64px; }
  .pb-hero__lead p { margin-bottom: 18px; }
  .pb-btn--lg { padding: 17px 26px; font-size: 16px; }
  .pb-sec { grid-template-columns: 1fr 1fr; }
  .pb-sec__icon { margin: 24px 0 16px; }
  .pb-price__row, .pb-faq { grid-template-columns: 1fr; gap: 24px; }
  .pb-faq__a p { margin-left: 0; }
  .pb-fcard { width: 78vw; height: 64vh; }
}
@media (prefers-reduced-motion: reduce) {
  .pb-final__orbit { animation: none; }
}
</style>
