<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { formatRub } from './useLandingMotion'

gsap.registerPlugin(ScrollTrigger)

const sources = [
  { id: 't', name: 'Т-Инвестиции', meta: 'API · только чтение', mark: 'T', color: '#ffdd2d', ink: '#111', live: true },
  { id: 'm', name: 'Ручной ввод', meta: 'Вклады, недвижимость', mark: '+', color: '#111', ink: '#fff', live: true },
  { id: 's', name: 'Сбер', meta: 'Скоро', mark: 'С', color: '#21a038', ink: '#fff', live: false },
  { id: 'v', name: 'ВТБ', meta: 'Скоро', mark: 'В', color: '#0a2896', ink: '#fff', live: false }
]

const stages = [
  { n: '01', title: 'Подключите брокера', text: 'Авторизация через официальный API — доступ только на чтение.' },
  { n: '02', title: 'Данные текут сами', text: 'Сделки, дивиденды и купоны загружаются автоматически.' },
  { n: '03', title: 'Дашборд готов', text: 'Доходность, структура и выплаты — на одном экране.' }
]

const structure = [
  { label: 'Акции', v: 42, c: '#2f5bff' },
  { label: 'Облигации', v: 26, c: '#8aa6ff' },
  { label: 'Фонды', v: 14, c: '#111111' },
  { label: 'Валюта', v: 10, c: '#c8f560' },
  { label: 'Крипто', v: 8, c: '#ff8a5c' }
]
const dividends = [
  { t: 'LKOH', d: '12 июл', v: '9 960 ₽' },
  { t: 'SBER', d: '19 июл', v: '6 920 ₽' },
  { t: 'ОФЗ 26238', d: '24 июл', v: '1 794 ₽' }
]
const trades = [
  { t: 'Покупка', a: 'YDEX × 4', v: '−16 840 ₽' },
  { t: 'Купон', a: 'ОФЗ 26238', v: '+1 794 ₽' },
  { t: 'Дивиденд', a: 'MGNT', v: '+3 120 ₽' }
]

const root = ref(null)
const stageEl = ref(null)
const dashEl = ref(null)
const svgEl = ref(null)
const srcEls = ref([])
const wireEls = ref([])
const packetEls = ref([])

const st = reactive({ stage: 0, progress: 0, total: 0 })
const wires = ref(sources.map(() => ''))
const chartLine = 'M0,92 C30,88 40,70 70,72 S110,52 140,58 S180,30 210,36 S260,12 300,8'
const PACKETS = 10

let ctx = null
let raf = 0
let active = false
let wireProg = 0
let lens = []
const packets = Array.from({ length: PACKETS }, (_, i) => ({ wire: i % 2, t: -i * 0.16, speed: 0.5 + Math.random() * 0.35 }))

function buildWires() {
  const svg = svgEl.value
  const dash = dashEl.value
  if (!svg || !dash) return
  const box = svg.getBoundingClientRect()
  const d = dash.getBoundingClientRect()
  const vertical = window.innerWidth < 900
  svg.setAttribute('viewBox', `0 0 ${box.width} ${box.height}`)
  wires.value = srcEls.value.map((el, i) => {
    const r = el.getBoundingClientRect()
    if (vertical) {
      const x1 = r.left + r.width / 2 - box.left
      const y1 = r.bottom - box.top
      const x2 = d.left + d.width * (0.2 + i * 0.2) - box.left
      const y2 = d.top - box.top + 2
      const my = (y1 + y2) / 2
      return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`
    }
    const x1 = r.right - box.left
    const y1 = r.top + r.height / 2 - box.top
    const x2 = d.left - box.left + 2
    const y2 = d.top + d.height * (0.22 + i * 0.18) - box.top
    const mx = (x1 + x2) / 2
    return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`
  })
  requestAnimationFrame(() => {
    lens = wireEls.value.map((p) => p?.getTotalLength?.() || 1)
    applyWire()
  })
}

function applyWire() {
  wireEls.value.forEach((p, i) => {
    if (!p) return
    const len = lens[i] || 1
    p.style.strokeDasharray = sources[i].live ? `${len}` : '4 7'
    p.style.strokeDashoffset = sources[i].live ? `${len * (1 - wireProg)}` : '0'
    p.style.opacity = sources[i].live ? 1 : wireProg * 0.5
  })
}

let lastPing = 0
function loop(now) {
  raf = requestAnimationFrame(loop)
  const dt = 1 / 60
  packets.forEach((pk, i) => {
    const el = packetEls.value[i]
    const path = wireEls.value[pk.wire]
    if (!el || !path) return
    pk.t += dt * pk.speed
    if (pk.t > 1) {
      pk.t = 0
      pk.wire = Math.random() < 0.7 ? 0 : 1
      pk.speed = 0.5 + Math.random() * 0.35
      if (wireProg > 0.98 && now - lastPing > 220) {
        lastPing = now
        gsap.fromTo(dashEl.value, { '--ping': 1 }, { '--ping': 0, duration: 0.6, ease: 'power2.out' })
      }
    }
    const reach = wireProg
    if (pk.t < 0 || pk.t > reach || reach < 0.05) { el.style.opacity = 0; return }
    const len = lens[pk.wire] || 1
    const pt = path.getPointAtLength(pk.t * len)
    el.setAttribute('transform', `translate(${pt.x},${pt.y})`)
    el.style.opacity = Math.min(1, pk.t * 8, (reach - pk.t) * 8, (1 - pk.t) * 8)
  })
}

function setActive(on) {
  if (on === active) return
  active = on
  if (on) raf = requestAnimationFrame(loop)
  else cancelAnimationFrame(raf)
}

function onResize() { buildWires() }

onMounted(() => {
  buildWires()
  window.addEventListener('resize', onResize)

  ctx = gsap.context(() => {
    const widgets = gsap.utils.toArray('.bf-w', root.value)
    const segs = gsap.utils.toArray('.bf-donut__seg', root.value)
    const C = 2 * Math.PI * 40
    segs.forEach((s) => gsap.set(s, { strokeDasharray: `0 ${C}` }))

    const tl = gsap.timeline({
      defaults: { ease: 'power2.out' },
      scrollTrigger: {
        trigger: root.value,
        start: 'top top',
        end: () => `+=${window.innerHeight * 2.6}`,
        pin: stageEl.value.parentElement,
        scrub: 0.6,
        invalidateOnRefresh: true,
        onRefresh: buildWires,
        onToggle: (self) => setActive(self.isActive),
        onUpdate: (self) => {
          st.progress = self.progress
          st.stage = self.progress < 0.3 ? 0 : self.progress < 0.62 ? 1 : 2
        }
      }
    })

    tl.from('.bf-src', { x: -60, opacity: 0, stagger: 0.05, duration: 0.25 }, 0)
      .to({ v: 0 }, {
        v: 1, duration: 0.35, ease: 'none',
        onUpdate() { wireProg = this.targets()[0].v; applyWire() }
      }, 0.15)
      .from(dashEl.value, { opacity: 0.25, scale: 0.94, duration: 0.3 }, 0.2)

    let at = 0.42
    widgets.forEach((w) => {
      tl.from(w, { opacity: 0, y: 50, scale: 0.9, filter: 'blur(10px)', duration: 0.16 }, at)
      at += 0.07
    })
    tl.to(st, { total: 2847320, duration: 0.4, ease: 'power1.out' }, 0.44)
      .fromTo('.bf-chart__line', { strokeDashoffset: 420 }, { strokeDashoffset: 0, duration: 0.3, ease: 'none' }, 0.52)
      .fromTo('.bf-chart__area', { opacity: 0 }, { opacity: 1, duration: 0.2 }, 0.62)

    let off = 0
    segs.forEach((s, i) => {
      const len = (structure[i].v / 100) * C
      gsap.set(s, { strokeDashoffset: -off })
      tl.to(s, { strokeDasharray: `${Math.max(len - 3, 0)} ${C}`, duration: 0.12 }, 0.6 + i * 0.04)
      off += len
    })
    tl.to({}, { duration: 0.15 })
  }, root.value)
})

onUnmounted(() => {
  setActive(false)
  window.removeEventListener('resize', onResize)
  ctx?.revert()
})
</script>

<template>
  <section ref="root" class="bf" id="flow">
    <div class="bf__pin">
      <div class="bf__head">
        <span class="pb-mono">[ 002 ] Живые данные</span>
        <div class="bf__stages">
          <div v-for="(s, i) in stages" :key="s.n" class="bf__stage-title" :class="{ 'is-on': st.stage === i }">
            <span class="pb-mono">{{ s.n }}</span>
            <h2>{{ s.title }}</h2>
            <p>{{ s.text }}</p>
          </div>
        </div>
        <div class="bf__bar"><i :style="{ transform: `scaleX(${st.progress})` }" /></div>
      </div>

      <div ref="stageEl" class="bf__stage">
        <svg ref="svgEl" class="bf__wires" aria-hidden="true">
          <defs>
            <linearGradient id="bf-wire-g" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stop-color="#111" />
              <stop offset="1" stop-color="#2f5bff" />
            </linearGradient>
          </defs>
          <path
            v-for="(d, i) in wires"
            :key="i"
            :ref="(el) => (wireEls[i] = el)"
            :d="d"
            class="bf-wire"
            :class="{ 'is-soon': !sources[i].live }"
          />
          <g v-for="i in PACKETS" :key="'p' + i" :ref="(el) => (packetEls[i - 1] = el)" class="bf-packet" style="opacity:0">
            <circle r="9" class="bf-packet__halo" />
            <circle r="4" class="bf-packet__dot" />
          </g>
        </svg>

        <div class="bf__sources">
          <div
            v-for="(s, i) in sources"
            :key="s.id"
            :ref="(el) => (srcEls[i] = el)"
            class="bf-src"
            :class="{ 'is-soon': !s.live }"
          >
            <span class="bf-src__mark" :style="{ background: s.color, color: s.ink }">{{ s.mark }}</span>
            <span class="bf-src__body">
              <b>{{ s.name }}</b>
              <small>{{ s.meta }}</small>
            </span>
            <span v-if="s.live" class="bf-src__status" :class="{ 'is-ok': st.progress > 0.45 }">
              {{ st.progress > 0.45 ? '✓ синхр.' : st.progress > 0.12 ? 'подключение…' : '—' }}
            </span>
          </div>
        </div>

        <div ref="dashEl" class="bf__dash">
          <div class="bf__dash-top">
            <span class="bf__dots"><i /><i /><i /></span>
            <span class="pb-mono">capitalview / дашборд</span>
          </div>
          <div class="bf__grid">
            <div class="bf-w bf-w--total">
              <span class="bf-w__label">Общий капитал</span>
              <b class="bf-w__big">{{ formatRub(st.total) }}</b>
              <span class="bf-w__delta">▲ +18,4% за год</span>
            </div>
            <div class="bf-w bf-w--chart">
              <span class="bf-w__label">Доходность</span>
              <svg viewBox="0 0 300 100" preserveAspectRatio="none" class="bf-chart">
                <defs>
                  <linearGradient id="bf-area" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0" stop-color="#2f5bff" stop-opacity=".35" />
                    <stop offset="1" stop-color="#2f5bff" stop-opacity="0" />
                  </linearGradient>
                </defs>
                <path :d="chartLine + ' L300,100 L0,100 Z'" fill="url(#bf-area)" class="bf-chart__area" />
                <path :d="chartLine" class="bf-chart__line" />
              </svg>
            </div>
            <div class="bf-w bf-w--donut">
              <span class="bf-w__label">Структура</span>
              <div class="bf-donut">
                <svg viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" class="bf-donut__track" />
                  <circle
                    v-for="s in structure"
                    :key="s.label"
                    cx="50" cy="50" r="40"
                    class="bf-donut__seg"
                    :stroke="s.c"
                  />
                </svg>
                <ul>
                  <li v-for="s in structure.slice(0, 4)" :key="s.label"><i :style="{ background: s.c }" />{{ s.label }} <b>{{ s.v }}%</b></li>
                </ul>
              </div>
            </div>
            <div class="bf-w bf-w--div">
              <span class="bf-w__label">Ближайшие выплаты</span>
              <ul class="bf-list">
                <li v-for="d in dividends" :key="d.t"><b>{{ d.t }}</b><span>{{ d.d }}</span><em>{{ d.v }}</em></li>
              </ul>
            </div>
            <div class="bf-w bf-w--tx">
              <span class="bf-w__label">Последние операции</span>
              <ul class="bf-list">
                <li v-for="t in trades" :key="t.a"><b>{{ t.t }}</b><span>{{ t.a }}</span><em :class="{ 'is-neg': t.v.startsWith('−') }">{{ t.v }}</em></li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bf { position: relative; }
.bf__pin {
  height: 100vh;
  height: 100svh;
  display: grid;
  grid-template-rows: auto 1fr;
  padding: 96px clamp(16px, 4vw, 56px) 32px;
  box-sizing: border-box;
  gap: 24px;
}
.bf__head { display: grid; grid-template-columns: auto 1fr; align-items: end; gap: 12px 40px; }
.bf__head > .pb-mono { grid-column: 1 / -1; }
.bf__stages { position: relative; height: clamp(84px, 9vw, 120px); grid-column: 1 / -1; }
.bf__stage-title {
  position: absolute; inset: 0;
  display: grid; grid-template-columns: auto 1fr; align-items: baseline; column-gap: 20px;
  opacity: 0; transform: translateY(30px);
  transition: opacity 0.5s, transform 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
}
.bf__stage-title.is-on { opacity: 1; transform: none; }
.bf__stage-title h2 {
  margin: 0; font: 800 clamp(36px, 6vw, 92px) / 0.95 'Inter Tight', sans-serif;
  letter-spacing: -0.045em; color: #111; text-transform: uppercase;
}
.bf__stage-title p { grid-column: 2; margin: 10px 0 0; color: #55524c; font-size: 16px; }
.bf__bar { grid-column: 1 / -1; height: 2px; background: rgba(17, 17, 17, 0.12); }
.bf__bar i { display: block; height: 100%; background: #111; transform-origin: 0 50%; }

.bf__stage { position: relative; display: grid; grid-template-columns: minmax(220px, 300px) 1fr; gap: clamp(60px, 10vw, 180px); align-items: center; min-height: 0; }
.bf__wires { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; z-index: 0; }
.bf-wire { fill: none; stroke: url(#bf-wire-g); stroke-width: 2; stroke-linecap: round; }
.bf-wire.is-soon { stroke: #111; stroke-width: 1.5; }
.bf-packet__halo { fill: #2f5bff; opacity: 0.18; }
.bf-packet__dot { fill: #2f5bff; }

.bf__sources { position: relative; z-index: 1; display: grid; gap: 12px; }
.bf-src {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px; border-radius: 16px;
  background: rgba(255, 255, 255, 0.75); border: 1px solid rgba(17, 17, 17, 0.08);
  backdrop-filter: blur(10px);
  box-shadow: 0 10px 30px -18px rgba(17, 17, 17, 0.4);
}
.bf-src.is-soon { opacity: 0.55; }
.bf-src__mark { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; font-weight: 800; flex: none; }
.bf-src__body { display: grid; min-width: 0; }
.bf-src__body b { font-size: 15px; color: #111; }
.bf-src__body small { font-size: 12px; color: #7a766e; }
.bf-src__status { margin-left: auto; font: 500 11px 'JetBrains Mono', monospace; color: #7a766e; white-space: nowrap; }
.bf-src__status.is-ok { color: #1f9d55; }

.bf__dash {
  --ping: 0;
  position: relative; z-index: 1;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(17, 17, 17, 0.08);
  border-radius: 24px;
  padding: 14px;
  backdrop-filter: blur(16px);
  box-shadow:
    0 40px 80px -40px rgba(17, 17, 17, 0.45),
    0 0 0 calc(var(--ping) * 6px) rgba(47, 91, 255, calc(var(--ping) * 0.18));
  max-height: 100%;
}
.bf__dash-top { display: flex; align-items: center; gap: 12px; padding: 2px 4px 12px; color: #9a958c; }
.bf__dots { display: flex; gap: 5px; }
.bf__dots i { width: 9px; height: 9px; border-radius: 50%; background: #e2ddd3; }
.bf__grid { display: grid; grid-template-columns: 1.1fr 1.4fr 1.2fr; grid-auto-rows: minmax(0, auto); gap: 10px; }
.bf-w { background: #faf8f4; border: 1px solid rgba(17, 17, 17, 0.06); border-radius: 16px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.bf-w__label { font: 500 11px 'JetBrains Mono', monospace; text-transform: uppercase; letter-spacing: 0.06em; color: #9a958c; }
.bf-w--total { background: #111; color: #fff; justify-content: space-between; }
.bf-w--total .bf-w__label { color: #8b877f; }
.bf-w__big { font: 800 clamp(22px, 2.4vw, 34px) / 1 'Inter Tight', sans-serif; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; white-space: nowrap; }
.bf-w__delta { color: #c8f560; font: 600 13px 'JetBrains Mono', monospace; }
.bf-w--chart { grid-column: span 2; }
.bf-chart { width: 100%; height: clamp(70px, 10vh, 120px); }
.bf-chart__line { fill: none; stroke: #2f5bff; stroke-width: 2.5; stroke-dasharray: 420; vector-effect: non-scaling-stroke; }
.bf-donut { display: flex; align-items: center; gap: 14px; }
.bf-donut svg { width: clamp(70px, 8vw, 110px); flex: none; transform: rotate(-90deg); }
.bf-donut__track { fill: none; stroke: #ece8df; stroke-width: 14; }
.bf-donut__seg { fill: none; stroke-width: 14; }
.bf-donut ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; font-size: 12px; color: #55524c; flex: 1; }
.bf-donut li { display: flex; align-items: center; gap: 6px; }
.bf-donut li i { width: 8px; height: 8px; border-radius: 2px; }
.bf-donut li b { margin-left: auto; color: #111; }
.bf-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.bf-list li { display: grid; grid-template-columns: auto 1fr auto; gap: 10px; font-size: 13px; align-items: baseline; }
.bf-list b { color: #111; }
.bf-list span { color: #9a958c; font-size: 12px; }
.bf-list em { font-style: normal; font-weight: 700; color: #1f9d55; font-variant-numeric: tabular-nums; }
.bf-list em.is-neg { color: #111; }

@media (min-width: 900px) and (max-width: 1279px) {
  .bf__stage { grid-template-columns: minmax(200px, 240px) 1fr; gap: clamp(48px, 7vw, 96px); }
  .bf__grid { grid-template-columns: 1fr 1fr; }
  .bf-w--chart { grid-column: auto; }
  .bf-w--tx { display: none; }
}
@media (max-width: 899px) {
  .bf__pin { padding-top: 84px; gap: 16px; }
  .bf__stage-title { grid-template-columns: 1fr; }
  .bf__stage-title p { grid-column: 1; font-size: 14px; margin-top: 6px; }
  .bf__stages { height: 118px; }
  .bf__stage { grid-template-columns: 1fr; grid-template-rows: auto 1fr; gap: 44px; align-items: start; }
  .bf__sources { grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .bf-src { flex-direction: column; padding: 10px 6px; gap: 6px; text-align: center; }
  .bf-src__body small, .bf-src__status { display: none; }
  .bf-src__body b { font-size: 11px; }
  .bf-src__mark { width: 30px; height: 30px; border-radius: 9px; }
  .bf__grid { grid-template-columns: 1fr 1fr; }
  .bf-w { padding: 10px 12px; }
  .bf-w--chart { grid-column: span 2; order: 1; }
  .bf-w--total { grid-column: span 2; order: 0; }
  .bf-w--donut { grid-column: span 2; order: 2; }
  .bf-w--div, .bf-w--tx { display: none; }
}
</style>
