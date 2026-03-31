<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ArrowUpRight, Check } from 'lucide-vue-next'

const props = defineProps({
  bullets: { type: Array, required: true },
  comingSoonBrokers: { type: Array, required: true }
})

const activeStep = ref(0)
let timer = null
const INTERVAL = 3500

const syncItems = [
  { label: 'Активы и позиции', delay: 0 },
  { label: 'История сделок', delay: 400 },
  { label: 'Дивиденды', delay: 800 },
  { label: 'Купоны', delay: 1200 }
]

function startTimer() {
  clearInterval(timer)
  timer = setInterval(() => {
    activeStep.value = (activeStep.value + 1) % 3
  }, INTERVAL)
}

function setStep(i) {
  activeStep.value = i
  startTimer()
}

onMounted(() => startTimer())
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <section id="integrations" class="section snap-section integ-section">
    <div class="container integ-container">
      <div class="integ-layout reveal">
        <!-- Left: text -->
        <div class="integ-text">
          <div class="integ-label">Подключение</div>
          <h2 class="integ-title">Подключите брокера<br>за 2 минуты</h2>
          <p class="integ-desc">
            Получите полный контроль над инвестициями. Все сделки, дивиденды и купоны
            синхронизируются автоматически через официальный API.
          </p>

          <div class="integ-features">
            <div v-for="(bullet, i) in bullets" :key="i" class="integ-feature">
              <span class="integ-feature-dot" />
              {{ bullet }}
            </div>
          </div>

          <router-link to="/login" class="integ-cta">
            Подключить Т-Инвестиции
            <ArrowUpRight :size="18" :stroke-width="2" />
          </router-link>

          <div class="integ-coming">
            <span class="integ-coming-label">Скоро</span>
            <div class="integ-coming-list">
              <div
                v-for="broker in comingSoonBrokers"
                :key="broker.name"
                class="integ-coming-item"
              >
                <div
                  class="integ-coming-avatar"
                  :style="{ borderColor: broker.color, color: broker.color }"
                >
                  {{ broker.initials }}
                </div>
                <span>{{ broker.name }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Right: interactive terminal widget -->
        <div class="integ-widget">
          <div class="term">
            <!-- Step indicators -->
            <div class="term-steps">
              <button
                v-for="(s, i) in ['Брокер', 'Синхронизация', 'Готово']"
                :key="i"
                class="term-step"
                :class="{ active: i === activeStep, done: i < activeStep }"
                @click="setStep(i)"
              >
                <span class="term-step-dot">
                  <Check v-if="i < activeStep" :size="12" :stroke-width="3" />
                  <span v-else class="term-step-num">{{ i + 1 }}</span>
                </span>
                <span class="term-step-label">{{ s }}</span>
              </button>
              <div class="term-steps-track">
                <div class="term-steps-fill" :style="{ width: (activeStep / 2 * 100) + '%' }" />
              </div>
            </div>

            <!-- Content area -->
            <div class="term-body">
              <Transition name="term-fade" mode="out-in">
                <!-- Step 0: Choose broker -->
                <div v-if="activeStep === 0" key="s0" class="term-panel">
                  <div class="term-broker">
                    <div class="term-broker-logo">
                      <span>Т</span>
                    </div>
                    <div class="term-broker-info">
                      <div class="term-broker-name">Т-Инвестиции</div>
                      <div class="term-broker-api">Tinkoff Invest API</div>
                    </div>
                    <div class="term-broker-badge">Рекомендуем</div>
                  </div>
                  <div class="term-broker-features">
                    <div class="term-bf"><Check :size="14" :stroke-width="2.5" /> Read-only доступ</div>
                    <div class="term-bf"><Check :size="14" :stroke-width="2.5" /> Авторизация OAuth 2.0</div>
                    <div class="term-bf"><Check :size="14" :stroke-width="2.5" /> Без доступа к средствам</div>
                  </div>
                  <button class="term-connect-btn" @click="setStep(1)">
                    Подключить
                    <ArrowUpRight :size="16" :stroke-width="2" />
                  </button>
                </div>

                <!-- Step 1: Syncing -->
                <div v-else-if="activeStep === 1" key="s1" class="term-panel">
                  <div class="term-sync-header">
                    <div class="term-sync-spinner" />
                    <span>Синхронизация данных...</span>
                  </div>
                  <div class="term-progress">
                    <div class="term-progress-bar" />
                  </div>
                  <div class="term-sync-items">
                    <div
                      v-for="(item, i) in syncItems"
                      :key="i"
                      class="term-sync-item"
                      :style="{ animationDelay: item.delay + 'ms' }"
                    >
                      <span class="term-sync-check"><Check :size="14" :stroke-width="2.5" /></span>
                      <span>{{ item.label }}</span>
                    </div>
                  </div>
                </div>

                <!-- Step 2: Done -->
                <div v-else key="s2" class="term-panel">
                  <div class="term-done-icon">
                    <Check :size="28" :stroke-width="2.5" />
                  </div>
                  <div class="term-done-title">Подключено</div>
                  <div class="term-done-sub">Все данные синхронизированы</div>
                  <div class="term-done-stats">
                    <div class="term-done-stat">
                      <span class="term-done-val">3</span>
                      <span class="term-done-lbl">Портфеля</span>
                    </div>
                    <div class="term-done-stat">
                      <span class="term-done-val">24</span>
                      <span class="term-done-lbl">Актива</span>
                    </div>
                    <div class="term-done-stat">
                      <span class="term-done-val">1 247</span>
                      <span class="term-done-lbl">Сделок</span>
                    </div>
                  </div>
                  <div class="term-done-bars">
                    <div class="term-done-bar" style="height:35%"></div>
                    <div class="term-done-bar" style="height:52%"></div>
                    <div class="term-done-bar" style="height:40%"></div>
                    <div class="term-done-bar" style="height:68%"></div>
                    <div class="term-done-bar" style="height:55%"></div>
                    <div class="term-done-bar" style="height:78%"></div>
                    <div class="term-done-bar" style="height:62%"></div>
                    <div class="term-done-bar" style="height:90%"></div>
                    <div class="term-done-bar" style="height:72%"></div>
                    <div class="term-done-bar" style="height:85%"></div>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
section#integrations.integ-section {
  position: relative;
  overflow: hidden;
  /* Центрирование как у .container, но через padding секции — без margin:auto у flex-ребёнка */
  padding: clamp(72px, 10vh, 100px) max(0px, calc((100% - 1200px) / 2));
  background: transparent;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  box-sizing: border-box;
}

section#integrations.integ-section .integ-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: none;
  margin-left: 0;
  margin-right: 0;
  box-sizing: border-box;
}

/* ── Layout ── */
.integ-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(40px, 5vw, 72px);
  align-items: center;
}

/* ── Left: text ── */
.integ-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.integ-title {
  font-family: var(--font-display);
  font-size: clamp(32px, 4vw, 44px);
  font-weight: 300;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: #0f172a;
  margin-bottom: 16px;
}

.integ-desc {
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  color: #64748b;
  max-width: 440px;
  margin-bottom: 24px;
}

.integ-features {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 32px;
}
.integ-feature {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  line-height: 1.4;
  color: #475569;
}
.integ-feature-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3b82f6;
  flex-shrink: 0;
}

.integ-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border-radius: 999px;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
  background: #0f172a;
  transition: background 0.2s;
  margin-bottom: 32px;
}
.integ-cta:hover {
  background: #1e293b;
}

/* ── Coming soon ── */
.integ-coming {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}
.integ-coming-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.integ-coming-list {
  display: flex;
  gap: 16px;
}
.integ-coming-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.integ-coming-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 2px dashed #d4d9e1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.integ-coming-item span {
  font-family: var(--font-body);
  font-size: 13px;
  color: #94a3b8;
}

/* ══════════════════════════════════════════
   Right: Interactive Terminal Widget
   ══════════════════════════════════════════ */
.integ-widget {
  min-width: 0;
}

.term {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 40px rgba(15, 23, 42, 0.06);
  padding: 28px;
  overflow: hidden;
}

/* ── Step indicators ── */
.term-steps {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0;
  margin-bottom: 28px;
  position: relative;
  padding-bottom: 20px;
}

.term-step {
  display: flex;
  align-items: center;
  gap: 8px;
  background: none;
  border: none;
  padding: 0;
  cursor: pointer;
  flex: 0 0 auto;
  position: relative;
  z-index: 1;
}

.term-step-dot {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  color: #94a3b8;
}
.term-step-num {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
}
.term-step.active .term-step-dot {
  background: #3b82f6;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.15);
}
.term-step.done .term-step-dot {
  background: #22c55e;
  color: #fff;
}

.term-step-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  white-space: nowrap;
  transition: color 0.3s;
}
.term-step.active .term-step-label {
  color: #0f172a;
  font-weight: 600;
}
.term-step.done .term-step-label {
  color: #22c55e;
}

/* Track connecting the dots */
.term-steps-track {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: #e2e8f0;
  border-radius: 2px;
}
.term-steps-fill {
  height: 100%;
  border-radius: 2px;
  background: linear-gradient(90deg, #22c55e, #3b82f6);
  transition: width 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Transitions ── */
.term-fade-enter-active,
.term-fade-leave-active {
  transition: opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1), transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
.term-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.term-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* ── Panel ── */
.term-body {
  min-height: 260px;
  display: flex;
  flex-direction: column;
}
.term-panel {
  display: flex;
  flex-direction: column;
}

/* ══ Step 0: Broker ══ */
.term-broker {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.06);
  margin-bottom: 20px;
}
.term-broker-logo {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: #fef08a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-body);
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  flex-shrink: 0;
  animation: logoPulse 2.5s ease-in-out infinite;
}
@keyframes logoPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(254, 240, 138, 0.4); }
  50% { box-shadow: 0 0 0 8px rgba(254, 240, 138, 0); }
}

.term-broker-info {
  flex: 1;
  min-width: 0;
}
.term-broker-name {
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 2px;
}
.term-broker-api {
  font-family: var(--font-body);
  font-size: 12px;
  color: #94a3b8;
}
.term-broker-badge {
  padding: 4px 10px;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.08);
  color: #3b82f6;
  white-space: nowrap;
}

.term-broker-features {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
}
.term-bf {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: #475569;
}
.term-bf svg {
  color: #22c55e;
  flex-shrink: 0;
}

.term-connect-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  width: 100%;
  padding: 12px;
  border-radius: 12px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  background: #0f172a;
  border: none;
  cursor: pointer;
  transition: background 0.2s;
}
.term-connect-btn:hover {
  background: #1e293b;
}

/* ══ Step 1: Syncing ══ */
.term-sync-header {
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 20px;
}
.term-sync-spinner {
  width: 20px;
  height: 20px;
  border: 2.5px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: termSpin 0.8s linear infinite;
}
@keyframes termSpin {
  to { transform: rotate(360deg); }
}

.term-progress {
  height: 6px;
  border-radius: 3px;
  background: #e2e8f0;
  overflow: hidden;
  margin-bottom: 24px;
}
.term-progress-bar {
  height: 100%;
  border-radius: 3px;
  background: linear-gradient(90deg, #3b82f6, #8b5cf6);
  animation: termFill 3.2s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
@keyframes termFill {
  from { width: 0%; }
  to { width: 100%; }
}

.term-sync-items {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.term-sync-item {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  opacity: 0;
  transform: translateX(-8px);
  animation: termItemIn 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}
@keyframes termItemIn {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.term-sync-check {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* ══ Step 2: Done ══ */
.term-done-icon {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: rgba(34, 197, 94, 0.1);
  color: #22c55e;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
}
.term-done-title {
  font-family: var(--font-body);
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  text-align: center;
  margin-bottom: 4px;
}
.term-done-sub {
  font-family: var(--font-body);
  font-size: 13px;
  color: #94a3b8;
  text-align: center;
  margin-bottom: 24px;
}

.term-done-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.term-done-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 0;
  border-radius: 10px;
  background: rgba(15, 23, 42, 0.02);
}
.term-done-val {
  font-family: var(--font-body);
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}
.term-done-lbl {
  font-family: var(--font-body);
  font-size: 11px;
  color: #94a3b8;
}

.term-done-bars {
  display: flex;
  align-items: flex-end;
  gap: 3px;
  height: 40px;
}
.term-done-bar {
  flex: 1;
  border-radius: 2px;
  background: rgba(59, 130, 246, 0.2);
  animation: termBarGrow 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  transform-origin: bottom;
}
@keyframes termBarGrow {
  from { transform: scaleY(0); }
  to { transform: scaleY(1); }
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .integ-layout {
    grid-template-columns: 1fr;
    gap: 40px;
  }
  .integ-title {
    font-size: 32px;
  }
}

@media (max-width: 600px) {
  .integ-title {
    font-size: 28px;
  }
  .term {
    padding: 20px;
  }
  .term-body {
    min-height: 220px;
  }
  .term-step-label {
    display: none;
  }
}
</style>
