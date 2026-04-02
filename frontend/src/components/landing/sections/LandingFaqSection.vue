<script setup>
import { ref } from 'vue'
import { Plus } from 'lucide-vue-next'

defineProps({
  items: { type: Array, required: true }
})

const openIndex = ref(null)

function toggle(i) {
  openIndex.value = openIndex.value === i ? null : i
}
</script>

<template>
  <section id="faq" class="section snap-section faq-section">
    <div class="container faq-container">
      <div class="faq-header">
        <div class="faq-label reveal">Поддержка</div>
        <h2 class="faq-heading reveal">Частые вопросы об учёте инвестиций</h2>
      </div>

      <div class="faq-list">
        <div
          v-for="(item, i) in items"
          :key="i"
          class="faq-row"
          :class="{ open: openIndex === i }"
        >
          <button
            class="faq-trigger"
            type="button"
            :aria-expanded="openIndex === i"
            @click="toggle(i)"
          >
            <span class="faq-num">{{ String(i + 1).padStart(2, '0') }}</span>
            <span class="faq-question">{{ item.question }}</span>
            <span class="faq-icon">
              <Plus :size="20" :stroke-width="1.8" />
            </span>
          </button>

          <div class="faq-body" :class="{ open: openIndex === i }">
            <div class="faq-answer">
              <p>{{ item.answer }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
section#faq.faq-section {
  position: relative;
  overflow: visible;
  padding: clamp(72px, 10vh, 100px) 0;
  background: transparent;
  /* сброс flex из .section.snap-section: center сдвигает блок при смене высоты */
  justify-content: flex-start;
}

.faq-container {
  position: relative;
  z-index: 1;
  width: 100%;
  min-width: 0;
}

/* ── Header ── */
.faq-header {
  text-align: center;
  margin-bottom: 56px;
}

.faq-label {
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 500;
  color: #94a3b8;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  margin-bottom: 20px;
}

.faq-heading {
  font-family: var(--font-display);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.025em;
  color: var(--color-text);
}

/* ── List: на всю ширину .container, без узкого 900px ── */
.faq-list {
  width: 100%;
  max-width: 100%;
}

/* ── Row ── */
.faq-row {
  width: 100%;
  border-top: 1px solid rgba(15, 23, 42, 0.06);
  transition: border-color 0.35s ease;
}

.faq-row.open {
  border-top-color: rgba(59, 130, 246, 0.12);
}

.faq-row:last-child {
  border-bottom: 1px solid rgba(15, 23, 42, 0.06);
}

/* ── Trigger ── */
.faq-trigger {
  box-sizing: border-box;
  width: calc(100% + 24px);
  max-width: none;
  background: transparent;
  border: none;
  padding: 28px 12px;
  margin: 0 -12px;
  display: grid;
  grid-template-columns: 48px 1fr 40px;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  text-align: left;
  border-radius: 12px;
  transition: background-color 0.3s cubic-bezier(0.16, 1, 0.3, 1),
    transform 0.22s cubic-bezier(0.16, 1, 0.3, 1),
    box-shadow 0.3s ease;
}



.faq-trigger:active {
  transform: scale(0.995);
}

.faq-trigger:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}

.faq-num {
  font-family: var(--font-display);
  font-weight: 200;
  font-size: 28px;
  line-height: 1;
  color: rgba(59, 130, 246, 0.15);
  letter-spacing: -0.04em;
  transition: color 0.35s;
}

.faq-question {
  font-family: var(--font-body);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
  color: var(--color-text);
  transition: color 0.35s;
  min-width: 0;
  word-wrap: break-word;
}

.faq-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: 1px solid rgba(15, 23, 42, 0.08);
  color: var(--color-text-secondary);
  transition: transform 0.45s cubic-bezier(0.16, 1, 0.3, 1),
    color 0.35s ease,
    border-color 0.35s ease,
    background 0.35s ease,
    box-shadow 0.35s ease;
  flex-shrink: 0;
  justify-self: end;
}

.faq-trigger:hover .faq-icon {
  transform: scale(1.06);
  box-shadow: 0 2px 12px rgba(15, 23, 42, 0.08);
}

/* ── Open state ── */
.faq-row.open .faq-num {
  color: rgba(59, 130, 246, 0.55);
}

.faq-row.open .faq-question {
  color: var(--color-primary);
}

.faq-row.open .faq-icon {
  transform: rotate(45deg);
  color: #fff;
  background: var(--color-primary);
  border-color: var(--color-primary);
  box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
}

.faq-row.open .faq-trigger:hover .faq-icon {
  transform: rotate(45deg) scale(1.06);
}

/* ── Answer: высота + мягкое появление текста ── */
.faq-body {
  width: 100%;
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.5s cubic-bezier(0.33, 1, 0.32, 1);
}

.faq-body.open {
  max-height: 2000px;
}

.faq-answer {
  overflow: visible;
  opacity: 0;
  transform: translateY(-8px);
  transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
}

.faq-body.open .faq-answer {
  opacity: 1;
  transform: translateY(0);
  transition: opacity 0.45s ease 0.1s, transform 0.5s cubic-bezier(0.16, 1, 0.3, 1) 0.06s;
}

.faq-answer p {
  font-family: var(--font-body);
  font-size: 15px;
  line-height: 1.75;
  color: var(--color-text-secondary);
  padding: 0 0 28px;
  margin-left: 64px;
  max-width: 56rem;
}

@media (prefers-reduced-motion: reduce) {
  .faq-body {
    transition: none;
  }

  .faq-body.open {
    max-height: none;
  }

  .faq-answer,
  .faq-body.open .faq-answer {
    transition: none;
    transform: none;
  }

  .faq-body.open .faq-answer {
    opacity: 1;
  }

  .faq-body:not(.open) .faq-answer {
    opacity: 0;
  }

  .faq-trigger {
    transition: none;
  }

  .faq-trigger:active {
    transform: none;
  }

  .faq-icon,
  .faq-row.open .faq-trigger:hover .faq-icon {
    transition: transform 0.2s ease, color 0.2s ease, border-color 0.2s ease,
      background 0.2s ease;
  }

  .faq-trigger:hover .faq-icon {
    transform: none;
    box-shadow: none;
  }

  .faq-row.open .faq-icon {
    box-shadow: none;
  }
}

/* ── Responsive ── */
@media (max-width: 767px) {
  .faq-trigger {
    grid-template-columns: 36px 1fr 36px;
    padding: 22px 12px;
    gap: 12px;
  }

  .faq-num {
    font-size: 22px;
  }

  .faq-question {
    font-size: 15px;
  }

  .faq-icon {
    width: 32px;
    height: 32px;
  }

  .faq-answer p {
    margin-left: 48px;
    padding-bottom: 22px;
  }
}

@media (max-width: 480px) {
  .faq-trigger {
    grid-template-columns: 1fr 36px;
  }

  .faq-num {
    display: none;
  }

  .faq-answer p {
    margin-left: 0;
  }
}
</style>
