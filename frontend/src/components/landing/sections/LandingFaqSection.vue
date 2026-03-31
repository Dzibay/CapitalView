<script setup>
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

defineProps({
  items: { type: Array, required: true }
})

const openIndex = ref(null)

function toggle(i) {
  openIndex.value = openIndex.value === i ? null : i
}
</script>

<template>
  <section id="faq" class="section snap-section">
    <div class="container">
      <div class="faq-wrapper">
        <h2 class="faq-heading reveal">Частые вопросы</h2>
        <div class="faq-list">
          <div
            v-for="(item, i) in items"
            :key="i"
            class="faq-item"
            :class="{ open: openIndex === i }"
          >
            <button class="faq-question" type="button" :aria-expanded="openIndex === i" @click="toggle(i)">
              <span>{{ item.question }}</span>
              <ChevronDown :size="20" class="faq-chevron" />
            </button>
            <div class="faq-answer-container">
              <div class="faq-answer">
                <p>{{ item.answer }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.faq-wrapper {
  max-width: 720px;
  margin: 0 auto;
  background: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.08);
  border-radius: 24px;
  padding: clamp(32px, 5vw, 56px);
}

.faq-heading {
  font-family: var(--font-display);
  font-size: clamp(28px, 3.5vw, 40px);
  font-weight: 300;
  line-height: 1.1;
  letter-spacing: -0.02em;
  color: var(--color-text);
  text-align: center;
  margin-bottom: 36px;
}

.faq-list {
  display: flex;
  flex-direction: column;
}

.faq-item {
  border-bottom: 1px solid rgba(16, 185, 129, 0.12);
}

.faq-item:first-child {
  border-top: 1px solid rgba(16, 185, 129, 0.12);
}

.faq-question {
  width: 100%;
  background: none;
  border: none;
  padding: 20px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  text-align: left;
  font-family: var(--font-body);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  gap: 16px;
  transition: color 0.2s;
}

.faq-question:hover {
  color: var(--color-primary);
}

.faq-chevron {
  color: var(--color-text-secondary);
  transition: transform 0.3s;
  flex-shrink: 0;
}

.faq-item.open .faq-chevron {
  transform: rotate(180deg);
}

.faq-item.open .faq-question {
  color: var(--color-primary);
}

.faq-answer-container {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.faq-item.open .faq-answer-container {
  grid-template-rows: 1fr;
}

.faq-answer {
  min-height: 0;
}

.faq-answer p {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  padding: 0 0 20px;
}
</style>
