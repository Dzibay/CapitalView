<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  items: { type: Array, required: true }
})

const activeIndex = ref(0)
const activeItem = computed(() => props.items[activeIndex.value])

function setStep(i) {
  activeIndex.value = i
}
</script>

<template>
  <section id="how-it-works" class="section snap-section steps-section">
    <!-- Плавающий orb -->
    <div class="steps-glow-orb" aria-hidden="true" />

    <!-- Та же сетка отступов, что у остальных секций (.container) -->
    <div class="container steps-inner">
      <div class="steps-left">
        <div class="steps-label reveal">Как это работает</div>

        <div class="steps-content">
          <Transition name="step-slide" mode="out-in">
            <div :key="activeIndex" class="steps-slide">
              <div class="steps-slide-num">{{ activeItem.number }}</div>
              <h2 class="steps-slide-title" v-html="activeItem.title.replace(' ', '<br>')" />
              <p class="steps-slide-desc">{{ activeItem.desc }}</p>
            </div>
          </Transition>
        </div>

        <div class="steps-dots">
          <button
            v-for="(item, i) in items"
            :key="i"
            class="steps-dot"
            :class="{ active: i === activeIndex }"
            :aria-label="`Шаг ${i + 1}`"
            @click="setStep(i)"
          />
        </div>
      </div>
    </div>

    <!-- Вне .container: top:50% от секции — вертикальное центрирование как в исходном макете -->
    <div class="steps-mock-float reveal">
      <div class="steps-mock-label">Портфель</div>
      <Transition name="mock-fade" mode="out-in">
        <div :key="activeIndex" class="steps-mock-data">
          <div class="steps-mock-stat">{{ activeItem.stat }}</div>
          <div class="steps-mock-change">{{ activeItem.change }}</div>
        </div>
      </Transition>
      <div class="steps-mock-bars">
        <div
          v-for="(h, i) in activeItem.bars"
          :key="i"
          class="steps-mock-bar"
          :style="{ height: h + '%' }"
        />
      </div>
    </div>

    <div class="steps-badges">
      <button
        v-for="(item, i) in items"
        :key="i"
        class="steps-badge"
        :class="{ active: i === activeIndex }"
        @click="setStep(i)"
      >
        {{ item.number }}
      </button>
    </div>
  </section>
</template>

<style scoped>
/* ══════════════════════════════════════════
   Точная копия варианта C в светлом стиле
   ══════════════════════════════════════════
   Важно: .cv-landing .section.snap-section в landing-page.css задаёт padding и
   flex с column + justify center с более высокой специфичностью, чем один класс
   в scoped — блок .steps-left (width: 50%) оказывался по центру («отступ слева»).
   Селектор с #how-it-works переопределяет глобальные правила.
   ══════════════════════════════════════════ */
section#how-it-works.steps-section {
  position: relative;
  overflow: hidden;
  /* Горизонталь: как у других секций — только через .container внутри */
  padding: clamp(72px, 10vh, 100px) 0;
  min-height: 680px;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  background: transparent;
  /* Правый край мока/бейджей = правый край контентной области .container */
  --steps-mock-right: max(24px, calc((100% - 1200px) / 2 + 24px));
}

.steps-inner {
  position: relative;
  width: 100%;
}

/* ── Плавающий orb ── */
.steps-glow-orb {
  position: absolute;
  width: 320px;
  height: 320px;
  border-radius: 50%;
  right: 10%;
  top: 50%;
  transform: translateY(-50%);
  background: radial-gradient(circle, rgba(59, 130, 246, 0.05) 0%, transparent 70%);
  pointer-events: none;
  animation: steps-orb-float 8s ease-in-out infinite;
}
@keyframes steps-orb-float {
  0%, 100% { transform: translateY(-50%) scale(1); }
  50% { transform: translateY(-55%) scale(1.1); }
}

/* ── Левая часть ── */
.steps-left {
  position: relative;
  z-index: 2;
  max-width: 520px;
  width: 50%;
}

.steps-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 24px;
}

.steps-content {
  position: relative;
  min-height: 320px;
}

.steps-slide-num {
  font-family: var(--font-display);
  font-weight: 100;
  font-size: 120px;
  line-height: 1;
  color: rgba(59, 130, 246, 0.08);
  letter-spacing: -0.06em;
  margin-bottom: -20px;
}

.steps-slide-title {
  font-family: var(--font-display);
  font-weight: 300;
  font-size: 44px;
  line-height: 1.1;
  letter-spacing: -0.03em;
  color: #0f172a;
  margin-bottom: 20px;
}

.steps-slide-desc {
  font-family: var(--font-body);
  font-size: 16px;
  line-height: 1.7;
  color: #64748b;
  max-width: 420px;
}

/* ── Slide transition ── */
.step-slide-enter-active,
.step-slide-leave-active {
  transition:
    opacity 0.5s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.step-slide-enter-from {
  opacity: 0;
  transform: translateY(24px);
}
.step-slide-leave-to {
  opacity: 0;
  transform: translateY(-12px);
}

/* ── Dots ── */
.steps-dots {
  display: flex;
  gap: 8px;
  margin-top: 40px;
}
.steps-dot {
  width: 32px;
  height: 4px;
  border-radius: 2px;
  background: #e2e8f0;
  border: none;
  padding: 0;
  cursor: pointer;
  transition: background 0.4s, width 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.steps-dot.active {
  width: 48px;
  background: #3b82f6;
}

/* ── Mock-карточка: центр по вертикали секции, не по высоте .steps-inner ── */
.steps-mock-float {
  position: absolute;
  right: var(--steps-mock-right);
  top: 50%;
  transform: translateY(-50%);
  width: 280px;
  padding: 24px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 40px rgba(15, 23, 42, 0.06);
  z-index: 2;
}

.steps-mock-label {
  font-family: var(--font-body);
  font-size: 10px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 14px;
}

.steps-mock-stat {
  font-family: var(--font-body);
  font-weight: 400;
  font-size: 32px;
  font-variant-numeric: tabular-nums;
  line-height: 1.15;
  letter-spacing: -0.02em;
  color: #0f172a;
  margin-bottom: 6px;
}

.steps-mock-change {
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 600;
  color: #22c55e;
  margin-bottom: 16px;
}

/* ── Mock data transition ── */
.mock-fade-enter-active,
.mock-fade-leave-active {
  transition:
    opacity 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}
.mock-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.mock-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.steps-mock-bars {
  display: flex;
  gap: 3px;
  align-items: flex-end;
  height: 40px;
}
.steps-mock-bar {
  flex: 1;
  border-radius: 2px;
  background: rgba(59, 130, 246, 0.2);
  transition: height 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

/* ── Номера-переключатели внизу справа (та же колонка, что и мок) ── */
.steps-badges {
  position: absolute;
  right: var(--steps-mock-right);
  bottom: clamp(32px, 8vh, 56px);
  display: flex;
  gap: 16px;
  z-index: 2;
}
.steps-badge {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-display);
  font-weight: 200;
  font-size: 28px;
  line-height: 1;
  color: #94a3b8;
  cursor: pointer;
  padding: 0;
  transition: all 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
.steps-badge:hover {
  border-color: rgba(15, 23, 42, 0.1);
  color: #64748b;
}
.steps-badge.active {
  background: rgba(59, 130, 246, 0.08);
  border-color: rgba(59, 130, 246, 0.2);
  color: #3b82f6;
  box-shadow: 0 0 32px rgba(59, 130, 246, 0.1);
  transform: scale(1.08);
}

/* ── Responsive (как steps-test.html: мок и бейджи скрыты, только точки) ── */
@media (max-width: 900px) {
  section#how-it-works.steps-section {
    padding: 48px 0;
    min-height: auto;
  }
  .steps-inner {
    min-height: 0;
    padding-bottom: 0;
  }
  .steps-left {
    max-width: 100%;
    width: 100%;
  }
  .steps-mock-float {
    display: none;
  }
  .steps-badges {
    display: none;
  }
}

@media (max-width: 600px) {
  section#how-it-works.steps-section {
    padding: 40px 0;
  }
  .steps-slide-num {
    font-size: 80px;
  }
  .steps-slide-title {
    font-size: 32px;
  }
  .steps-badge {
    width: 52px;
    height: 52px;
    font-size: 22px;
    border-radius: 12px;
  }
}
</style>
