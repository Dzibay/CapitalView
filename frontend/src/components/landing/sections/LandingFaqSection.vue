<script setup>
import FaqAccordion from '../../faq/FaqAccordion.vue'

defineProps({
  items: { type: Array, required: true },
})
</script>

<template>
  <section id="faq" class="section snap-section faq-section">
    <div class="container faq-container">
      <div class="faq-header">
        <div class="faq-label reveal">Поддержка</div>
        <h2 class="faq-heading reveal">Частые вопросы об учёте инвестиций</h2>
      </div>

      <FaqAccordion :items="items" />
    </div>
  </section>
</template>

<style scoped>
section#faq.faq-section {
  position: relative;
  overflow: visible;
  padding: clamp(72px, 10vh, 100px) 0;
  background: transparent;
  justify-content: flex-start;
}

.faq-container {
  position: relative;
  z-index: 1;
  width: 100%;
  min-width: 0;
}

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
</style>
