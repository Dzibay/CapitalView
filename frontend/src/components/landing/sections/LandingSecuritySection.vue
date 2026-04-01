<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { Lock, ShieldCheck, Zap, Eye } from 'lucide-vue-next'

const iconMap = { Lock, ShieldCheck, Zap, Eye }

const props = defineProps({
  tabs: { type: Array, required: true }
})

const activeIndex = ref(0)
const activeTab = computed(() => props.tabs[activeIndex.value])
const isPaused = ref(false)
const progressKey = ref(0)
let autoTimer = null
let resumeTimer = null

const lineEnds = [
  { x: 12, y: 22 },
  { x: 88, y: 22 },
  { x: 88, y: 78 },
  { x: 12, y: 78 }
]

function startAuto() {
  clearInterval(autoTimer)
  autoTimer = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % props.tabs.length
  }, 4500)
}

function selectTab(i) {
  activeIndex.value = i
  isPaused.value = true
  clearTimeout(resumeTimer)
  clearInterval(autoTimer)
  resumeTimer = setTimeout(() => {
    isPaused.value = false
    startAuto()
  }, 8000)
}

watch([activeIndex, isPaused], () => { progressKey.value++ })

onMounted(startAuto)
onUnmounted(() => {
  clearInterval(autoTimer)
  clearTimeout(resumeTimer)
})
</script>

<template>
  <section id="security" class="section snap-section sec-section">
    <div class="container sec-container">
      <div class="sec-header">
        <div class="sec-label reveal">Безопасность</div>
        <h2 class="sec-heading reveal">Защита без компромиссов</h2>
      </div>

      <div class="sec-orbit reveal">
        <!-- Connection lines -->
        <svg class="orbit-svg" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          <line
            v-for="(pt, i) in lineEnds" :key="i"
            x1="50" y1="50" :x2="pt.x" :y2="pt.y"
            vector-effect="non-scaling-stroke"
            class="orbit-line" :class="{ active: activeIndex === i }"
          />
        </svg>

        <!-- Concentric rings -->
        <div class="orbit-ring r1" aria-hidden="true" />
        <div class="orbit-ring r2" aria-hidden="true" />
        <div class="orbit-ring r3" aria-hidden="true" />

        <!-- Central shield -->
        <div class="orbit-center">
          <div class="orbit-glow" aria-hidden="true" />
          <div class="orbit-shield">
            <ShieldCheck :size="44" :stroke-width="1" />
          </div>
        </div>

        <!-- Orbital markers -->
        <div class="orbit-markers">
          <button
            v-for="(tab, i) in tabs" :key="tab.id"
            class="orbit-node" :class="['n' + i, { active: activeIndex === i }]"
            @click="selectTab(i)"
            :aria-label="tab.label"
          >
            <span class="node-icon">
              <svg
                v-if="activeIndex === i && !isPaused"
                :key="progressKey"
                class="node-ring"
                viewBox="0 0 60 60"
              >
                <circle cx="30" cy="30" r="28" />
              </svg>
              <component :is="iconMap[tab.icon]" :size="20" :stroke-width="1.5" />
            </span>
            <span class="node-text">{{ tab.label }}</span>
          </button>
        </div>

        <!-- Карточка снаружи орбиты: слот якорится к маркере, translate уводит от центра -->
        <Transition name="card-pop" mode="out-in">
          <div :key="activeIndex" class="orbit-card-slot" :class="'slot-' + activeIndex">
            <div class="orbit-card">
              <div class="orbit-card-label">{{ activeTab.label }}</div>
              <h4 class="orbit-card-title">{{ activeTab.heading }}</h4>
              <p class="orbit-card-body">{{ activeTab.body }}</p>
            </div>
          </div>
        </Transition>
      </div>

      <!-- Mobile-only detail (replaces orbit-card on small screens) -->
      <div class="sec-mobile-detail">
        <Transition name="sec-swap" mode="out-in">
          <div :key="activeIndex" class="mobile-panel">
            <h4 class="mobile-panel-title">{{ activeTab.heading }}</h4>
            <p class="mobile-panel-body">{{ activeTab.body }}</p>
          </div>
        </Transition>
      </div>
    </div>
  </section>
</template>

<style scoped>
section#security.sec-section {
  position: relative;
  /* карточки уходят за пределы орбиты к краю экрана */
  overflow-x: visible;
  overflow-y: visible;
  padding: clamp(72px, 10vh, 100px) 0;
  background: transparent;
}

.sec-container {
  position: relative;
  z-index: 1;
  overflow: visible;
}

/* ── Header ── */
.sec-header {
  text-align: center;
  margin-bottom: 24px;
}

.sec-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.sec-heading {
  font-family: var(--font-display);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.025em;
  color: var(--color-text);
}

/* ── Orbital arena (compact — no detail panel below) ── */
.sec-orbit {
  position: relative;
  width: 100%;
  max-width: 760px;
  min-height: 420px;
  margin: 0 auto;
  overflow: visible;
}

/* ── Connecting lines ── */
.orbit-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 0;
}

.orbit-line {
  stroke: rgba(59, 130, 246, 0.05);
  stroke-width: 1;
  stroke-dasharray: 6 6;
  transition: stroke 0.6s ease;
}

.orbit-line.active {
  stroke: rgba(59, 130, 246, 0.2);
  animation: dash-flow 2.5s linear infinite;
}

@keyframes dash-flow {
  to { stroke-dashoffset: -24; }
}

/* ── Concentric rings ── */
.orbit-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  border-radius: 50%;
  border: 1px solid rgba(59, 130, 246, 0.06);
  pointer-events: none;
  z-index: 0;
}

.orbit-ring.r1 {
  width: 140px;
  height: 140px;
  transform: translate(-50%, -50%);
  animation: ring-breathe 5s ease-in-out infinite;
}

.orbit-ring.r2 {
  width: 260px;
  height: 260px;
  transform: translate(-50%, -50%);
  animation: ring-breathe 5s ease-in-out infinite 0.7s;
}

.orbit-ring.r3 {
  width: 400px;
  height: 400px;
  transform: translate(-50%, -50%);
  animation: ring-breathe 5s ease-in-out infinite 1.4s;
}

@keyframes ring-breathe {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
    border-color: rgba(59, 130, 246, 0.06);
  }
  50% {
    transform: translate(-50%, -50%) scale(1.04);
    border-color: rgba(59, 130, 246, 0.14);
  }
}

/* ── Central shield ── */
.orbit-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 2;
}

.orbit-glow {
  position: absolute;
  width: 140px;
  height: 140px;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
  animation: glow-pulse 4s ease-in-out infinite;
}

@keyframes glow-pulse {
  0%, 100% { opacity: 0.5; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 1; transform: translate(-50%, -50%) scale(1.25); }
}

.orbit-shield {
  position: relative;
  width: 88px;
  height: 88px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(59, 130, 246, 0.1);
  backdrop-filter: blur(16px);
  box-shadow:
    0 8px 40px rgba(59, 130, 246, 0.08),
    inset 0 0 0 1px rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
}

/* ── Orbital markers ── */
.orbit-markers {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 3;
}

.orbit-node {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0;
  pointer-events: auto;
}

.orbit-node:focus { outline: none; }

.orbit-node.n0 { left: 12%; top: 22%; }
.orbit-node.n1 { left: 88%; top: 22%; }
.orbit-node.n2 { left: 88%; top: 78%; }
.orbit-node.n3 { left: 12%; top: 78%; }

.node-icon {
  position: relative;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
  box-shadow: 0 4px 24px rgba(15, 23, 42, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  transition:
    transform 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    border-color 0.4s ease,
    color 0.4s ease,
    background 0.4s ease,
    box-shadow 0.4s ease;
}

.orbit-node:hover .node-icon {
  transform: scale(1.08);
  border-color: rgba(59, 130, 246, 0.12);
  box-shadow: 0 4px 24px rgba(59, 130, 246, 0.08);
}

.orbit-node.active .node-icon {
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.06);
  border-color: rgba(59, 130, 246, 0.2);
  box-shadow: 0 0 32px rgba(59, 130, 246, 0.12);
  transform: scale(1.12);
}

.orbit-node:focus-visible .node-icon {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

/* ── Progress ring ── */
.node-ring {
  position: absolute;
  inset: -3px;
  width: calc(100% + 6px);
  height: calc(100% + 6px);
  pointer-events: none;
}

.node-ring circle {
  fill: none;
  stroke: rgba(59, 130, 246, 0.3);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-dasharray: 176;
  stroke-dashoffset: 176;
  transform: rotate(-90deg);
  transform-origin: center;
  animation: ring-fill 4.5s linear forwards;
}

@keyframes ring-fill {
  to { stroke-dashoffset: 0; }
}

.node-text {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
  white-space: nowrap;
  transition: color 0.35s ease, opacity 0.35s ease;
}

.orbit-node.active .node-text {
  color: var(--color-primary);
  opacity: 0;
}

.orbit-node:hover .node-text {
  color: var(--color-text);
}

/* ════════════════════════════════════════════
   Карточка снаружи: слот на маркере, translate — от щита к краю
   ════════════════════════════════════════════ */
.orbit-card-slot {
  position: absolute;
  z-index: 5;
  pointer-events: none;
}

.orbit-card-slot .orbit-card {
  pointer-events: auto;
}

/* Якорь по вертикали = центр маркера (22% / 78%); -50% по Y — центр карточки на этой линии */
.orbit-card-slot.slot-0 {
  left: 12%;
  top: 22%;
  transform: translate(calc(-100% - 28px), -50%);
}

.orbit-card-slot.slot-1 {
  left: 88%;
  top: 22%;
  transform: translate(28px, -50%);
}

.orbit-card-slot.slot-2 {
  left: 88%;
  top: 78%;
  transform: translate(28px, -50%);
}

.orbit-card-slot.slot-3 {
  left: 12%;
  top: 78%;
  transform: translate(calc(-100% - 28px), -50%);
}

.orbit-card {
  width: 280px;
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(59, 130, 246, 0.08);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  box-shadow: 0 8px 40px rgba(15, 23, 42, 0.07);
  text-align: left;
}

/* Масштаб — от стороны у маркера, по вертикали по центру карточки */
.slot-0 .orbit-card,
.slot-3 .orbit-card {
  transform-origin: 100% 50%;
}

.slot-1 .orbit-card,
.slot-2 .orbit-card {
  transform-origin: 0% 50%;
}

.orbit-card-label {
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-primary);
  letter-spacing: 0.06em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.orbit-card-title {
  font-family: var(--font-display);
  font-size: 15px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--color-text);
  margin-bottom: 8px;
}

.orbit-card-body {
  font-family: var(--font-body);
  font-size: 13px;
  line-height: 1.65;
  color: var(--color-text-secondary);
}

/* Анимация только на внутренней карточке (у слота свой translate) */
.card-pop-enter-active .orbit-card {
  transition:
    opacity 0.4s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.card-pop-leave-active .orbit-card {
  transition:
    opacity 0.25s ease,
    transform 0.25s ease;
}

.card-pop-enter-from .orbit-card {
  opacity: 0;
  transform: scale(0.85);
}

.card-pop-leave-to .orbit-card {
  opacity: 0;
  transform: scale(0.92);
}

/* ── Mobile detail panel (visible only on small screens) ── */
.sec-mobile-detail {
  display: none;
}

.mobile-panel {
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(15, 23, 42, 0.04);
  border-radius: 16px;
  backdrop-filter: blur(8px);
  text-align: center;
}

.mobile-panel-title {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-text);
  margin-bottom: 10px;
}

.mobile-panel-body {
  font-family: var(--font-body);
  font-size: 14px;
  line-height: 1.65;
  color: var(--color-text-secondary);
}

/* ── Mobile transition ── */
.sec-swap-enter-active,
.sec-swap-leave-active {
  transition:
    opacity 0.35s ease,
    transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.sec-swap-enter-from {
  opacity: 0;
  transform: translateY(10px);
}

.sec-swap-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

/* ── Reduced motion ── */
@media (prefers-reduced-motion: reduce) {
  .orbit-ring { animation: none; }
  .orbit-glow { animation: none; opacity: 0.7; }
  .orbit-line.active { animation: none; }
  .node-ring circle { animation: none; stroke-dashoffset: 0; }

  .card-pop-enter-active .orbit-card,
  .card-pop-leave-active .orbit-card {
    transition: opacity 0.15s ease;
  }

  .card-pop-enter-from .orbit-card,
  .card-pop-leave-to .orbit-card {
    transform: none;
  }

  .sec-swap-enter-active,
  .sec-swap-leave-active {
    transition: opacity 0.15s ease;
  }

  .sec-swap-enter-from,
  .sec-swap-leave-to {
    transform: none;
  }
}

/* ── Responsive: tablet ── */
@media (max-width: 900px) {
  .sec-orbit {
    max-width: 600px;
    min-height: 380px;
  }

  .orbit-ring.r3 {
    width: 320px;
    height: 320px;
  }

  .orbit-ring.r2 {
    width: 220px;
    height: 220px;
  }

  .orbit-card {
    width: 220px;
    padding: 16px 18px;
  }

  .orbit-card-slot.slot-0 {
    transform: translate(calc(-100% - 20px), -50%);
  }

  .orbit-card-slot.slot-1 {
    transform: translate(20px, -50%);
  }

  .orbit-card-slot.slot-2 {
    transform: translate(20px, -50%);
  }

  .orbit-card-slot.slot-3 {
    transform: translate(calc(-100% - 20px), -50%);
  }

  .orbit-card-title {
    font-size: 14px;
  }

  .orbit-card-body {
    font-size: 12px;
  }
}

/* ── Responsive: mobile ── */
@media (max-width: 768px) {
  .sec-orbit {
    min-height: auto;
    max-width: none;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 24px;
    padding: 24px 0;
  }

  .orbit-svg,
  .orbit-ring {
    display: none;
  }

  .orbit-center {
    position: static;
    transform: none;
  }

  .orbit-glow { display: none; }

  .orbit-shield {
    width: 72px;
    height: 72px;
    border-radius: 20px;
  }

  .orbit-markers {
    position: static;
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 12px;
    pointer-events: auto;
  }

  .orbit-node {
    position: static;
    transform: none;
  }

  .orbit-node.active .node-text {
    opacity: 1;
  }

  .node-icon {
    width: 48px;
    height: 48px;
  }

  .node-text {
    font-size: 11px;
  }

  .orbit-card-slot {
    display: none;
  }

  .sec-mobile-detail {
    display: block;
  }
}

@media (max-width: 480px) {
  .orbit-markers {
    gap: 8px;
  }

  .node-text {
    display: none;
  }
}
</style>
