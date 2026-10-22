<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import LandingIcon from './LandingIcon.vue'
import { formatRub, prefersReducedMotion } from './useLandingMotion'

gsap.registerPlugin(ScrollTrigger)
const emit = defineEmits(['demo', 'ready'])

/* ---------- данные дашборда ---------- */
const CLASSES = [
  { name: 'Акции', c: '#3d5afe', icon: 'candles', src: 'Т-Инвестиции · 14 бумаг', base: 1312400 },
  { name: 'Облигации', c: '#22b8cf', icon: 'bond', src: 'Т-Инвестиции · купоны', base: 0 },
  { name: 'Золото', c: '#f5b544', icon: 'gold', src: 'Т-Инвестиции · GLDRUB', base: 0 },
  { name: 'Крипто', c: '#ff7a45', icon: 'bitcoin', src: 'Ручной ввод', base: 0 },
  { name: 'Валюта', c: '#12b76a', icon: 'dollar', src: 'Наличные и вклады', base: 0 },
  { name: 'Недвижимость', c: '#8b5cf6', icon: 'house', src: 'Ручная оценка', base: 0 }
]

/* фишки активов, которые «влетают» в дашборд при скролле (порядок = порядок приземления) */
const CHIPS = [
  { name: 'Сбербанк', val: '312 000 ₽', chg: '+3,2%', cls: 0, value: 312000, side: -1, f: 0.04, dx: 18, z: 1 },
  { name: 'Bitcoin', val: '395 000 ₽', chg: '+5,6%', cls: 3, value: 395000, side: 1, f: 0, dx: -6, z: 1.04 },
  { name: 'ОФЗ 26238', val: '486 000 ₽', chg: '+0,4%', cls: 1, value: 486000, side: -1, f: 0.46, dx: -34, z: 0.94 },
  { name: 'Доллары', val: '241 000 ₽', chg: '−0,3%', cls: 4, value: 241000, side: 1, f: 0.44, dx: 36, z: 0.92 },
  { name: 'Золото', val: '228 000 ₽', chg: '+1,8%', cls: 2, value: 228000, side: -1, f: 0.9, dx: 26, z: 1.06 },
  { name: 'Квартира', val: '5 200 000 ₽', chg: '+0,9%', cls: 5, value: 5200000, side: 1, f: 0.88, dx: -18, z: 1 }
].map((ch) => ({ ...ch, c: CLASSES[ch.cls].c, icon: CLASSES[ch.cls].icon }))

const FINAL = CLASSES.reduce((s, c) => s + c.base, 0) + CHIPS.reduce((s, c) => s + c.value, 0)
const NAV = [
  { t: 'Обзор', i: 'layers' }, { t: 'Портфели', i: 'wallet' }, { t: 'Сделки', i: 'receipt' },
  { t: 'Дивиденды', i: 'calendar' }, { t: 'Аналитика', i: 'trend' }, { t: 'Конструктор', i: 'target' }
]
const TRADES = [
  { op: 'Покупка', s: 'SBER · 10 шт', v: '3 124 ₽' },
  { op: 'Купон', s: 'ОФЗ 26238', v: '+1 773 ₽' },
  { op: 'Дивиденды', s: 'LKOH', v: '+18 400 ₽' },
  { op: 'Покупка', s: 'YDEX · 2 шт', v: '8 412 ₽' },
  { op: 'Покупка', s: 'GLDRUB · 5 г', v: '45 600 ₽' }
]
const DIV_BARS = [22, 0, 14, 8, 30, 52, 96, 64, 18, 40, 12, 58]
const MONTHS = ['Ноя', 'Дек', 'Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт']

/* история капитала: сглаженное случайное блуждание вверх, последняя точка = 1 */
const SERIES = (() => {
  let seed = 11
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  const out = []
  let v = 0.6, noise = 0
  for (let i = 0; i < 48; i++) {
    noise = noise * 0.72 + (rnd() - 0.46) * 0.045
    v += 0.0085 + noise * 0.5
    out.push(v)
  }
  const last = out[out.length - 1]
  return out.map((x) => x / last)
})()

/* ---------- состояние ---------- */
const LAND0 = Object.fromEntries(CHIPS.map((_, i) => ['l' + i, 0]))
const land = { ...LAND0 } // твинится таймлайном
const L = reactive({ ...LAND0 }) // зеркало для шаблона
const live = reactive({ d: 0 })
const toast = reactive({ on: false, i: 0 })
const tradesNew = ref(3)
const mobile = ref(false)
const chipMode = ref('full')
const isStatic = ref(false)

const values = computed(() => CLASSES.map((c, ci) =>
  c.base + CHIPS.reduce((s, ch, i) => s + (ch.cls === ci ? ch.value * L['l' + i] : 0), 0)
))
const sum = computed(() => values.value.reduce((a, b) => a + b, 0))
const total = computed(() => sum.value * (1 + live.d))
const todayPct = computed(() => 0.42 + live.d * 100)
const todayRub = computed(() => total.value * todayPct.value / 100)
const litCount = computed(() => values.value.filter((v) => v > 1).length)
const classWord = computed(() => (litCount.value === 1 ? 'класс' : litCount.value < 5 ? 'класса' : 'классов'))

const pct = (v) => v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const share = (v) => (sum.value ? Math.round((v / sum.value) * 100) : 0)
function short(v) {
  if (v < 1) return '—'
  if (v >= 1e6) return (v / 1e6).toFixed(1).replace('.', ',') + ' млн ₽'
  return Math.round(v / 1000) + ' тыс ₽'
}
const portfolios = computed(() => {
  const v = values.value
  return [
    { t: 'Т-Инвестиции', mark: 'Т', c: '#ffdd2d', ink: '#111', v: v[0] + v[1] + v[2] },
    { t: 'Крипто', c: '#ff7a45', i: 'bitcoin', v: v[3] },
    { t: 'Наличные', c: '#12b76a', i: 'dollar', v: v[4] },
    { t: 'Недвижимость', c: '#8b5cf6', i: 'house', v: v[5] }
  ]
})

/* график */
const CW = 600, CH = 150
const chartPts = computed(() => {
  const k = 0.5 + 0.5 * (sum.value / FINAL)
  const n = SERIES.length
  return SERIES.map((v, i) => {
    const wob = i >= n - 3 ? live.d * 18 * ((i - n + 4) / 3) : 0
    return [(i / (n - 1)) * CW, CH - 6 - ((v * (1 + wob) - 0.42) / 0.62) * (CH - 18) * k]
  })
})
function smooth(pts) {
  let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)}`
  for (let i = 1; i < pts.length; i++) {
    const [x0, y0] = pts[i - 1]
    const [x1, y1] = pts[i]
    const mx = ((x0 + x1) / 2).toFixed(1)
    d += ` C${mx},${y0.toFixed(1)} ${mx},${y1.toFixed(1)} ${x1.toFixed(1)},${y1.toFixed(1)}`
  }
  return d
}
const chartLine = computed(() => smooth(chartPts.value))
const chartArea = computed(() => `${chartLine.value} L${CW},${CH} L0,${CH} Z`)
const chartEnd = computed(() => chartPts.value[chartPts.value.length - 1])

/* кольцо структуры */
const R = 46
const CIRC = 2 * Math.PI * R
const donut = computed(() => {
  let acc = 0
  return values.value.map((v, i) => {
    const len = sum.value ? (v / sum.value) * CIRC : 0
    const seg = { c: CLASSES[i].c, dash: `${Math.max(0, len - 2.5)} ${CIRC}`, off: -acc, on: len > 3 }
    acc += len
    return seg
  })
})

/* ---------- DOM и раскладка ---------- */
const root = ref(null)
const pinEl = ref(null)
const copyEl = ref(null)
const tiltEl = ref(null)
const introEl = ref(null)
const fitEl = ref(null)
const appEl = ref(null)
const clipEl = ref(null)
const chipEls = []
const rowIcons = []

const HEADER = 64
const DESIGN = { w: 1180, h: 700 }
const DESIGN_M = { w: 390, h: 664 }
const design = computed(() => (mobile.value ? DESIGN_M : DESIGN))
const geo = { startY: 400, f: CHIPS.map(() => ({ x: 0, y: 0, s: 0.3 })) }

function offsetIn(el, top) {
  let x = 0, y = 0
  while (el && el !== top) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent }
  return { x, y }
}

/** Размер «экрана», его стартовое положение, позиции фишек и точки их приземления. */
function measure() {
  const pin = pinEl.value
  if (!pin || !copyEl.value) return
  const W = pin.clientWidth
  const H = pin.clientHeight
  const nextMobile = W < 761
  const nextChip = W >= 1180 ? 'full' : W >= 920 ? 'pill' : 'token'
  if (nextMobile !== mobile.value || nextChip !== chipMode.value) {
    mobile.value = nextMobile
    chipMode.value = nextChip
    nextTick(() => ScrollTrigger.refresh())
  }

  const D = nextMobile ? DESIGN_M : DESIGN
  const padX = nextMobile ? 14 : 40
  const fit = Math.min((W - padX * 2) / D.w, (H - HEADER - 28) / D.h, 1.06)
  const appW = D.w * fit
  const appH = D.h * fit
  const appLeft = (W - appW) / 2
  const appTop = HEADER + Math.max(10, (H - HEADER - appH) / 2)

  const tilt = tiltEl.value
  tilt.style.width = appW + 'px'
  tilt.style.height = appH + 'px'
  fitEl.value.style.transform = `scale(${fit})`
  if (isStatic.value) return
  tilt.style.left = appLeft + 'px'
  tilt.style.top = appTop + 'px'

  const copyTop = copyEl.value.offsetTop + copyEl.value.querySelector('.hx-title').offsetTop
  const copyBottom = copyEl.value.offsetTop + copyEl.value.offsetHeight
  const sizes = chipEls.map((el) => ({ w: el.offsetWidth, h: el.offsetHeight }))
  const centers = []
  let startTop

  if (nextChip === 'full') {
    startTop = copyBottom + Math.min(56, Math.max(28, H * 0.05))
    const r = Math.min(W * 0.36, 540)
    CHIPS.forEach((ch) => {
      centers.push({ x: W / 2 + ch.side * (r + ch.dx), y: copyTop + 12 + ch.f * (startTop + 36 - copyTop) })
    })
  } else {
    const ch = sizes[0].h
    const rowY = copyBottom + 24 + ch / 2
    const widths = sizes.reduce((s, z) => s + z.w, 0)
    const gap = Math.max(4, Math.min(nextChip === 'token' ? 16 : 10, (W - 24 - widths) / (CHIPS.length - 1)))
    let x = (W - widths - gap * (CHIPS.length - 1)) / 2
    sizes.forEach((z, i) => {
      centers.push({ x: x + z.w / 2, y: rowY + (i % 2 ? 5 : -5) })
      x += z.w + gap
    })
    startTop = rowY + ch / 2 + 22
  }
  startTop = Math.min(startTop, H - 110)
  geo.startY = startTop - appTop

  chipEls.forEach((el, i) => {
    const c = centers[i]
    el.style.left = c.x - sizes[i].w / 2 + 'px'
    el.style.top = c.y - sizes[i].h / 2 + 'px'
    const icon = el.querySelector('.hx-chip__icon')
    const io = offsetIn(icon, el)
    const ox = io.x + icon.offsetWidth / 2 - sizes[i].w / 2
    const oy = io.y + icon.offsetHeight / 2 - sizes[i].h / 2
    const target = rowIcons[CHIPS[i].cls]
    const to = offsetIn(target, appEl.value)
    const tx = appLeft + (to.x + target.offsetWidth / 2) * fit
    const ty = appTop + (to.y + target.offsetHeight / 2) * fit
    const s = (target.offsetWidth * fit) / icon.offsetWidth
    geo.f[i] = { x: tx - s * ox - c.x, y: ty - s * oy - c.y, s }
  })
}

/* ---------- «живые» данные ---------- */
let driftCall = null
let toastCall = null
let liveOn = false
function drift() {
  driftCall = gsap.to(live, {
    d: (Math.random() - 0.42) * 0.0032, duration: 1.4 + Math.random(), ease: 'sine.inOut',
    onComplete: () => { driftCall = gsap.delayedCall(0.4 + Math.random() * 0.8, drift) }
  })
}
function nextToast() {
  toast.i = (toast.i + 1) % TRADES.length
  toast.on = true
  tradesNew.value = tradesNew.value >= 9 ? 3 : tradesNew.value + 1
  toastCall = gsap.delayedCall(3.4, () => {
    toast.on = false
    toastCall = gsap.delayedCall(2.6, nextToast)
  })
}
function startLive() {
  if (liveOn) return
  liveOn = true
  drift()
  toastCall = gsap.delayedCall(2.4, nextToast)
}
function stopLive() {
  liveOn = false
  driftCall?.kill()
  toastCall?.kill()
}

function onMove(e) {
  const r = pinEl.value.getBoundingClientRect()
  pinEl.value.style.setProperty('--px', (((e.clientX - r.left) / r.width) * 100).toFixed(1) + '%')
  pinEl.value.style.setProperty('--py', (((e.clientY - r.top) / r.height) * 100).toFixed(1) + '%')
}

let ctx = null
let io = null

onMounted(async () => {
  const reduced = prefersReducedMotion()
  isStatic.value = reduced
  await nextTick()
  measure()
  await nextTick()
  measure()

  if (reduced) {
    Object.assign(L, Object.fromEntries(CHIPS.map((_, i) => ['l' + i, 1])))
    emit('ready')
    return
  }

  ctx = gsap.context(() => {
    /* появление */
    gsap.timeline({ delay: 0.1 })
      .from('.hx-eyebrow', { y: 14, opacity: 0, duration: 1, ease: 'expo.out' })
      .from('.hx-line > span', { yPercent: 108, duration: 1.4, ease: 'expo.out', stagger: 0.1 }, 0.08)
      .from('.hx-lead, .hx-cta', { y: 18, opacity: 0, duration: 1.2, ease: 'expo.out', stagger: 0.08 }, 0.4)
      .from(introEl.value, { y: 160, opacity: 0, duration: 2, ease: 'expo.out' }, 0.45)
      .from('.hx-chip__pop', { scale: 0.3, opacity: 0, duration: 1.3, ease: 'back.out(1.7)', stagger: 0.07 }, 0.85)
      .from('.hx-hint', { opacity: 0, y: 10, duration: 1, ease: 'expo.out' }, 1.4)
      .fromTo(clipEl.value, { attr: { width: 0 } }, { attr: { width: CW + 20 }, duration: 2.2, ease: 'power2.inOut' }, 0.9)
      .from('.hx-dot', { opacity: 0, scale: 0, duration: 0.8, ease: 'back.out(2)' }, 2.9)

    /* скролл: экран встаёт ровно, активы собираются в нём */
    const tl = gsap.timeline({
      defaults: { ease: 'none' },
      onUpdate: () => {
        for (const k in land) if (L[k] !== land[k]) L[k] = land[k]
      },
      scrollTrigger: {
        trigger: pinEl.value,
        start: 'top top',
        end: () => '+=' + Math.round(window.innerHeight * 1.8),
        pin: true,
        scrub: 0.7,
        invalidateOnRefresh: true,
        // hero создаётся позже секций ниже (после nextTick) — пересчитываем его первым,
        // иначе их pin-зоны считаются без отступа под закреплённый первый экран
        refreshPriority: 10,
        onRefreshInit: () => { measure() }
      }
    })
    tl.fromTo(tiltEl.value,
      { y: () => geo.startY, rotateX: 26, scale: 0.94 },
      { y: 0, rotateX: 0, scale: 1, duration: 0.38, ease: 'power2.inOut' }, 0)
      .to(copyEl.value, { y: -90, opacity: 0, scale: 0.96, duration: 0.2, ease: 'power1.in' }, 0)
      .to('.hx-hint', { opacity: 0, duration: 0.05 }, 0)
      .to('.hx-aurora', { yPercent: -16, scale: 1.12, duration: 0.5 }, 0)
      .to(chipEls, { y: -26, duration: 0.36 }, 0)

    CHIPS.forEach((_, i) => {
      const el = chipEls[i]
      const t0 = 0.36 + i * 0.085
      tl.to(el, { x: () => geo.f[i].x, y: () => geo.f[i].y, scale: () => geo.f[i].s, duration: 0.17, ease: 'power2.in' }, t0)
        .to(el.querySelector('.hx-chip__txt'), { opacity: 0, duration: 0.08 }, t0 + 0.03)
        .to(el, { opacity: 0, duration: 0.025 }, t0 + 0.155)
        .to(land, { ['l' + i]: 1, duration: 0.06, ease: 'power1.out' }, t0 + 0.15)
    })
    tl.fromTo('.hx-app__ring', { opacity: 0 }, { opacity: 1, duration: 0.08 }, 0.92)
      .fromTo('.hx-done', { opacity: 0, y: 6, scale: 0.9 }, { opacity: 1, y: 0, scale: 1, duration: 0.06, ease: 'back.out(2)' }, 0.94)
      .to({}, { duration: 0.06 }, 1)
  }, root.value)
  ScrollTrigger.sort()
  ScrollTrigger.refresh()
  // разметка страницы окончательная (pin-отступы расставлены) — можно прыгать по якорям
  emit('ready')

  io = new IntersectionObserver(([e]) => (e.isIntersecting ? startLive() : stopLive()), { threshold: 0.05 })
  io.observe(root.value)
})

onUnmounted(() => {
  io?.disconnect()
  stopLive()
  ctx?.revert()
})
</script>

<template>
  <section ref="root" class="hx" :class="{ 'is-static': isStatic }" :data-chips="chipMode">
    <div ref="pinEl" class="hx-pin" @pointermove="onMove">
      <div class="hx-bg" aria-hidden="true">
        <div class="hx-aurora"><i /></div>
        <div class="hx-grid" />
        <div class="hx-beam" />
        <div class="hx-spot" />
        <div class="hx-noise" />
      </div>

      <div ref="copyEl" class="hx-copy">
        <a href="#flow" class="hx-eyebrow" @click.prevent="emit('demo')">
          <span class="hx-eyebrow__tag">Новое</span>
          Автоимпорт из Т-Инвестиций
          <LandingIcon name="arrow" :size="14" :stroke="1.8" />
        </a>
        <h1 class="hx-title">
          <span class="hx-line"><span>Все инвестиции.</span></span>
          <span class="hx-line hx-line--accent"><span>Один экран.</span></span>
        </h1>
        <p class="hx-lead">
          Брокерские счета, вклады, валюта, крипта и&nbsp;недвижимость — в&nbsp;одной картине.
          CapitalView сам считает реальную доходность, дивиденды и&nbsp;структуру.
        </p>
        <div class="hx-cta">
          <router-link to="/login" class="lp-btn lp-btn--light lp-btn--lg">
            Начать бесплатно
            <LandingIcon name="arrow" :size="18" :stroke="1.8" />
          </router-link>
          <a href="#flow" class="lp-btn lp-btn--lg hx-btn2" @click.prevent="emit('demo')">Посмотреть в деле</a>
        </div>
      </div>

      <!-- приложение -->
      <div class="hx-stage" aria-hidden="true">
        <div ref="tiltEl" class="hx-tilt">
          <div ref="introEl" class="hx-intro">
            <div ref="fitEl" class="hx-fit">
              <div ref="appEl" class="hx-app" :class="{ 'hx-app--m': mobile }" :style="{ width: design.w + 'px', height: design.h + 'px' }">
                <span class="hx-app__ring" />
                <div class="hx-chrome">
                  <span class="hx-chrome__dots"><i /><i /><i /></span>
                  <span class="hx-chrome__url"><LandingIcon name="lock" :size="10" :stroke="2" /> app.capitalview.ru</span>
                  <span class="hx-chrome__sync"><i class="lp-live" /> Синхронизировано</span>
                </div>

                <div class="hx-body">
                  <aside v-if="!mobile" class="hx-side">
                    <div class="hx-side__logo"><img src="/site-logo.webp" alt="" width="22" height="22" />CapitalView</div>
                    <div class="hx-side__search">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="6.5" /><path d="M16 16l4 4" /></svg>
                      Поиск <kbd>⌘K</kbd>
                    </div>
                    <nav class="hx-side__nav">
                      <span v-for="(n, i) in NAV" :key="n.t" :class="{ 'is-on': !i }">
                        <LandingIcon :name="n.i" :size="16" />{{ n.t }}
                        <em v-if="n.t === 'Сделки'" class="hx-badge">+{{ tradesNew }}</em>
                      </span>
                    </nav>
                    <div class="hx-side__cap">Портфели</div>
                    <ul class="hx-side__pf">
                      <li v-for="p in portfolios" :key="p.t" :class="{ 'is-off': p.v < 1 }">
                        <span class="hx-pf__mark" :style="{ background: p.c, color: p.ink || '#fff' }">
                          <template v-if="p.mark">{{ p.mark }}</template>
                          <LandingIcon v-else :name="p.i" :size="11" :stroke="2" />
                        </span>
                        <span class="hx-pf__name">{{ p.t }}</span>
                        <b>{{ short(p.v) }}</b>
                      </li>
                    </ul>
                    <div class="hx-side__foot"><i class="lp-live" /> Обновлено только что</div>
                  </aside>

                  <main class="hx-main">
                    <header class="hx-head">
                      <div class="hx-head__t">
                        <b>{{ mobile ? 'Обзор' : 'Обзор капитала' }}</b>
                        <small v-if="!mobile">{{ litCount }} {{ classWord }} активов · все счета</small>
                      </div>
                      <span class="hx-done"><LandingIcon name="check" :size="12" :stroke="2.4" /> Всё в одном месте</span>
                      <span class="hx-seg"><i>1М</i><i>6М</i><i class="is-on">1Г</i><i>Всё</i></span>
                      <span v-if="!mobile" class="hx-avatar" />
                    </header>

                    <div class="hx-grid-a">
                      <section class="hx-card hx-total">
                        <div class="hx-card__row">
                          <span class="hx-label">Общий капитал</span>
                          <span class="hx-livepill"><i class="lp-live" /> Live</span>
                        </div>
                        <b class="hx-total__num">{{ formatRub(total) }}</b>
                        <div class="hx-total__delta">
                          <span class="hx-up"><LandingIcon name="arrow-up-right" :size="11" :stroke="2.4" /> 18,4% за год</span>
                          <span class="hx-today">Сегодня <em :class="{ 'is-neg': todayPct < 0 }">{{ todayPct >= 0 ? '+' : '−' }}{{ pct(Math.abs(todayPct)) }}%</em> · {{ todayPct >= 0 ? '+' : '−' }}{{ formatRub(Math.abs(todayRub)) }}</span>
                        </div>
                        <div v-if="mobile" class="hx-alloc">
                          <i v-for="(v, i) in values" :key="i" :style="{ flexGrow: v, background: CLASSES[i].c }" />
                        </div>
                        <div class="hx-chart">
                          <div class="hx-chart__plot">
                            <svg :viewBox="`0 0 ${CW} ${CH}`" preserveAspectRatio="none">
                              <defs>
                                <linearGradient id="hx-area" x1="0" x2="0" y1="0" y2="1">
                                  <stop offset="0" stop-color="#5b74ff" stop-opacity=".32" />
                                  <stop offset="1" stop-color="#5b74ff" stop-opacity="0" />
                                </linearGradient>
                                <linearGradient id="hx-stroke" x1="0" x2="1" y1="0" y2="0">
                                  <stop offset="0" stop-color="#8b5cf6" />
                                  <stop offset=".6" stop-color="#5b74ff" />
                                  <stop offset="1" stop-color="#7dd3fc" />
                                </linearGradient>
                                <clipPath id="hx-clip"><rect ref="clipEl" x="-10" y="-20" :width="CW + 20" :height="CH + 40" /></clipPath>
                              </defs>
                              <path d="M0,37 H600 M0,75 H600 M0,113 H600" class="hx-chart__grid" />
                              <g clip-path="url(#hx-clip)">
                                <path :d="chartArea" fill="url(#hx-area)" />
                                <path :d="chartLine" class="hx-chart__line" />
                              </g>
                            </svg>
                            <span class="hx-dot" :style="{ left: (chartEnd[0] / CW) * 100 + '%', top: (chartEnd[1] / CH) * 100 + '%' }" />
                          </div>
                          <div class="hx-chart__x"><span v-for="(m, i) in MONTHS" :key="m" :class="{ 'is-hide': i % 2 }">{{ m }}</span></div>
                        </div>
                      </section>

                      <section v-if="!mobile" class="hx-card hx-str">
                        <div class="hx-card__row">
                          <span class="hx-label">Структура</span>
                          <small>по классам</small>
                        </div>
                        <div class="hx-str__body">
                          <div class="hx-donut">
                            <svg viewBox="0 0 120 120">
                              <circle cx="60" cy="60" :r="R" class="hx-donut__track" />
                              <circle v-for="(s, i) in donut" v-show="s.on" :key="i" cx="60" cy="60" :r="R" class="hx-donut__seg" :stroke="s.c" :stroke-dasharray="s.dash" :stroke-dashoffset="s.off" />
                            </svg>
                            <span class="hx-donut__c"><b>{{ litCount }}</b><small>{{ classWord }}</small></span>
                          </div>
                          <ul class="hx-legend">
                            <li v-for="(c, i) in CLASSES" :key="c.name" :class="{ 'is-off': values[i] < 1 }">
                              <i :style="{ background: c.c }" />{{ c.name }}<b>{{ share(values[i]) }}%</b>
                            </li>
                          </ul>
                        </div>
                      </section>

                      <section class="hx-card hx-assets">
                        <div class="hx-card__row">
                          <span class="hx-label">Активы</span>
                          <small class="hx-link">Все <LandingIcon name="arrow" :size="11" :stroke="2" /></small>
                        </div>
                        <ul class="hx-rows">
                          <li v-for="(c, i) in CLASSES" :key="c.name" class="hx-row" :class="{ 'is-on': values[i] > 1 }" :style="{ '--c': c.c }">
                            <span :ref="(el) => (rowIcons[i] = el)" class="hx-row__icon"><LandingIcon :name="c.icon" :size="15" :stroke="1.8" /></span>
                            <span class="hx-row__name"><b>{{ c.name }}</b><small>{{ values[i] > 1 ? c.src : 'Ожидает подключения' }}</small></span>
                            <span class="hx-row__val">{{ values[i] > 1 ? formatRub(values[i] * (1 + live.d)) : '—' }}</span>
                            <span v-if="!mobile" class="hx-row__share">{{ values[i] > 1 ? share(values[i]) + '%' : '' }}</span>
                          </li>
                        </ul>
                      </section>

                      <section v-if="!mobile" class="hx-card hx-div">
                        <div class="hx-card__row">
                          <span class="hx-label">Дивиденды и купоны</span>
                          <small>12 мес</small>
                        </div>
                        <div class="hx-div__sum"><b>79 200 ₽</b><span class="hx-up"><LandingIcon name="arrow-up-right" :size="11" :stroke="2.4" /> 24%</span></div>
                        <div class="hx-div__bars">
                          <i v-for="(h, i) in DIV_BARS" :key="i" :class="{ 'is-now': i === 11 }" :style="{ height: Math.max(4, h) + '%' }" />
                        </div>
                        <div class="hx-div__next">
                          <span class="hx-date"><b>18</b>дек</span>
                          <span><b>Лукойл</b><small>Следующая выплата</small></span>
                          <em>+18 400 ₽</em>
                        </div>
                      </section>
                    </div>

                    <div class="hx-toast" :class="{ 'is-on': toast.on }">
                      <span class="hx-toast__mark">Т</span>
                      <span class="hx-toast__txt">
                        <b>Т-Инвестиции · новая операция</b>
                        <small>{{ TRADES[toast.i].op }} {{ TRADES[toast.i].s }}</small>
                      </span>
                      <em>{{ TRADES[toast.i].v }}</em>
                    </div>
                  </main>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- активы вокруг экрана -->
      <div class="hx-chips" aria-hidden="true">
        <div
          v-for="(ch, i) in CHIPS"
          :key="ch.name"
          :ref="(el) => (chipEls[i] = el)"
          class="hx-chip"
          :style="{ '--c': ch.c, '--z': ch.z, '--d': i * 0.7 + 's', '--t': 5.5 + (i % 3) + 's' }"
        >
          <div class="hx-chip__pop">
            <div class="hx-chip__body">
              <span class="hx-chip__icon"><LandingIcon :name="ch.icon" :size="chipMode === 'full' ? 19 : 17" :stroke="1.8" /></span>
              <span class="hx-chip__txt">
                <b>{{ ch.name }}</b>
                <small>{{ ch.val }} <em :class="{ 'is-neg': ch.chg.startsWith('−') }">{{ ch.chg }}</em></small>
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="hx-hint" aria-hidden="true"><span class="hx-hint__mouse"><i /></span>Листайте — активы соберутся в&nbsp;один экран</div>
    </div>
  </section>
</template>

<style scoped>
.hx { position: relative; z-index: 1; }
.hx-pin {
  --px: 50%; --py: 30%;
  position: relative; height: 100vh; height: 100svh; overflow: hidden; isolation: isolate;
  background: #06070b; color: #fff;
  border-radius: 0 0 clamp(28px, 3.4vw, 48px) clamp(28px, 3.4vw, 48px);
}

/* ---------- фон ---------- */
.hx-bg { position: absolute; inset: 0; z-index: 0; pointer-events: none; }
.hx-bg > * { position: absolute; inset: 0; }
.hx-aurora { inset: -20% -10% 10%; }
.hx-aurora i {
  position: absolute; inset: 0;
  background:
    radial-gradient(38% 34% at 50% 58%, rgba(61, 90, 254, .42), transparent 70%),
    radial-gradient(30% 30% at 30% 40%, rgba(139, 92, 246, .26), transparent 70%),
    radial-gradient(28% 26% at 72% 42%, rgba(34, 184, 207, .16), transparent 70%);
  animation: hx-aurora 16s ease-in-out infinite alternate;
}
@keyframes hx-aurora {
  from { transform: translate3d(-2%, 0, 0) rotate(-2deg); }
  to { transform: translate3d(2%, -2%, 0) rotate(2deg); }
}
.hx-grid {
  background-image:
    linear-gradient(rgba(255,255,255,.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,.045) 1px, transparent 1px);
  background-size: 64px 64px; background-position: center -1px;
  mask-image: radial-gradient(60% 55% at 50% 30%, #000 10%, transparent 75%);
  -webkit-mask-image: radial-gradient(60% 55% at 50% 30%, #000 10%, transparent 75%);
}
.hx-beam {
  background: conic-gradient(from 180deg at 50% -8%, transparent 160deg, rgba(165, 180, 255, .16) 176deg, rgba(255,255,255,.22) 180deg, rgba(165, 180, 255, .16) 184deg, transparent 200deg);
  mask-image: linear-gradient(180deg, #000, transparent 70%);
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 70%);
  mix-blend-mode: screen;
}
.hx-spot { background: radial-gradient(28vmax 28vmax at var(--px) var(--py), rgba(120, 140, 255, .09), transparent 70%); }
.hx-noise {
  opacity: .5; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 1 0 0 0 0 1 0 0 0 0 1 0 0 0 .5 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.35'/%3E%3C/svg%3E");
}

/* ---------- текст ---------- */
.hx-copy {
  position: relative; z-index: 1; display: grid; justify-items: center; text-align: center;
  padding: calc(64px + clamp(20px, 6vh, 72px)) var(--lp-pad) 0;
  will-change: transform, opacity;
}
.hx-eyebrow {
  display: inline-flex; align-items: center; gap: 10px; padding: 5px 14px 5px 5px; border-radius: 99px;
  font-size: 13.5px; color: rgba(235, 238, 255, .78); text-decoration: none;
  background: linear-gradient(180deg, rgba(255,255,255,.08), rgba(255,255,255,.03));
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.1), inset 0 1px 0 rgba(255,255,255,.08);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
  transition: box-shadow .3s, color .3s;
}
.hx-eyebrow:hover { color: #fff; box-shadow: inset 0 0 0 1px rgba(255,255,255,.2), inset 0 1px 0 rgba(255,255,255,.1); }
.hx-eyebrow .lp-icon { transition: transform .4s var(--lp-ease); }
.hx-eyebrow:hover .lp-icon { transform: translateX(3px); }
.hx-eyebrow__tag {
  padding: 4px 10px; border-radius: 99px; font-size: 12px; font-weight: 600; color: #fff;
  background: linear-gradient(100deg, #3d5afe, #8b5cf6);
  box-shadow: 0 0 18px rgba(99, 102, 241, .55), inset 0 1px 0 rgba(255,255,255,.3);
}
.hx-title {
  margin-top: clamp(18px, 2.6vh, 28px);
  font-family: var(--lp-display); font-weight: 600;
  font-size: clamp(44px, 6.6vw, 100px); line-height: .98; letter-spacing: -0.05em;
}
.hx-line { display: block; overflow: hidden; padding: 0 .04em .08em; }
.hx-line > span {
  display: inline-block;
  background: linear-gradient(180deg, #fff 30%, #c4c9d6);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hx-line--accent > span {
  background: linear-gradient(95deg, #e9edff 0%, #9fb0ff 38%, #7b8cff 58%, #b79dff 82%, #e3d9ff 100%);
  -webkit-background-clip: text; background-clip: text;
}
.hx-lead {
  margin-top: clamp(14px, 2.2vh, 24px); max-width: 620px;
  font-size: clamp(16px, 1.3vw, 19px); line-height: 1.55; color: rgba(225, 230, 248, .62);
}
.hx-cta { margin-top: clamp(20px, 3.2vh, 34px); display: flex; flex-wrap: wrap; justify-content: center; gap: 12px; }
.hx-btn2 {
  color: #fff; background: rgba(255,255,255,.06);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.16);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
}
.hx-btn2:hover { background: rgba(255,255,255,.11); }

/* ---------- сцена с приложением ---------- */
.hx-stage { position: absolute; inset: 0; z-index: 2; pointer-events: none; perspective: 1500px; perspective-origin: 50% 20%; }
.hx-tilt { position: absolute; left: 0; top: 0; transform-origin: 50% 0%; will-change: transform; }
.hx-tilt::before {
  content: ''; position: absolute; z-index: -1; left: -18%; right: -18%; top: -22%; height: 90%;
  background: radial-gradient(50% 50% at 50% 50%, rgba(77, 99, 255, .36), rgba(139, 92, 246, .12) 45%, transparent 72%);
}
.hx-tilt::after {
  content: ''; position: absolute; left: 12%; right: 12%; top: -1px; height: 1px; z-index: 2;
  background: linear-gradient(90deg, transparent, rgba(165, 180, 255, .9) 30%, #fff 50%, rgba(196, 181, 253, .9) 70%, transparent);
  box-shadow: 0 0 28px 3px rgba(129, 140, 248, .55);
}
.hx-intro { width: 100%; height: 100%; }
.hx-fit { transform-origin: 0 0; }

.hx-app {
  --a-ink: #eef0f6; --a-mut: #8b91a1; --a-dim: #5d6374; --a-line: rgba(255,255,255,.065);
  position: relative; display: flex; flex-direction: column; overflow: hidden;
  border-radius: 18px; background: #0a0c12; color: var(--a-ink);
  font: 400 13px/1.35 var(--lp-text); letter-spacing: -0.005em; text-align: left;
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.09), inset 0 1px 0 rgba(255,255,255,.14),
    0 50px 120px -30px rgba(0,0,0,.9), 0 30px 160px -40px rgba(61, 90, 254, .5);
}
.hx-app__ring {
  position: absolute; inset: 0; z-index: 5; border-radius: inherit; pointer-events: none; padding: 1px; opacity: 0;
  background: conic-gradient(from 210deg, transparent 0deg, #8b9bff 60deg, #fff 90deg, #b79dff 120deg, transparent 200deg, transparent 360deg);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask: linear-gradient(#000 0 0) content-box exclude, linear-gradient(#000 0 0);
}

.hx-chrome {
  flex: none; height: 40px; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; padding: 0 16px;
  border-bottom: 1px solid var(--a-line); background: #0c0e15;
}
.hx-chrome__dots { display: flex; gap: 7px; }
.hx-chrome__dots i { width: 11px; height: 11px; border-radius: 50%; background: rgba(255,255,255,.12); }
.hx-chrome__url {
  display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border-radius: 8px;
  background: rgba(255,255,255,.04); color: var(--a-mut); font-size: 12px;
}
.hx-chrome__sync { justify-self: end; display: inline-flex; align-items: center; gap: 8px; font-size: 12px; color: var(--a-mut); }

.hx-body { flex: 1; display: flex; min-height: 0; }

/* сайдбар */
.hx-side {
  flex: none; width: 226px; padding: 18px 12px 14px; display: flex; flex-direction: column;
  border-right: 1px solid var(--a-line); background: #08090e;
}
.hx-side__logo { display: flex; align-items: center; gap: 9px; padding: 0 8px; font: 600 15px var(--lp-display); letter-spacing: -0.02em; }
.hx-side__logo img { border-radius: 6px; }
.hx-side__search {
  margin: 16px 0 12px; display: flex; align-items: center; gap: 8px; height: 32px; padding: 0 10px; border-radius: 9px;
  background: rgba(255,255,255,.035); box-shadow: inset 0 0 0 1px var(--a-line); color: var(--a-dim); font-size: 12.5px;
}
.hx-side__search kbd { margin-left: auto; font: 500 10.5px var(--lp-text); padding: 2px 6px; border-radius: 5px; background: rgba(255,255,255,.06); color: var(--a-mut); }
.hx-side__nav { display: grid; gap: 2px; }
.hx-side__nav span {
  display: flex; align-items: center; gap: 10px; height: 33px; padding: 0 10px; border-radius: 9px;
  color: var(--a-mut); font-size: 13.5px;
}
.hx-side__nav span.is-on { color: #fff; background: linear-gradient(90deg, rgba(91, 116, 255, .2), rgba(91, 116, 255, .06)); box-shadow: inset 0 0 0 1px rgba(124, 142, 255, .18); }
.hx-side__nav .is-on .lp-icon { color: #9fb0ff; }
.hx-badge {
  margin-left: auto; font: 600 10.5px var(--lp-text); font-style: normal; padding: 2px 7px; border-radius: 99px;
  background: rgba(91, 116, 255, .22); color: #b8c3ff;
}
.hx-side__cap { margin: 20px 10px 8px; font-size: 10.5px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--a-dim); }
.hx-side__pf { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.hx-side__pf li { display: flex; align-items: center; gap: 9px; height: 30px; padding: 0 10px; font-size: 12px; transition: opacity .4s; }
.hx-side__pf li.is-off { opacity: .35; }
.hx-pf__mark { flex: none; display: grid; place-items: center; width: 18px; height: 18px; border-radius: 5px; font: 700 10.5px var(--lp-display); }
.hx-pf__name { flex: 1; min-width: 0; color: var(--a-mut); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hx-side__pf b { flex: none; font-weight: 500; white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--a-ink); }
.hx-side__foot { margin-top: auto; display: flex; align-items: center; gap: 9px; padding: 10px; border-radius: 10px; background: rgba(255,255,255,.03); font-size: 11.5px; color: var(--a-mut); }

/* основная колонка */
.hx-main { position: relative; flex: 1; min-width: 0; padding: 18px 22px 20px; display: flex; flex-direction: column; gap: 14px; }
.hx-head { display: flex; align-items: center; gap: 12px; min-height: 40px; }
.hx-head__t { display: grid; gap: 2px; }
.hx-head__t b { font: 600 19px var(--lp-display); letter-spacing: -0.02em; }
.hx-head__t small { font-size: 12px; color: var(--a-mut); }
.hx-done {
  margin-right: auto; display: inline-flex; align-items: center; gap: 6px; height: 28px; padding: 0 12px; border-radius: 99px;
  font-size: 12px; font-weight: 600; color: #7ef0b5; background: rgba(18, 183, 106, .12); box-shadow: inset 0 0 0 1px rgba(18, 183, 106, .3);
  opacity: 0;
}
.hx-seg { display: inline-flex; padding: 3px; border-radius: 9px; background: rgba(255,255,255,.04); box-shadow: inset 0 0 0 1px var(--a-line); }
.hx-seg i { font-style: normal; font-size: 11.5px; padding: 4px 10px; border-radius: 6px; color: var(--a-mut); }
.hx-seg i.is-on { background: rgba(255,255,255,.1); color: #fff; }
.hx-avatar { width: 30px; height: 30px; border-radius: 50%; background: conic-gradient(from 200deg, #3d5afe, #8b5cf6, #22b8cf, #3d5afe); box-shadow: inset 0 0 0 2px #0a0c12, 0 0 0 1px rgba(255,255,255,.14); }

.hx-grid-a { flex: 1; min-height: 0; display: grid; grid-template-columns: 1.72fr 1fr; grid-template-rows: 1.1fr 1fr; gap: 14px; }
.hx-card {
  position: relative; min-height: 0; border-radius: 14px; padding: 16px 18px;
  background: linear-gradient(180deg, #11141d, #0e1018);
  box-shadow: inset 0 0 0 1px var(--a-line), inset 0 1px 0 rgba(255,255,255,.04);
}
.hx-card__row { display: flex; align-items: center; justify-content: space-between; gap: 10px; }
.hx-card__row small { font-size: 11.5px; color: var(--a-dim); }
.hx-label { font-size: 12.5px; font-weight: 500; color: var(--a-mut); }
.hx-link { display: inline-flex; align-items: center; gap: 4px; }
.hx-livepill { display: inline-flex; align-items: center; gap: 7px; font-size: 11px; font-weight: 600; color: #7ef0b5; }
.hx-up { display: inline-flex; align-items: center; gap: 3px; height: 22px; padding: 0 8px; border-radius: 99px; font-size: 11.5px; font-weight: 600; color: #4ade80; background: rgba(34, 197, 94, .12); white-space: nowrap; }

/* капитал + график */
.hx-total { display: flex; flex-direction: column; overflow: hidden; }
.hx-total__num { margin-top: 8px; font: 600 46px/1.05 var(--lp-display); letter-spacing: -0.045em; font-variant-numeric: tabular-nums; }
.hx-total__delta { margin-top: 8px; display: flex; align-items: center; gap: 12px; font-size: 12px; color: var(--a-mut); }
.hx-today { white-space: nowrap; font-variant-numeric: tabular-nums; }
.hx-today em { font-style: normal; color: #4ade80; }
.hx-today em.is-neg { color: #f87171; }
.hx-chart { position: relative; flex: 1; min-height: 0; margin: 12px -18px -16px; }
.hx-chart__plot { position: absolute; inset: 0 0 26px; }
.hx-chart svg { width: 100%; height: 100%; overflow: visible; display: block; }
.hx-chart__grid { stroke: rgba(255,255,255,.05); stroke-width: 1; fill: none; vector-effect: non-scaling-stroke; }
.hx-chart__line { fill: none; stroke: url(#hx-stroke); stroke-width: 2.4; stroke-linecap: round; vector-effect: non-scaling-stroke; filter: drop-shadow(0 4px 12px rgba(91, 116, 255, .55)); }
.hx-dot {
  position: absolute; width: 9px; height: 9px; margin: -4.5px 0 0 -4.5px; border-radius: 50%; background: #fff;
  box-shadow: 0 0 0 4px rgba(125, 211, 252, .25), 0 0 18px rgba(125, 211, 252, .9);
}
.hx-dot::after { content: ''; position: absolute; inset: -9px; border-radius: 50%; border: 1.5px solid rgba(125, 211, 252, .7); animation: lp-live 2s var(--lp-ease) infinite; }
.hx-chart__x { position: absolute; left: 18px; right: 18px; bottom: 6px; display: flex; justify-content: space-between; font-size: 10.5px; color: var(--a-dim); }
.hx-chart__x .is-hide { visibility: hidden; }

/* структура */
.hx-str { display: flex; flex-direction: column; }
.hx-str__body { flex: 1; display: grid; grid-template-columns: 128px 1fr; align-items: center; gap: 16px; }
.hx-donut { position: relative; width: 128px; height: 128px; }
.hx-donut svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.hx-donut__track { fill: none; stroke: rgba(255,255,255,.05); stroke-width: 12; }
.hx-donut__seg { fill: none; stroke-width: 12; }
.hx-donut__c { position: absolute; inset: 0; display: grid; place-content: center; text-align: center; }
.hx-donut__c b { font: 600 30px/1 var(--lp-display); letter-spacing: -0.04em; }
.hx-donut__c small { margin-top: 3px; font-size: 10.5px; color: var(--a-mut); }
.hx-legend { list-style: none; margin: 0; padding: 0; display: grid; gap: 7px; }
.hx-legend li { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--a-mut); transition: opacity .4s; }
.hx-legend li.is-off { opacity: .3; }
.hx-legend i { width: 8px; height: 8px; border-radius: 3px; }
.hx-legend b { margin-left: auto; font-weight: 500; color: var(--a-ink); font-variant-numeric: tabular-nums; }

/* активы */
.hx-assets { display: flex; flex-direction: column; padding-bottom: 8px; }
.hx-rows { list-style: none; margin: 8px 0 0; padding: 0; display: grid; grid-auto-rows: 1fr; flex: 1; }
.hx-row {
  position: relative; display: grid; grid-template-columns: 30px 1fr auto 48px; align-items: center; gap: 12px;
  padding: 0 8px; margin: 0 -8px; border-radius: 9px;
}
.hx-row + .hx-row::before { content: ''; position: absolute; left: 50px; right: 8px; top: 0; height: 1px; background: var(--a-line); }
.hx-row__icon {
  display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; color: rgba(255,255,255,.3);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.12);
  background-image: repeating-linear-gradient(45deg, rgba(255,255,255,.035) 0 4px, transparent 4px 8px);
  transition: box-shadow .5s, color .5s;
}
.hx-row__name { display: grid; gap: 1px; min-width: 0; }
.hx-row__name b { font-weight: 500; font-size: 13px; color: var(--a-mut); transition: color .4s; }
.hx-row__name small { font-size: 11px; color: var(--a-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hx-row__val { font-weight: 500; font-variant-numeric: tabular-nums; color: var(--a-dim); }
.hx-row__share { justify-self: end; font-size: 11.5px; font-variant-numeric: tabular-nums; color: var(--a-mut); }
.hx-row.is-on { animation: hx-hit 1.1s var(--lp-ease); }
.hx-row.is-on .hx-row__icon {
  color: #fff; box-shadow: inset 0 1px 0 rgba(255,255,255,.3), 0 6px 16px -6px var(--c);
  background: radial-gradient(circle at 30% 25%, color-mix(in srgb, var(--c), #fff 30%), var(--c) 55%, color-mix(in srgb, var(--c), #000 25%));
}
.hx-row.is-on .hx-row__name b, .hx-row.is-on .hx-row__val { color: var(--a-ink); }
@keyframes hx-hit {
  0% { background: color-mix(in srgb, var(--c) 28%, transparent); }
  100% { background: transparent; }
}

/* дивиденды */
.hx-div { display: flex; flex-direction: column; }
.hx-div__sum { margin-top: 8px; display: flex; align-items: center; gap: 10px; }
.hx-div__sum b { font: 600 26px var(--lp-display); letter-spacing: -0.035em; }
.hx-div__bars { flex: 1; min-height: 0; margin: 12px 0; display: flex; align-items: flex-end; gap: 5px; }
.hx-div__bars i { flex: 1; border-radius: 4px 4px 2px 2px; background: linear-gradient(180deg, rgba(124, 142, 255, .55), rgba(124, 142, 255, .12)); }
.hx-div__bars i.is-now { background: linear-gradient(180deg, #a5b4ff, #5b74ff); box-shadow: 0 0 18px rgba(91, 116, 255, .6); }
.hx-div__next { display: flex; align-items: center; gap: 10px; padding-top: 10px; border-top: 1px solid var(--a-line); }
.hx-div__next > span:nth-child(2) { display: grid; gap: 1px; }
.hx-div__next small { font-size: 11px; color: var(--a-dim); }
.hx-div__next em { margin-left: auto; font-style: normal; font-weight: 600; color: #4ade80; }
.hx-date { display: grid; place-items: center; width: 36px; height: 36px; border-radius: 9px; background: rgba(255,255,255,.05); font-size: 9.5px; color: var(--a-mut); line-height: 1; }
.hx-date b { font: 600 14px var(--lp-display); color: #fff; }

/* уведомление об импорте */
.hx-toast {
  position: absolute; z-index: 4; top: 12px; right: 18px; min-width: 330px; display: flex; align-items: center; gap: 11px;
  padding: 11px 14px 11px 11px; border-radius: 13px;
  background: rgba(24, 28, 40, .97); box-shadow: inset 0 0 0 1px rgba(255,255,255,.1), 0 24px 50px -16px rgba(0,0,0,.8);
  opacity: 0; transform: translate3d(0, -12px, 0) scale(.96);
  transition: opacity .5s var(--lp-ease), transform .6s var(--lp-ease);
}
.hx-toast.is-on { opacity: 1; transform: none; }
.hx-toast__mark { flex: none; display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; background: #ffdd2d; color: #111; font: 700 15px var(--lp-display); }
.hx-toast__txt { display: grid; gap: 2px; min-width: 0; }
.hx-toast__txt b { font-size: 12px; font-weight: 600; white-space: nowrap; }
.hx-toast__txt small { font-size: 12px; color: var(--a-mut); white-space: nowrap; }
.hx-toast em { margin-left: auto; padding-left: 10px; font-style: normal; font-weight: 600; font-size: 12.5px; white-space: nowrap; }

/* ---------- мобильная версия экрана ---------- */
.hx-app--m { border-radius: 22px; font-size: 13.5px; }
.hx-app--m .hx-chrome { height: 36px; grid-template-columns: auto 1fr auto; gap: 12px; }
.hx-app--m .hx-chrome__sync { display: none; }
.hx-app--m .hx-chrome::after { content: ''; width: 47px; }
.hx-app--m .hx-chrome__url { justify-self: center; }
.hx-app--m .hx-main { padding: 14px 14px 16px; gap: 12px; }
.hx-app--m .hx-head { min-height: 30px; }
.hx-app--m .hx-head__t b { font-size: 18px; }
.hx-app--m .hx-done { margin: 0 0 0 auto; height: 26px; }
.hx-app--m .hx-seg { display: none; }
.hx-app--m .hx-grid-a { grid-template-columns: 1fr; grid-template-rows: 252px 1fr; gap: 12px; }
.hx-app--m .hx-total__num { font-size: 34px; }
.hx-app--m .hx-total__delta { gap: 8px; }
.hx-app--m .hx-today { font-size: 11.5px; }
.hx-alloc { margin-top: 14px; display: flex; gap: 3px; height: 6px; }
.hx-alloc i { flex: 0 1 0; min-width: 0; border-radius: 3px; }
.hx-app--m .hx-row { grid-template-columns: 32px 1fr auto; }
.hx-app--m .hx-row__icon { width: 32px; height: 32px; }
.hx-app--m .hx-row + .hx-row::before { left: 52px; }
.hx-app--m .hx-toast { top: auto; bottom: 14px; left: 14px; right: 14px; min-width: 0; }

/* ---------- фишки активов ---------- */
.hx-chips { position: absolute; inset: 0; z-index: 4; pointer-events: none; }
.hx-chip { position: absolute; left: 0; top: 0; will-change: transform, opacity; }
.hx-chip__body {
  display: flex; align-items: center; gap: 12px; padding: 9px 18px 9px 9px; border-radius: 18px;
  background: linear-gradient(180deg, rgba(44, 49, 66, .86), rgba(22, 25, 36, .86));
  box-shadow:
    inset 0 0 0 1px rgba(255,255,255,.12), inset 0 1px 0 rgba(255,255,255,.18),
    0 24px 50px -18px rgba(0,0,0,.75), 0 18px 46px -22px var(--c);
  backdrop-filter: blur(16px) saturate(1.4); -webkit-backdrop-filter: blur(16px) saturate(1.4);
  transform: scale(var(--z));
  animation: hx-float var(--t) ease-in-out var(--d) infinite;
}
@keyframes hx-float {
  0%, 100% { transform: translate3d(0, 0, 0) scale(var(--z)); }
  50% { transform: translate3d(0, -9px, 0) rotate(.6deg) scale(var(--z)); }
}
.hx-chip__icon {
  flex: none; display: grid; place-items: center; width: 42px; height: 42px; border-radius: 13px; color: #fff;
  background: radial-gradient(circle at 30% 22%, color-mix(in srgb, var(--c), #fff 35%), var(--c) 55%, color-mix(in srgb, var(--c), #000 30%));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), inset 0 -2px 6px rgba(0,0,0,.2), 0 8px 22px -8px var(--c);
}
.hx-chip__txt { display: grid; gap: 2px; white-space: nowrap; }
.hx-chip__txt b { font: 600 15px var(--lp-display); letter-spacing: -0.015em; }
.hx-chip__txt small { font-size: 12.5px; color: rgba(225, 230, 248, .6); font-variant-numeric: tabular-nums; }
.hx-chip__txt em { font-style: normal; margin-left: 4px; color: #4ade80; }
.hx-chip__txt em.is-neg { color: #f87171; }

.hx[data-chips='pill'] .hx-chip__body { padding: 5px 14px 5px 5px; gap: 9px; border-radius: 99px; }
.hx[data-chips='pill'] .hx-chip__icon { width: 30px; height: 30px; border-radius: 50%; }
.hx[data-chips='pill'] .hx-chip__txt b { font-size: 13.5px; }
.hx[data-chips='pill'] .hx-chip__txt small { display: none; }
.hx[data-chips='token'] .hx-chip__body { padding: 4px; border-radius: 50%; }
.hx[data-chips='token'] .hx-chip__icon { width: 38px; height: 38px; border-radius: 50%; }
.hx[data-chips='token'] .hx-chip__txt { display: none; }

/* ---------- подсказка ---------- */
.hx-hint {
  position: absolute; z-index: 5; left: 50%; bottom: 22px; translate: -50% 0;
  display: inline-flex; align-items: center; gap: 10px; padding: 8px 16px 8px 10px; border-radius: 99px; white-space: nowrap;
  font-size: 13px; color: rgba(235, 238, 255, .8);
  background: rgba(14, 16, 24, .72); box-shadow: inset 0 0 0 1px rgba(255,255,255,.1), 0 16px 40px -12px rgba(0,0,0,.7);
  backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
}
.hx-hint__mouse { position: relative; width: 16px; height: 24px; border-radius: 8px; box-shadow: inset 0 0 0 1.5px rgba(255,255,255,.55); }
.hx-hint__mouse i { position: absolute; left: 50%; top: 5px; width: 2px; height: 5px; margin-left: -1px; border-radius: 1px; background: #fff; animation: hx-wheel 1.8s var(--lp-ease) infinite; }
@keyframes hx-wheel { 0% { transform: translateY(0); opacity: 1; } 70% { transform: translateY(8px); opacity: 0; } 100% { opacity: 0; } }

/* ---------- адаптив ---------- */
@media (max-width: 760px) {
  .hx-title { font-size: 10.8vw; letter-spacing: -0.045em; }
  .hx-eyebrow { font-size: 12.5px; }
  .hx-lead { font-size: 15.5px; }
  .hx-cta { width: 100%; max-width: 360px; }
  .hx-cta .lp-btn { flex: 1 1 100%; }
  .hx-hint { display: none; }
}
@media (max-height: 760px) and (min-width: 761px) {
  .hx-title { font-size: clamp(44px, 5.6vw, 80px); }
  .hx-lead { font-size: 16px; }
}

/* без анимаций: всё статично, без закрепления */
.hx.is-static .hx-pin { height: auto; padding-bottom: 48px; }
.hx.is-static .hx-stage { position: relative; inset: auto; margin-top: 40px; perspective: none; }
.hx.is-static .hx-tilt { position: relative; margin: 0 auto; }
.hx.is-static .hx-chips, .hx.is-static .hx-hint { display: none; }
.hx.is-static .hx-done, .hx.is-static .hx-app__ring { opacity: 1; }
@media (prefers-reduced-motion: reduce) {
  .hx-aurora i, .hx-chip__body { animation: none; }
}
</style>
