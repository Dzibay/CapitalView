<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import LandingIcon from './LandingIcon.vue'
import { formatRub } from './useLandingMotion'

gsap.registerPlugin(ScrollTrigger)

const sources = [
  { id: 't', name: 'Т-Инвестиции', meta: 'Официальный API · чтение', mark: 'Т', color: '#ffdd2d', ink: '#0b0d12', live: true },
  { id: 'm', name: 'Ручной ввод', meta: 'Вклады, недвижимость, крипта', icon: 'pencil', color: '#0b0d12', ink: '#fff', live: true },
  { id: 's', name: 'Сбер', meta: 'В разработке', mark: 'С', color: '#eef0f3', ink: '#8a909c', live: false },
  { id: 'v', name: 'ВТБ', meta: 'В разработке', mark: 'В', color: '#eef0f3', ink: '#8a909c', live: false }
]

const stages = [
  { n: '01', icon: 'link', title: 'Подключите брокера', text: 'Официальный API, доступ только на чтение.' },
  { n: '02', icon: 'sync', title: 'Данные приходят сами', text: 'Сделки, дивиденды и купоны — за секунды.' },
  { n: '03', icon: 'trend', title: 'Капитал как на ладони', text: 'Доходность, структура и выплаты на одном экране.' }
]
const STAGE_AT = [0, 0.3, 0.62]
const STAGE_LEN = [0.3, 0.32, 0.38]
const stageFill = (i) => Math.min(1, Math.max(0, (st.progress - STAGE_AT[i]) / STAGE_LEN[i]))
const nav = ['wallet', 'trend', 'pie', 'calendar', 'receipt']

const structure = [
  { label: 'Акции', v: 42, c: '#3d5afe' },
  { label: 'Облигации', v: 26, c: '#22b8cf' },
  { label: 'Фонды', v: 14, c: '#8b5cf6' },
  { label: 'Валюта', v: 10, c: '#12b76a' },
  { label: 'Крипто', v: 8, c: '#ff7a45' }
]
const dividends = [
  { t: 'LKOH', n: 'Лукойл', d: '12', m: 'июл', v: '+9 960 ₽' },
  { t: 'SBER', n: 'Сбербанк', d: '19', m: 'июл', v: '+6 920 ₽' },
  { t: 'OFZ', n: 'ОФЗ 26238', d: '24', m: 'июл', v: '+1 794 ₽' }
]
const trades = [
  { t: 'Покупка', a: 'YDEX × 4', v: '−16 840 ₽', icon: 'plus' },
  { t: 'Купон', a: 'ОФЗ 26238', v: '+1 794 ₽', icon: 'bond' },
  { t: 'Дивиденд', a: 'MGNT', v: '+3 120 ₽', icon: 'wallet' }
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
const chartLine = 'M0,88 C25,86 35,74 60,76 S100,60 125,62 S160,44 185,48 S230,26 255,28 S285,12 300,10'
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
      const y2 = d.top - box.top
      const my = (y1 + y2) / 2
      return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`
    }
    const x1 = r.right - box.left
    const y1 = r.top + r.height / 2 - box.top
    const x2 = d.left - box.left
    const y2 = d.top + d.height * (0.24 + i * 0.16) - box.top
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
    p.style.strokeDasharray = sources[i].live ? `${len}` : '3 6'
    p.style.strokeDashoffset = sources[i].live ? `${len * (1 - wireProg)}` : '0'
    p.style.opacity = sources[i].live ? 1 : wireProg * 0.6
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
        gsap.fromTo(dashEl.value, { '--ping': 1 }, { '--ping': 0, duration: 0.7, ease: 'power2.out' })
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

    tl.from('.bf-src', { x: -40, opacity: 0, stagger: 0.05, duration: 0.25 }, 0)
      .to({ v: 0 }, {
        v: 1, duration: 0.35, ease: 'none',
        onUpdate() { wireProg = this.targets()[0].v; applyWire() }
      }, 0.15)
      .from(dashEl.value, { opacity: 0.4, scale: 0.96, y: 20, duration: 0.3 }, 0.2)

    let at = 0.42
    widgets.forEach((w) => {
      tl.from(w, { opacity: 0, y: 24, scale: 0.97, filter: 'blur(6px)', duration: 0.16 }, at)
      at += 0.06
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
        <span class="lp-eyebrow">Как это работает</span>
        <h2 class="lp-h2">Подключите брокера.<br /><span class="lp-dim">Остальное — наша работа.</span></h2>
        <ol class="bf__steps">
          <li v-for="(s, i) in stages" :key="s.n" :class="{ 'is-on': st.stage === i, 'is-done': st.stage > i }">
            <span class="bf__step-icon"><LandingIcon :name="st.stage > i ? 'check' : s.icon" :size="16" :stroke="1.7" /></span>
            <span class="bf__step-txt"><b>{{ s.title }}</b><small>{{ s.text }}</small></span>
            <span class="bf__step-bar"><i :style="{ transform: `scaleX(${stageFill(i)})` }" /></span>
          </li>
        </ol>
      </div>

      <div ref="stageEl" class="bf__stage">
        <svg ref="svgEl" class="bf__wires" aria-hidden="true">
          <defs>
            <linearGradient id="bf-wire-g" x1="0" x2="1" y1="0" y2="0">
              <stop offset="0" stop-color="#8b5cf6" />
              <stop offset="1" stop-color="#3d5afe" />
            </linearGradient>
            <radialGradient id="bf-halo">
              <stop offset="0" stop-color="#3d5afe" stop-opacity=".45" />
              <stop offset="1" stop-color="#3d5afe" stop-opacity="0" />
            </radialGradient>
          </defs>
          <path v-for="(d, i) in wires" :key="'t' + i" :d="d" class="bf-wire-track" />
          <path
            v-for="(d, i) in wires"
            :key="i"
            :ref="(el) => (wireEls[i] = el)"
            :d="d"
            class="bf-wire"
            :class="{ 'is-soon': !sources[i].live }"
          />
          <g v-for="i in PACKETS" :key="'p' + i" :ref="(el) => (packetEls[i - 1] = el)" class="bf-packet" style="opacity:0">
            <circle r="11" fill="url(#bf-halo)" />
            <circle r="3" class="bf-packet__dot" />
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
            <span class="bf-src__mark" :style="{ background: s.color, color: s.ink }">
              <LandingIcon v-if="s.icon" :name="s.icon" :size="16" :stroke="1.7" />
              <template v-else>{{ s.mark }}</template>
            </span>
            <span class="bf-src__body">
              <b>{{ s.name }}</b>
              <small>{{ s.meta }}</small>
            </span>
            <span v-if="s.live" class="bf-src__status" :class="{ 'is-ok': st.progress > 0.45, 'is-wait': st.progress > 0.12 && st.progress <= 0.45 }">
              <LandingIcon v-if="st.progress > 0.45" name="check" :size="12" :stroke="2.2" />
              <i v-else class="bf-spin" />
            </span>
            <span v-else class="bf-src__soon">Скоро</span>
          </div>
        </div>

        <div ref="dashEl" class="bf__dash">
          <div class="bf__chrome">
            <span class="bf__dots"><i /><i /><i /></span>
            <span class="bf__url"><LandingIcon name="lock" :size="11" :stroke="2" /> app.capitalview.ru</span>
            <span />
          </div>
          <div class="bf__app">
            <aside class="bf__nav" aria-hidden="true">
              <span class="bf__logo" />
              <span v-for="(n, i) in nav" :key="n" :class="{ 'is-on': !i }"><LandingIcon :name="n" :size="16" /></span>
            </aside>
            <div class="bf__grid">
              <div class="bf-w bf-w--total">
                <span class="bf-w__label">Общий капитал</span>
                <b class="bf-w__big">{{ formatRub(st.total) }}</b>
                <span class="bf-w__delta"><LandingIcon name="arrow-up-right" :size="11" :stroke="2.2" /> 18,4% за год</span>
              </div>
              <div class="bf-w bf-w--chart">
                <div class="bf-w__row">
                  <span class="bf-w__label">Доходность, XIRR</span>
                  <span class="bf-w__seg"><i>1М</i><i>6М</i><i class="is-on">1Г</i><i>Всё</i></span>
                </div>
                <svg viewBox="0 0 300 100" preserveAspectRatio="none" class="bf-chart">
                  <defs>
                    <linearGradient id="bf-area" x1="0" x2="0" y1="0" y2="1">
                      <stop offset="0" stop-color="#3d5afe" stop-opacity=".2" />
                      <stop offset="1" stop-color="#3d5afe" stop-opacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0,25 H300 M0,50 H300 M0,75 H300" class="bf-chart__grid" />
                  <path :d="chartLine + ' L300,100 L0,100 Z'" fill="url(#bf-area)" class="bf-chart__area" />
                  <path :d="chartLine" class="bf-chart__line" />
                </svg>
              </div>
              <div class="bf-w bf-w--donut">
                <span class="bf-w__label">Структура</span>
                <div class="bf-donut">
                  <svg viewBox="0 0 100 100">
                    <circle cx="50" cy="50" r="40" class="bf-donut__track" />
                    <circle v-for="s in structure" :key="s.label" cx="50" cy="50" r="40" class="bf-donut__seg" :stroke="s.c" />
                  </svg>
                  <ul>
                    <li v-for="s in structure.slice(0, 4)" :key="s.label"><i :style="{ background: s.c }" />{{ s.label }} <b>{{ s.v }}%</b></li>
                  </ul>
                </div>
              </div>
              <div class="bf-w bf-w--div">
                <span class="bf-w__label">Ближайшие выплаты</span>
                <ul class="bf-list">
                  <li v-for="d in dividends" :key="d.t">
                    <span class="bf-date"><b>{{ d.d }}</b>{{ d.m }}</span>
                    <span class="bf-list__name">{{ d.n }}</span>
                    <em>{{ d.v }}</em>
                  </li>
                </ul>
              </div>
              <div class="bf-w bf-w--tx">
                <span class="bf-w__label">Последние операции</span>
                <ul class="bf-list">
                  <li v-for="t in trades" :key="t.a">
                    <span class="bf-list__icon"><LandingIcon :name="t.icon" :size="13" :stroke="1.8" /></span>
                    <span class="bf-list__name">{{ t.t }} <small>{{ t.a }}</small></span>
                    <em :class="{ 'is-neg': t.v.startsWith('−') }">{{ t.v }}</em>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.bf { position: relative; background: var(--lp-bg-2); }
.bf__pin {
  height: 100vh; height: 100svh; box-sizing: border-box;
  display: grid; grid-template-rows: auto 1fr; gap: clamp(16px, 3.5vh, 40px);
  padding: clamp(80px, 11vh, 112px) var(--lp-pad) clamp(20px, 4vh, 44px);
  max-width: calc(var(--lp-max) + var(--lp-pad) * 2); margin: 0 auto;
}
.bf__head { display: grid; grid-template-columns: 1fr 1.3fr; align-items: end; gap: 14px 64px; }
.bf__head .lp-eyebrow { grid-column: 1 / -1; }
.bf__head .lp-h2 { font-size: clamp(30px, 3.3vw, 52px); }
.bf__steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin: 0; padding: 0; list-style: none; }
.bf__steps li { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; align-content: start; opacity: .45; transition: opacity .5s var(--lp-ease); }
.bf__steps li.is-on, .bf__steps li.is-done { opacity: 1; }
.bf__step-icon {
  display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px;
  background: #fff; color: var(--lp-ink); box-shadow: 0 0 0 1px var(--lp-line);
  transition: background .4s, color .4s;
}
.bf__steps li.is-on .bf__step-icon { background: var(--lp-ink); color: #fff; }
.bf__steps li.is-done .bf__step-icon { background: var(--lp-green); color: #fff; box-shadow: none; }
.bf__step-txt b { display: block; font-size: 14.5px; font-weight: 600; color: var(--lp-ink); letter-spacing: -0.01em; }
.bf__step-txt small { display: block; margin-top: 3px; font-size: 13px; line-height: 1.45; color: var(--lp-muted); }
.bf__step-bar { grid-column: 1 / -1; height: 2px; margin-top: 12px; border-radius: 2px; background: rgba(11,13,18,.08); overflow: hidden; }
.bf__step-bar i { display: block; height: 100%; background: var(--lp-ink); transform-origin: left; }

.bf__stage {
  position: relative; min-height: 0;
  display: grid; grid-template-columns: minmax(220px, 260px) 1fr; gap: clamp(64px, 9vw, 150px); align-items: center;
}
.bf__wires { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; z-index: 1; }
.bf-wire-track { fill: none; stroke: rgba(11,13,18,.09); stroke-width: 1.5; }
.bf-wire { fill: none; stroke: url(#bf-wire-g); stroke-width: 1.75; stroke-linecap: round; }
.bf-wire.is-soon { stroke: rgba(11,13,18,.25); stroke-width: 1.25; }
.bf-packet__dot { fill: #fff; stroke: #3d5afe; stroke-width: 2; }

.bf__sources { position: relative; z-index: 2; display: grid; gap: 12px; }
.bf-src {
  display: flex; align-items: center; gap: 12px; padding: 12px 14px 12px 12px; border-radius: 16px;
  background: #fff; box-shadow: 0 0 0 1px var(--lp-line), 0 8px 20px -12px rgba(11,13,18,.18);
}
.bf-src.is-soon { background: rgba(255,255,255,.55); box-shadow: 0 0 0 1px var(--lp-line); }
.bf-src__mark {
  display: grid; place-items: center; width: 36px; height: 36px; border-radius: 11px; flex: none;
  font-family: var(--lp-display); font-weight: 700; font-size: 17px;
}
.bf-src__body { flex: 1; min-width: 0; }
.bf-src__body b { display: block; font-size: 14px; font-weight: 600; color: var(--lp-ink); }
.bf-src__body small { display: block; font-size: 12px; color: var(--lp-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bf-src.is-soon .bf-src__body b { color: var(--lp-muted); }
.bf-src__status {
  display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; flex: none;
  background: var(--lp-bg-2); color: #fff; transition: background .4s;
}
.bf-src__status.is-ok { background: var(--lp-green); }
.bf-spin { width: 12px; height: 12px; border-radius: 50%; border: 1.5px solid rgba(11,13,18,.15); border-top-color: transparent; }
.bf-src__status.is-wait .bf-spin { border-color: var(--lp-blue); border-top-color: transparent; animation: bf-spin .8s linear infinite; }
@keyframes bf-spin { to { transform: rotate(360deg); } }
.bf-src__soon { font-size: 11px; font-weight: 500; padding: 3px 8px; border-radius: 99px; background: var(--lp-bg-2); color: var(--lp-muted); }

.bf__dash {
  --ping: 0;
  position: relative; z-index: 2; align-self: center;
  border-radius: 18px; background: #fff; overflow: hidden;
  box-shadow:
    0 0 0 1px rgba(11,13,18,.07),
    0 30px 60px -20px rgba(30,40,90,.25),
    0 80px 120px -60px rgba(61,90,254,.3),
    0 0 calc(var(--ping) * 40px) rgba(61,90,254, calc(var(--ping) * .35));
}
.bf__chrome {
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center;
  height: 36px; padding: 0 14px; border-bottom: 1px solid var(--lp-line); background: #fbfbfc;
}
.bf__dots { display: flex; gap: 6px; }
.bf__dots i { width: 10px; height: 10px; border-radius: 50%; background: #e4e6ea; }
.bf__url {
  display: flex; align-items: center; gap: 5px; padding: 3px 12px; border-radius: 7px;
  background: var(--lp-bg-2); font-size: 11.5px; color: var(--lp-muted);
}
.bf__app { display: grid; grid-template-columns: 52px 1fr; }
.bf__nav { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 14px 0; border-right: 1px solid var(--lp-line); color: #9aa0ab; }
.bf__nav span { display: grid; place-items: center; width: 32px; height: 32px; border-radius: 9px; }
.bf__nav span.is-on { background: var(--lp-bg-2); color: var(--lp-ink); }
.bf__nav .bf__logo { margin-bottom: 8px; width: 26px; height: 26px; border-radius: 8px; background: linear-gradient(135deg, #3d5afe, #8b5cf6); }
.bf__grid { display: grid; grid-template-columns: 1.1fr 1fr 1fr; gap: 12px; padding: 14px; }
.bf-w { padding: 14px; border-radius: 14px; background: #fff; box-shadow: 0 0 0 1px var(--lp-line); min-width: 0; }
.bf-w--chart { grid-column: span 2; }
.bf-w__row { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.bf-w__label { display: block; font-size: 12px; color: var(--lp-muted); }
.bf-w__seg { display: flex; gap: 2px; padding: 2px; border-radius: 8px; background: var(--lp-bg-2); }
.bf-w__seg i { font-style: normal; font-size: 10.5px; padding: 2px 7px; border-radius: 6px; color: var(--lp-muted); }
.bf-w__seg i.is-on { background: #fff; color: var(--lp-ink); box-shadow: 0 1px 2px rgba(11,13,18,.08); }
.bf-w__big {
  display: block; margin-top: 10px; font-family: var(--lp-display); font-weight: 600;
  font-size: clamp(22px, 2vw, 30px); letter-spacing: -0.03em; color: var(--lp-ink); font-variant-numeric: tabular-nums; white-space: nowrap;
}
.bf-w__delta {
  display: inline-flex; align-items: center; gap: 3px; margin-top: 8px; padding: 2px 8px; border-radius: 99px;
  font-size: 11.5px; font-weight: 600; color: var(--lp-green); background: rgba(18,183,106,.1);
}
.bf-chart { display: block; width: 100%; height: clamp(70px, 11vh, 110px); margin-top: 8px; }
.bf-chart__grid { stroke: rgba(11,13,18,.07); stroke-width: 1; vector-effect: non-scaling-stroke; stroke-dasharray: 3 4; }
.bf-chart__line { fill: none; stroke: #3d5afe; stroke-width: 2; vector-effect: non-scaling-stroke; stroke-dasharray: 420; }
.bf-donut { display: flex; align-items: center; gap: 12px; margin-top: 10px; }
.bf-donut svg { width: 76px; height: 76px; flex: none; transform: rotate(-90deg); }
.bf-donut__track { fill: none; stroke: var(--lp-bg-2); stroke-width: 11; }
.bf-donut__seg { fill: none; stroke-width: 11; }
.bf-donut ul { margin: 0; padding: 0; list-style: none; display: grid; gap: 4px; min-width: 0; flex: 1; }
.bf-donut li { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--lp-muted); white-space: nowrap; }
.bf-donut li i { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.bf-donut li b { margin-left: auto; padding-left: 6px; color: var(--lp-ink); font-weight: 600; }
.bf-list { margin: 8px 0 0; padding: 0; list-style: none; }
.bf-list li { display: flex; align-items: center; gap: 10px; padding: 7px 0; font-size: 12.5px; }
.bf-list li + li { border-top: 1px solid var(--lp-line); }
.bf-list__name { flex: 1; min-width: 0; color: var(--lp-ink); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.bf-list__name small { color: var(--lp-muted); font-weight: 400; margin-left: 4px; font-size: inherit; }
.bf-list em { font-style: normal; font-weight: 600; color: var(--lp-green); font-variant-numeric: tabular-nums; white-space: nowrap; }
.bf-list em.is-neg { color: var(--lp-ink); }
.bf-date {
  display: grid; place-items: center; align-content: center; width: 32px; height: 32px; border-radius: 9px; flex: none;
  background: var(--lp-bg-2); font-size: 9px; line-height: 1.1; color: var(--lp-muted); text-transform: uppercase;
}
.bf-date b { font-size: 13px; color: var(--lp-ink); }
.bf-list__icon { display: grid; place-items: center; width: 26px; height: 26px; border-radius: 8px; background: var(--lp-bg-2); color: var(--lp-ink-2); flex: none; }

@media (min-width: 900px) and (max-width: 1279px) {
  .bf__head { grid-template-columns: 1fr; }
  .bf__stage { grid-template-columns: minmax(200px, 230px) 1fr; gap: clamp(48px, 7vw, 96px); }
  .bf__grid { grid-template-columns: 1fr 1fr; }
  .bf-w--chart { grid-column: auto; }
  .bf-w--tx { display: none; }
}
@media (max-height: 820px) and (min-width: 900px) {
  .bf__steps small { display: none; }
  .bf-w--tx, .bf-w--div { display: none; }
}
@media (max-width: 899px) {
  .bf__pin { padding-top: 76px; gap: 16px; }
  .bf__head { grid-template-columns: 1fr; gap: 10px; }
  .bf__head .lp-h2 { font-size: 28px; }
  .bf__steps { grid-template-columns: 1fr; gap: 0; position: relative; height: 62px; }
  .bf__steps li { position: absolute; inset: 0; opacity: 0; transform: translateY(8px); transition: opacity .4s, transform .5s var(--lp-ease); }
  .bf__steps li.is-on { opacity: 1; transform: none; }
  .bf__steps li.is-done { opacity: 0; }
  .bf__step-bar { margin-top: 8px; }
  .bf__stage { grid-template-columns: 1fr; grid-template-rows: auto 1fr; gap: 40px; align-items: start; }
  .bf__sources { grid-template-columns: repeat(4, 1fr); gap: 8px; }
  .bf-src { flex-direction: column; text-align: center; padding: 10px 4px; gap: 6px; }
  .bf-src__body small, .bf-src__status, .bf-src__soon { display: none; }
  .bf-src__body b { font-size: 11.5px; }
  .bf-src__mark { width: 30px; height: 30px; font-size: 14px; }
  .bf__app { grid-template-columns: 1fr; }
  .bf__nav { display: none; }
  .bf__grid { grid-template-columns: 1fr 1fr; gap: 8px; padding: 10px; }
  .bf-w { padding: 11px; }
  .bf-w--total, .bf-w--chart { grid-column: 1 / -1; }
  .bf-w--tx { display: none; }
  .bf-w--donut ul { display: none; }
  .bf-donut { justify-content: center; }
  .bf-date { display: none; }
  .bf-w--div .bf-list li:nth-child(3) { display: none; }
  .bf-chart { height: 64px; }
}
</style>
