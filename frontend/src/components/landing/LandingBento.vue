<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import LandingIcon from './LandingIcon.vue'
import { formatRub, prefersReducedMotion } from './useLandingMotion'

gsap.registerPlugin(ScrollTrigger)

/* ---------- сцена 1: доходность ---------- */
const PERIODS = { '1М': 22, '6М': 26, '1Г': 52, 'Всё': 60 }
const GROWTH = { '1М': 0.021, '6М': 0.094, '1Г': 0.184, 'Всё': 0.612 }
const period = ref('1Г')
function series(key) {
  const n = PERIODS[key]
  const g = GROWTH[key]
  let seed = n * 7 + 3
  const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280)
  const start = 2847320 / (1 + g)
  // сглаженное блуждание вокруг тренда — без «пилы»
  let noise = 0
  return Array.from({ length: n }, (_, i) => {
    if (i === n - 1) return 2847320
    noise = noise * 0.75 + (rnd() - 0.5) * start * 0.018
    return start * (1 + (g * i) / (n - 1)) + noise
  })
}
const data = computed(() => series(period.value))
const W = 1000
const H = 300
const pts = computed(() => {
  const d = data.value
  const min = Math.min(...d)
  const max = Math.max(...d)
  return d.map((v, i) => [(i / (d.length - 1)) * W, 24 + (1 - (v - min) / (max - min || 1)) * (H - 48)])
})
const line = computed(() => pts.value.reduce((s, [x, y], i, a) => {
  if (!i) return `M${x},${y}`
  const [px, py] = a[i - 1]
  const cx = (px + x) / 2
  return `${s} C${cx},${py} ${cx},${y} ${x},${y}`
}, ''))
const area = computed(() => `${line.value} L${W},${H} L0,${H} Z`)
const hover = ref(-1)
const hi = computed(() => (hover.value < 0 ? data.value.length - 1 : hover.value))
const hiPt = computed(() => pts.value[hi.value])
const profit = computed(() => data.value[hi.value] - data.value[0])
const profitPct = computed(() => ((profit.value / data.value[0]) * 100).toFixed(1).replace('.', ','))
function onChartMove(e) {
  const r = e.currentTarget.getBoundingClientRect()
  hover.value = Math.round(Math.min(1, Math.max(0, (e.clientX - r.left) / r.width)) * (data.value.length - 1))
}
/* подписи событий прямо на графике */
const NOTES = [
  { f: 0.22, icon: 'wallet', t: 'Дивиденд · Сбербанк', v: '+6 920 ₽', c: '#12b76a' },
  { f: 0.55, icon: 'plus', t: 'Пополнение', v: '+50 000 ₽', c: '#3d5afe' },
  { f: 0.82, icon: 'bond', t: 'Купон · ОФЗ 26238', v: '+1 794 ₽', c: '#22b8cf' }
]
const notes = computed(() => NOTES.map((n) => {
  const p = pts.value[Math.round(n.f * (pts.value.length - 1))]
  return { ...n, x: (p[0] / W) * 100, y: (p[1] / H) * 100 }
}))
const lineEl = ref(null)
function setPeriod(p) {
  if (p === period.value) return
  period.value = p
  requestAnimationFrame(() => {
    if (!lineEl.value || prefersReducedMotion()) return
    gsap.fromTo(lineEl.value, { strokeDashoffset: 1 }, { strokeDashoffset: 0, duration: 1.1, ease: 'power3.out' })
  })
}

/* ---------- сцена 2: дивиденды ---------- */
const months = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
const payouts = [2140, 1380, 3920, 4610, 7240, 12980, 18420, 9860, 3310, 5470, 2980, 6890]
const payers = ['ОФЗ 26238', 'МТС', 'Сургутнефтегаз', 'НЛМК', 'Татнефть', 'Лукойл, МТС', 'Сбербанк, Лукойл', 'Северсталь', 'ОФЗ 26238', 'Татнефть', 'ОФЗ 26238', 'Лукойл, X5']
const maxPay = Math.max(...payouts)
const yearPay = payouts.reduce((a, b) => a + b, 0)
const month = ref(6)
const divShown = reactive({ v: 0 })

/* ---------- сцена 3: структура ---------- */
const structure = [
  { k: 'Акции', v: 42, c: '#3d5afe', d: 'Сбербанк, Лукойл, Яндекс и ещё 9' },
  { k: 'Облигации', v: 26, c: '#22b8cf', d: 'ОФЗ и корпоративные, купон 7–14%' },
  { k: 'Фонды', v: 14, c: '#8b5cf6', d: 'Индексные БПИФ на Мосбирже' },
  { k: 'Валюта', v: 10, c: '#12b76a', d: 'USD, CNY — по курсу ЦБ' },
  { k: 'Крипто', v: 8, c: '#ff7a45', d: 'BTC, ETH — ручной учёт' }
]
const SC = 2 * Math.PI * 38
const segs = (() => {
  let off = 0
  return structure.map((s) => {
    const len = (s.v / 100) * SC
    const seg = { ...s, dash: `${len - 2.2} ${SC}`, off: -off }
    off += len
    return seg
  })
})()
const LAYERS = 9
const seg = ref(-1)
const segShown = computed(() => structure[seg.value < 0 ? 0 : seg.value])

/* ---------- нижний ряд ---------- */
const POOL = [
  { k: 'Дивиденд', a: 'Лукойл', v: '+9 960 ₽', icon: 'wallet', pos: true },
  { k: 'Покупка', a: 'Яндекс × 4', v: '−16 840 ₽', icon: 'plus' },
  { k: 'Купон', a: 'ОФЗ 26238', v: '+1 794 ₽', icon: 'bond', pos: true },
  { k: 'Покупка', a: 'Т-Технологии × 2', v: '−6 412 ₽', icon: 'plus' },
  { k: 'Дивиденд', a: 'Сбербанк', v: '+6 920 ₽', icon: 'wallet', pos: true },
  { k: 'Продажа', a: 'Газпром × 50', v: '+7 215 ₽', icon: 'arrow-up-right', pos: true },
  { k: 'Комиссия', a: 'Т-Инвестиции', v: '−18 ₽', icon: 'receipt' }
]
const feed = ref(POOL.slice(0, 3).map((x, i) => ({ ...x, id: i })))
let feedIdx = 3
let feedTimer = null

const portfolios = [
  { t: 'Брокерский', v: 1684200, c: '#3d5afe' },
  { t: 'ИИС-3', v: 742500, c: '#8b5cf6' },
  { t: 'Семейный', v: 420620, c: '#22b8cf' }
]

const RATES = { RUB: 1, USD: 96.4, EUR: 104.2, CNY: 13.3 }
const SIGNS = { RUB: '₽', USD: '$', EUR: '€', CNY: '¥' }
const cur = ref('RUB')
const curVal = reactive({ v: 2847320 })
function setCur(c) {
  cur.value = c
  gsap.to(curVal, { v: 2847320 / RATES[c], duration: 0.9, ease: 'expo.out' })
}
const curText = computed(() => Math.round(curVal.v).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ' + SIGNS[cur.value])

/* подсветка материала под курсором: и заливка, и градиентная рамка */
function spot(e) {
  const el = e.currentTarget
  const r = el.getBoundingClientRect()
  el.style.setProperty('--mx', `${e.clientX - r.left}px`)
  el.style.setProperty('--my', `${e.clientY - r.top}px`)
}

const root = ref(null)
let ctx = null
let feedST = null

onMounted(() => {
  const reduced = prefersReducedMotion()
  ctx = gsap.context(() => {
    // все сцены «въезжают» и выпрямляются по скроллу
    gsap.utils.toArray('.sc-in').forEach((el) => {
      el.classList.add('is-in')
      if (reduced) return
      gsap.fromTo(el, { y: 90, scale: 0.94, opacity: 0.2 }, {
        y: 0, scale: 1, opacity: 1, ease: 'none',
        scrollTrigger: { trigger: el, start: 'top bottom', end: 'top 62%', scrub: 0.6 }
      })
    })
    if (reduced) { divShown.v = yearPay; return }

    // сцена 1: линия рисуется скроллом, затем всплывают подписи
    const t1 = gsap.timeline({ scrollTrigger: { trigger: '.sc-perf', start: 'top 70%', end: 'center 45%', scrub: 0.8 } })
    t1.fromTo('.sc-perf__line', { strokeDashoffset: 1 }, { strokeDashoffset: 0, ease: 'none', duration: 1 })
      .from('.sc-perf__area', { opacity: 0, duration: 0.5 }, 0.4)
      .from('.sc-note', { opacity: 0, y: 14, scale: 0.9, stagger: 0.18, duration: 0.25 }, 0.3)
      .from('.sc-kpi', { opacity: 0, y: 20, stagger: 0.08, duration: 0.3 }, 0.5)

    // сцена 2: столбцы растут, сумма за год досчитывается
    gsap.timeline({ scrollTrigger: { trigger: '.sc-div', start: 'top 65%', end: 'center 50%', scrub: 0.8 } })
      .from('.sc-bar', { scaleY: 0, stagger: 0.05, ease: 'none', duration: 0.5 })
      .to(divShown, { v: yearPay, ease: 'none', duration: 1 }, 0)

    // сцена 3: слои пончика складываются в объём
    gsap.timeline({ scrollTrigger: { trigger: '.sc-str', start: 'top 70%', end: 'center 50%', scrub: 0.8 } })
      .from('.st-seg', { z: 160, opacity: 0, stagger: 0.12, ease: 'none', duration: 0.5 })
      .from('.st-row', { opacity: 0, x: 24, stagger: 0.08, duration: 0.3 }, 0.2)
  }, root.value)

  feedST = ScrollTrigger.create({
    trigger: '.sc-card--feed',
    start: 'top bottom',
    end: 'bottom top',
    onToggle(self) {
      clearInterval(feedTimer)
      if (!self.isActive || reduced) return
      feedTimer = setInterval(() => {
        const next = POOL[feedIdx % POOL.length]
        feed.value = [{ ...next, id: feedIdx++ }, ...feed.value].slice(0, 3)
      }, 2200)
    }
  })
})

onUnmounted(() => {
  clearInterval(feedTimer)
  feedST?.kill()
  ctx?.revert()
})
</script>

<template>
  <section id="features" ref="root" class="sc">
    <div class="lp-container">
      <header class="lp-head lp-head--center">
        <span class="lp-eyebrow">Возможности</span>
        <h2 class="lp-h2">Каждая цифра —<br /><span class="lp-dim">на своём месте.</span></h2>
        <p class="lp-sub">Ответ на вопрос «как дела у моих денег?» занимает секунду. Всё остальное — в одном клике.</p>
      </header>

      <!-- СЦЕНА 1 — доходность -->
      <article class="sc-perf mat sc-in" @pointermove="spot">
        <div class="sc-perf__top">
          <div class="sc-title">
            <span class="sc-badge"><LandingIcon name="trend" :size="18" :stroke="1.8" /></span>
            <h3>Реальная доходность</h3>
            <p>XIRR с&nbsp;учётом пополнений, комиссий и&nbsp;налогов. Не&nbsp;«рост цены», а&nbsp;сколько вы&nbsp;действительно заработали.</p>
          </div>
          <div class="sc-perf__side">
            <div class="sc-perf__num">
              <b>{{ formatRub(data[hi]) }}</b>
              <span :class="{ 'is-neg': profit < 0 }">
                <LandingIcon name="arrow-up-right" :size="13" :stroke="2" />
                {{ profit >= 0 ? '+' : '−' }}{{ formatRub(Math.abs(profit)) }} · {{ profitPct }}%
              </span>
            </div>
            <div class="sc-tabs" role="tablist">
              <button v-for="(_, p) in PERIODS" :key="p" type="button" :class="{ 'is-on': period === p }" @click="setPeriod(p)">{{ p }}</button>
            </div>
          </div>
        </div>

        <div class="sc-perf__chart" @pointermove="onChartMove" @pointerleave="hover = -1">
          <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none">
            <defs>
              <linearGradient id="scArea" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stop-color="#3d5afe" stop-opacity=".22" />
                <stop offset=".7" stop-color="#3d5afe" stop-opacity=".03" />
                <stop offset="1" stop-color="#3d5afe" stop-opacity="0" />
              </linearGradient>
              <linearGradient id="scLine" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0" stop-color="#8b5cf6" />
                <stop offset=".6" stop-color="#3d5afe" />
                <stop offset="1" stop-color="#22b8cf" />
              </linearGradient>
            </defs>
            <path :d="`M0,${H * 0.25} H${W} M0,${H * 0.5} H${W} M0,${H * 0.75} H${W}`" class="sc-perf__grid" />
            <path :d="area" fill="url(#scArea)" class="sc-perf__area" />
            <path :d="line" class="sc-perf__glow" />
            <path ref="lineEl" :d="line" pathLength="1" class="sc-perf__line" />
          </svg>
          <div
            v-for="n in notes"
            :key="n.t"
            class="sc-note"
            :class="{ 'is-low': n.y < 40 }"
            :style="{ left: n.x + '%', top: n.y + '%', '--c': n.c }"
          >
            <i class="sc-note__pin" />
            <span class="sc-note__body">
              <span class="sc-note__icon"><LandingIcon :name="n.icon" :size="13" :stroke="1.8" /></span>
              {{ n.t }} <b>{{ n.v }}</b>
            </span>
          </div>
          <span class="sc-perf__x" :style="{ left: (hiPt[0] / W) * 100 + '%' }" :class="{ 'is-on': hover >= 0 }" />
          <span class="sc-perf__dot" :style="{ left: (hiPt[0] / W) * 100 + '%', top: (hiPt[1] / H) * 100 + '%' }" />
        </div>

        <ul class="sc-kpis">
          <li class="sc-kpi"><small>XIRR, годовых</small><b>18,4%</b></li>
          <li class="sc-kpi"><small>Дивиденды и купоны</small><b>{{ formatRub(yearPay) }}</b></li>
          <li class="sc-kpi"><small>Комиссии и налоги</small><b>−4 120 ₽</b></li>
          <li class="sc-kpi"><small>Против индекса Мосбиржи</small><b class="is-pos">+6,2 п.п.</b></li>
        </ul>
      </article>

      <!-- СЦЕНА 2 — дивиденды (тёмная) -->
      <article class="sc-div sc-in" @pointermove="spot">
        <div class="sc-div__glow" aria-hidden="true" />
        <div class="sc-div__copy">
          <div class="sc-title sc-title--dark">
            <span class="sc-badge sc-badge--dark"><LandingIcon name="calendar" :size="18" :stroke="1.8" /></span>
            <h3>Дивидендный календарь</h3>
            <p>Все будущие выплаты и&nbsp;купоны по&nbsp;месяцам. Вы&nbsp;знаете, когда придут деньги, ещё до&nbsp;отсечки.</p>
          </div>
          <div class="sc-div__total">
            <small>Ожидается за 12 месяцев</small>
            <b>{{ formatRub(divShown.v) }}</b>
          </div>
          <div class="sc-div__month">
            <span class="sc-div__mname">{{ months[month] }}</span>
            <span class="sc-div__mval">{{ formatRub(payouts[month]) }}</span>
            <span class="sc-div__mwho">{{ payers[month] }}</span>
          </div>
        </div>

        <div class="sc-div__viz">
          <div class="sc-div__plane" @pointerleave="month = 6">
            <button
              v-for="(m, i) in months"
              :key="m"
              type="button"
              class="sc-col"
              :class="{ 'is-on': month === i }"
              :aria-label="`${m}: ${formatRub(payouts[i])}`"
              @pointerenter="month = i"
              @focus="month = i"
            >
              <span class="sc-bar" :style="{ height: (payouts[i] / maxPay) * 100 + '%' }"><i /></span>
              <small>{{ m }}</small>
            </button>
          </div>
        </div>
      </article>

      <!-- СЦЕНА 3 — структура -->
      <article class="sc-str mat sc-in" @pointermove="spot">
        <div class="sc-str__viz" @pointerleave="seg = -1">
          <div class="st-iso">
            <div
              v-for="(s, i) in segs"
              :key="s.k"
              class="st-seg"
            >
              <div class="st-seg__lift" :class="{ 'is-on': seg === i, 'is-dim': seg >= 0 && seg !== i }">
                <svg
                  v-for="l in LAYERS"
                  :key="l"
                  viewBox="0 0 100 100"
                  class="st-layer"
                  :class="{ 'is-top': l === LAYERS }"
                  :style="{ '--z': l * 2.4 + 'px' }"
                >
                  <circle
                    cx="50" cy="50" r="38"
                    :stroke="s.c"
                    :stroke-dasharray="s.dash"
                    :stroke-dashoffset="s.off"
                    @pointerenter="l === LAYERS && (seg = i)"
                  />
                </svg>
              </div>
            </div>
          </div>
          <div class="st-shadow" aria-hidden="true" />
        </div>

        <div class="sc-str__copy">
          <div class="sc-title">
            <span class="sc-badge"><LandingIcon name="pie" :size="18" :stroke="1.8" /></span>
            <h3>Структура без перекосов</h3>
            <p>Классы активов, секторы и&nbsp;валюты. Наведите на&nbsp;сегмент, чтобы увидеть, из&nbsp;чего он&nbsp;состоит.</p>
          </div>
          <div class="st-focus">
            <b :style="{ color: segShown.c }">{{ segShown.v }}%</b>
            <span><strong>{{ segShown.k }}</strong>{{ segShown.d }}</span>
          </div>
          <ul class="st-list">
            <li
              v-for="(s, i) in structure"
              :key="s.k"
              class="st-row"
              :class="{ 'is-on': seg === i, 'is-dim': seg >= 0 && seg !== i }"
              @pointerenter="seg = i"
              @pointerleave="seg = -1"
            >
              <span class="st-row__name"><i :style="{ background: s.c }" />{{ s.k }}</span>
              <span class="st-row__bar"><i :style="{ width: s.v / 0.42 + '%', background: s.c }" /></span>
              <b>{{ s.v }}%</b>
            </li>
          </ul>
        </div>
      </article>

      <!-- НИЖНИЙ РЯД -->
      <div class="sc-row">
        <article class="sc-card sc-card--feed mat sc-in" @pointermove="spot">
          <div class="sc-title sc-title--sm">
            <span class="sc-badge"><LandingIcon name="sync" :size="16" :stroke="1.8" /></span>
            <h3>Сделки — сами</h3>
            <p>История загружается из&nbsp;брокера автоматически.</p>
          </div>
          <TransitionGroup name="sc-feed" tag="ul" class="sc-feed">
            <li v-for="f in feed" :key="f.id">
              <span class="sc-feed__icon"><LandingIcon :name="f.icon" :size="14" :stroke="1.8" /></span>
              <span class="sc-feed__txt"><b>{{ f.k }}</b><small>{{ f.a }}</small></span>
              <em :class="{ 'is-pos': f.pos }">{{ f.v }}</em>
            </li>
          </TransitionGroup>
        </article>

        <article class="sc-card sc-card--stack mat sc-in" @pointermove="spot">
          <div class="sc-title sc-title--sm">
            <span class="sc-badge"><LandingIcon name="wallet" :size="16" :stroke="1.8" /></span>
            <h3>Несколько портфелей</h3>
            <p>ИИС, брокерский, семейный — отдельно и&nbsp;вместе.</p>
          </div>
          <div class="sc-stack">
            <div v-for="(p, i) in portfolios" :key="p.t" class="sc-stack__card" :style="{ '--i': i, '--c': p.c }">
              <span><i />{{ p.t }}</span>
              <b>{{ formatRub(p.v) }}</b>
            </div>
          </div>
        </article>

        <article class="sc-card sc-card--cur mat sc-in" @pointermove="spot">
          <div class="sc-title sc-title--sm">
            <span class="sc-badge"><LandingIcon name="globe" :size="16" :stroke="1.8" /></span>
            <h3>Любая валюта отчёта</h3>
            <p>Курсы ЦБ подтягиваются сами.</p>
          </div>
          <div class="sc-cur">
            <b class="sc-cur__val">{{ curText }}</b>
            <div class="sc-tabs sc-tabs--full">
              <button v-for="(_, c) in RATES" :key="c" type="button" :class="{ 'is-on': cur === c }" @click="setCur(c)">{{ c }}</button>
            </div>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<style scoped>
.sc {
  position: relative; padding: var(--lp-section) 0;
  background: linear-gradient(180deg, var(--lp-bg) 0, var(--lp-bg-2) 220px, var(--lp-bg-2) calc(100% - 220px), var(--lp-bg) 100%);
}

/* ---------- материал: светлое «стекло» с внутренним бликом, мягкой тенью, шумом и рамкой за курсором ---------- */
.mat {
  --mx: 50%; --my: 50%;
  position: relative; isolation: isolate; overflow: hidden;
  border-radius: 32px;
  background:
    radial-gradient(600px circle at var(--mx) var(--my), rgba(61,90,254,.05), transparent 45%),
    linear-gradient(180deg, #fff, #fbfbfd);
  box-shadow:
    inset 0 1px 0 #fff,
    0 0 0 1px rgba(11,13,18,.06),
    0 1px 2px rgba(11,13,18,.04),
    0 12px 24px -12px rgba(30,40,90,.08),
    0 40px 80px -40px rgba(30,40,90,.22);
}
.mat::before {
  content: ''; position: absolute; inset: 0; border-radius: inherit; padding: 1px; pointer-events: none; z-index: 5;
  background: radial-gradient(360px circle at var(--mx) var(--my), rgba(61,90,254,.7), rgba(139,92,246,.35) 40%, transparent 70%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor; mask-composite: exclude;
  opacity: 0; transition: opacity .5s;
}
.mat:hover::before { opacity: 1; }
.mat::after {
  content: ''; position: absolute; inset: 0; z-index: -1; pointer-events: none; opacity: .35; mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .05 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}

/* ---------- общие ---------- */
.sc-in { will-change: transform; }
.sc-title { max-width: 440px; }
.sc-title h3 { margin-top: 18px; font-family: var(--lp-display); font-size: clamp(26px, 2.6vw, 36px); font-weight: 600; letter-spacing: -0.035em; line-height: 1.08; color: var(--lp-ink); }
.sc-title p { margin-top: 12px; font-size: 16px; line-height: 1.55; color: var(--lp-muted); }
.sc-title--sm h3 { margin-top: 16px; font-size: 21px; letter-spacing: -0.025em; }
.sc-title--sm p { margin-top: 6px; font-size: 14.5px; }
.sc-title--dark h3 { color: #fff; }
.sc-title--dark p { color: rgba(255,255,255,.58); }
.sc-badge {
  display: inline-grid; place-items: center; width: 40px; height: 40px; border-radius: 13px; color: #fff;
  background: linear-gradient(150deg, #5b74ff, #3d5afe 50%, #2a3fd6);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), inset 0 -2px 4px rgba(0,0,0,.15), 0 10px 20px -8px rgba(61,90,254,.7);
}
.sc-title--sm .sc-badge { width: 36px; height: 36px; border-radius: 11px; }
.sc-badge--dark {
  background: linear-gradient(150deg, rgba(255,255,255,.18), rgba(255,255,255,.04));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.25), inset 0 0 0 1px rgba(255,255,255,.1), 0 10px 30px -10px rgba(139,92,246,.8);
}
.sc-tabs { display: inline-flex; gap: 2px; padding: 3px; border-radius: 12px; background: var(--lp-bg-2); box-shadow: inset 0 1px 2px rgba(11,13,18,.06); }
.sc-tabs button {
  border: 0; background: none; font: inherit; font-size: 13px; font-weight: 500; color: var(--lp-muted);
  padding: 7px 13px; border-radius: 9px; cursor: pointer; transition: color .25s, background .25s, box-shadow .25s;
}
.sc-tabs button:hover { color: var(--lp-ink); }
.sc-tabs button.is-on { background: #fff; color: var(--lp-ink); box-shadow: 0 1px 2px rgba(11,13,18,.1), 0 2px 8px -2px rgba(11,13,18,.12); }

/* ---------- сцена 1 ---------- */
.sc-perf { margin-top: clamp(48px, 6vw, 80px); padding: clamp(24px, 3.4vw, 48px); }
.sc-perf__top { display: flex; justify-content: space-between; align-items: flex-end; gap: 24px 40px; flex-wrap: wrap; }
.sc-perf__side { display: flex; flex-direction: column; align-items: flex-end; gap: 16px; }
.sc-perf__num { text-align: right; }
.sc-perf__num b {
  display: block; font-family: var(--lp-display); font-size: clamp(36px, 4.4vw, 60px); font-weight: 600; letter-spacing: -0.045em; line-height: 1;
  color: var(--lp-ink); font-variant-numeric: tabular-nums;
}
.sc-perf__num span {
  display: inline-flex; align-items: center; gap: 4px; margin-top: 10px; padding: 4px 10px; border-radius: 99px;
  font-size: 13.5px; font-weight: 600; color: var(--lp-green); background: rgba(18,183,106,.1); font-variant-numeric: tabular-nums;
}
.sc-perf__num span.is-neg { color: var(--lp-red); background: rgba(229,72,77,.1); }
.sc-perf__chart { position: relative; height: clamp(220px, 26vw, 340px); margin-top: 40px; cursor: crosshair; touch-action: pan-y; }
.sc-perf__chart svg { width: 100%; height: 100%; display: block; overflow: visible; }
.sc-perf__grid { stroke: rgba(11,13,18,.07); stroke-dasharray: 3 6; vector-effect: non-scaling-stroke; }
.sc-perf__line { fill: none; stroke: url(#scLine); stroke-width: 2.5; vector-effect: non-scaling-stroke; stroke-dasharray: 1; stroke-linecap: round; transition: d .6s var(--lp-ease); }
.sc-perf__glow { fill: none; stroke: rgba(61,90,254,.25); stroke-width: 10; vector-effect: non-scaling-stroke; filter: blur(8px); transition: d .6s var(--lp-ease); }
.sc-perf__area { transition: d .6s var(--lp-ease); }
.sc-perf__x { position: absolute; top: 0; bottom: 0; width: 1px; background: linear-gradient(180deg, transparent, rgba(11,13,18,.2), transparent); opacity: 0; transition: opacity .2s; pointer-events: none; }
.sc-perf__x.is-on { opacity: 1; }
.sc-perf__dot {
  position: absolute; width: 14px; height: 14px; margin: -7px 0 0 -7px; border-radius: 50%; pointer-events: none;
  background: #fff; border: 3px solid var(--lp-blue); box-shadow: 0 0 0 7px rgba(61,90,254,.14), 0 4px 12px rgba(61,90,254,.4);
  transition: top .25s var(--lp-ease), left .12s linear;
}
.sc-note { position: absolute; z-index: 2; pointer-events: none; }
.sc-note__pin {
  position: absolute; left: -5px; top: -5px; width: 10px; height: 10px; border-radius: 50%;
  background: #fff; border: 2px solid var(--c); box-shadow: 0 0 0 4px color-mix(in srgb, var(--c) 18%, transparent);
}
.sc-note__body {
  position: absolute; left: 0; bottom: 18px; translate: -50% 0; white-space: nowrap;
  display: flex; align-items: center; gap: 8px; padding: 6px 12px 6px 6px; border-radius: 99px;
  font-size: 12.5px; color: var(--lp-ink-2);
  background: rgba(255,255,255,.85); backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
  box-shadow: inset 0 1px 0 #fff, 0 0 0 1px rgba(11,13,18,.06), 0 10px 24px -10px rgba(30,40,90,.3);
}
.sc-note.is-low .sc-note__body { bottom: auto; top: 18px; }
.sc-note__body b { color: var(--c); font-weight: 600; }
.sc-note__icon { display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; color: #fff; background: var(--c); }
.sc-kpis { display: grid; grid-template-columns: repeat(4, 1fr); margin: 32px 0 0; padding: 24px 0 0; list-style: none; border-top: 1px solid var(--lp-line); }
.sc-kpi + .sc-kpi { padding-left: 24px; border-left: 1px solid var(--lp-line); }
.sc-kpi small { display: block; font-size: 13px; color: var(--lp-muted); }
.sc-kpi b { display: block; margin-top: 6px; font-family: var(--lp-display); font-size: clamp(20px, 2vw, 26px); font-weight: 600; letter-spacing: -0.03em; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.sc-kpi b.is-pos { color: var(--lp-green); }

/* ---------- сцена 2 (тёмная) ---------- */
.sc-div {
  --mx: 50%; --my: 50%;
  position: relative; isolation: isolate; overflow: hidden;
  display: grid; grid-template-columns: 5fr 7fr; gap: 40px; align-items: stretch;
  margin-top: 24px; padding: clamp(24px, 3.4vw, 48px); border-radius: 32px;
  background:
    radial-gradient(500px circle at var(--mx) var(--my), rgba(139,92,246,.12), transparent 50%),
    linear-gradient(160deg, #141826, #0a0c13 60%);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.1), inset 0 0 0 1px rgba(255,255,255,.06), 0 50px 100px -40px rgba(11,13,40,.6);
  color: #fff;
}
.sc-div__glow {
  position: absolute; right: -10%; bottom: -40%; width: 70%; height: 90%; z-index: -1; pointer-events: none;
  background: radial-gradient(50% 50% at 50% 50%, rgba(61,90,254,.4), rgba(139,92,246,.18) 50%, transparent 75%);
  filter: blur(40px);
}
.sc-div__copy { display: flex; flex-direction: column; gap: 28px; }
.sc-div__total small { display: block; font-size: 13px; color: rgba(255,255,255,.5); }
.sc-div__total b {
  display: block; margin-top: 6px; font-family: var(--lp-display); font-size: clamp(40px, 5vw, 68px); font-weight: 600; letter-spacing: -0.045em; line-height: 1;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(180deg, #fff 30%, #a5b4ff); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.sc-div__month {
  margin-top: auto; display: grid; grid-template-columns: auto 1fr; gap: 2px 14px; align-items: baseline;
  padding: 16px 18px; border-radius: 18px;
  background: rgba(255,255,255,.05); box-shadow: inset 0 1px 0 rgba(255,255,255,.08), inset 0 0 0 1px rgba(255,255,255,.07);
}
.sc-div__mname { grid-row: span 2; font-family: var(--lp-display); font-size: 28px; font-weight: 600; letter-spacing: -0.03em; color: #a5b4ff; }
.sc-div__mval { font-size: 18px; font-weight: 600; font-variant-numeric: tabular-nums; }
.sc-div__mwho { font-size: 13px; color: rgba(255,255,255,.5); }
.sc-div__viz { position: relative; perspective: 1200px; min-height: 380px; display: flex; align-items: flex-end; }
.sc-div__plane {
  width: 100%; height: 340px; display: grid; grid-template-columns: repeat(12, 1fr); gap: clamp(4px, .8vw, 10px);
  transform: rotateX(14deg) rotateY(-16deg); transform-origin: 50% 100%;
  padding-bottom: 28px; position: relative;
}
.sc-div__plane::after {
  content: ''; position: absolute; left: -4%; right: -4%; bottom: 22px; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,.3), transparent);
}
.sc-col { position: relative; border: 0; padding: 0; background: none; cursor: pointer; display: flex; flex-direction: column; justify-content: flex-end; align-items: stretch; font: inherit; height: 100%; }
.sc-bar {
  position: relative; display: block; min-height: 8px; border-radius: 10px 10px 4px 4px; transform-origin: bottom;
  background: linear-gradient(180deg, rgba(165,180,255,.45), rgba(61,90,254,.12));
  box-shadow: inset 0 1px 0 rgba(255,255,255,.35), inset 0 0 0 1px rgba(165,180,255,.18);
  transition: background .3s, box-shadow .3s;
}
.sc-bar i {
  position: absolute; left: 0; right: 0; top: 100%; height: 60%; border-radius: 4px; pointer-events: none;
  background: inherit; opacity: .25; transform: scaleY(-1); transform-origin: top;
  -webkit-mask-image: linear-gradient(180deg, #000, transparent 80%); mask-image: linear-gradient(180deg, #000, transparent 80%);
  filter: blur(2px);
}
.sc-col:hover .sc-bar { background: linear-gradient(180deg, rgba(165,180,255,.7), rgba(61,90,254,.2)); }
.sc-col.is-on .sc-bar {
  background: linear-gradient(180deg, #c4b5fd, #6a7dff 40%, #3d5afe);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.6), 0 0 30px rgba(110,125,255,.7), 0 0 80px rgba(139,92,246,.4);
}
.sc-col small { position: absolute; left: 0; right: 0; bottom: -26px; text-align: center; font-size: 11px; color: rgba(255,255,255,.4); }
.sc-col.is-on small { color: #fff; font-weight: 600; }

/* ---------- сцена 3 ---------- */
.sc-str { display: grid; grid-template-columns: 6fr 5fr; gap: 40px; align-items: center; margin-top: 24px; padding: clamp(24px, 3.4vw, 48px); }
.sc-str__viz { position: relative; height: clamp(320px, 34vw, 460px); display: grid; place-items: center; perspective: 1400px; }
.st-iso { position: relative; width: min(360px, 78%); aspect-ratio: 1; transform-style: preserve-3d; transform: rotateX(58deg) rotateZ(-32deg); }
.st-seg, .st-seg__lift { position: absolute; inset: 0; transform-style: preserve-3d; }
.st-seg__lift { transition: transform .6s var(--lp-ease), opacity .4s; }
.st-seg__lift.is-on { transform: translateZ(26px); }
.st-seg__lift.is-dim { opacity: .45; }
.st-layer { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; transform: translateZ(var(--z)) rotate(-90deg); pointer-events: none; filter: brightness(.72) saturate(1.1); }
.st-layer circle { fill: none; stroke-width: 16; }
.st-layer.is-top { filter: none; }
.st-layer.is-top circle { pointer-events: stroke; cursor: pointer; }
.st-shadow {
  position: absolute; left: 50%; top: 58%; width: 70%; height: 30%; translate: -50% 0; z-index: -1; pointer-events: none;
  background: radial-gradient(50% 50% at 50% 50%, rgba(30,40,90,.22), transparent 70%); filter: blur(14px);
}
.st-focus { display: flex; align-items: center; gap: 18px; margin-top: 28px; }
.st-focus b { font-family: var(--lp-display); font-size: clamp(48px, 5vw, 72px); font-weight: 600; letter-spacing: -0.05em; line-height: 1; transition: color .3s; font-variant-numeric: tabular-nums; }
.st-focus span { font-size: 13.5px; line-height: 1.45; color: var(--lp-muted); }
.st-focus strong { display: block; font-size: 15px; font-weight: 600; color: var(--lp-ink); }
.st-list { margin: 24px 0 0; padding: 0; list-style: none; }
.st-row { display: grid; grid-template-columns: 120px 1fr 44px; gap: 14px; align-items: center; padding: 10px 0; border-top: 1px solid var(--lp-line); cursor: default; transition: opacity .3s; }
.st-row.is-dim { opacity: .45; }
.st-row__name { display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: var(--lp-ink); }
.st-row__name i { width: 8px; height: 8px; border-radius: 50%; }
.st-row__bar { height: 6px; border-radius: 6px; background: var(--lp-bg-2); overflow: hidden; }
.st-row__bar i { display: block; height: 100%; border-radius: inherit; }
.st-row b { text-align: right; font-size: 14px; font-weight: 600; color: var(--lp-ink); font-variant-numeric: tabular-nums; }

/* ---------- нижний ряд ---------- */
.sc-row { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 24px; margin-top: 24px; }
.sc-card { display: flex; flex-direction: column; gap: 24px; padding: 28px; min-height: 360px; }
.sc-feed { position: relative; margin: auto 0 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.sc-feed li {
  display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 14px;
  background: #fff; box-shadow: inset 0 1px 0 #fff, 0 0 0 1px var(--lp-line), 0 6px 14px -8px rgba(30,40,90,.15);
}
.sc-feed li:nth-child(3) { opacity: .5; }
.sc-feed__icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; background: var(--lp-bg-2); color: var(--lp-ink-2); flex: none; }
.sc-feed__txt { flex: 1; min-width: 0; }
.sc-feed__txt b { display: block; font-size: 13px; font-weight: 600; color: var(--lp-ink); }
.sc-feed__txt small { display: block; font-size: 12px; color: var(--lp-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.sc-feed em { font-style: normal; font-size: 13px; font-weight: 600; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.sc-feed em.is-pos { color: var(--lp-green); }
.sc-feed-enter-active { transition: all .7s var(--lp-ease); }
.sc-feed-leave-active { transition: all .4s ease; position: absolute; left: 0; right: 0; bottom: 0; }
.sc-feed-enter-from { opacity: 0; transform: translateY(-16px) scale(.97); }
.sc-feed-leave-to { opacity: 0; }
.sc-feed-move { transition: transform .7s var(--lp-ease); }

.sc-stack { position: relative; height: 150px; margin-top: auto; }
.sc-stack__card {
  position: absolute; left: 0; right: 0; bottom: calc(var(--i) * 22px);
  display: flex; justify-content: space-between; align-items: flex-end;
  height: 92px; padding: 16px 18px; border-radius: 18px; box-sizing: border-box;
  background: linear-gradient(180deg, #fff, #fafbff);
  box-shadow: inset 0 1px 0 #fff, 0 0 0 1px var(--lp-line), 0 12px 28px -14px rgba(30,40,90,.3);
  transform: scale(calc(1 - var(--i) * .05)); transform-origin: bottom center;
  z-index: calc(3 - var(--i));
  transition: transform .6s var(--lp-ease), bottom .6s var(--lp-ease);
}
.sc-stack__card span { display: flex; align-items: center; gap: 8px; align-self: flex-start; font-size: 13px; font-weight: 600; color: var(--lp-ink); }
.sc-stack__card span i { width: 8px; height: 8px; border-radius: 50%; background: var(--c); box-shadow: 0 0 8px var(--c); }
.sc-stack__card b { font-family: var(--lp-display); font-size: 20px; font-weight: 600; letter-spacing: -0.02em; color: var(--lp-ink); font-variant-numeric: tabular-nums; }
.sc-card--stack:hover .sc-stack__card { bottom: calc(var(--i) * 48px); transform: scale(calc(1 - var(--i) * .03)) rotate(calc(var(--i) * -1.5deg)); }

.sc-cur { display: flex; flex-direction: column; gap: 18px; margin-top: auto; }
.sc-cur__val {
  font-family: var(--lp-display); font-size: clamp(30px, 2.8vw, 40px); font-weight: 600; letter-spacing: -0.04em; line-height: 1;
  font-variant-numeric: tabular-nums; white-space: nowrap;
  background: linear-gradient(90deg, var(--lp-ink), #3d5afe 150%); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.sc-tabs--full { display: flex; }
.sc-tabs--full button { flex: 1; }

@media (max-width: 1023px) {
  .sc-div, .sc-str { grid-template-columns: 1fr; }
  .sc-str__viz { order: -1; }
  .sc-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sc-card--cur { grid-column: 1 / -1; min-height: 0; }
  .sc-kpis { grid-template-columns: repeat(2, 1fr); gap: 20px 0; }
  .sc-kpi:nth-child(3) { padding-left: 0; border-left: 0; }
}
@media (max-width: 680px) {
  .mat, .sc-div { border-radius: 24px; }
  .sc-perf__side { align-items: flex-start; }
  .sc-perf__num { text-align: left; }
  .sc-note__body { font-size: 11px; padding: 4px 9px 4px 4px; }
  .sc-note:nth-of-type(2) { display: none; }
  .sc-note__icon { width: 18px; height: 18px; }
  .sc-div__viz { min-height: 280px; }
  .sc-div__plane { height: 250px; transform: rotateX(10deg) rotateY(-8deg); }
  .sc-col small { font-size: 9px; }
  .sc-row { grid-template-columns: 1fr; gap: 16px; }
  .sc-card { min-height: 0; padding: 22px; }
  .sc-card--cur { grid-column: auto; }
  .st-row { grid-template-columns: 100px 1fr 40px; }
}
</style>
