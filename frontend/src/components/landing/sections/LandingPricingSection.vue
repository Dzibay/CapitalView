<script setup>
import { ArrowRight, Check } from 'lucide-vue-next'

defineProps({
  features: { type: Array, required: true }
})
</script>

<template>
  <section id="pricing" class="section snap-section">
    <div class="container">
      <div class="pricing-hero reveal">
        <h2 class="pricing-heading">Бесплатно.<br>Без скрытых платежей.</h2>
        <p class="pricing-sub">Все функции доступны без ограничений. Начните пользоваться прямо сейчас.</p>

        <div class="pricing-checklist">
          <span v-for="feat in features" :key="feat" class="pricing-check-item">
            <Check :size="15" :stroke-width="2.5" />
            {{ feat }}
          </span>
        </div>

        <router-link to="/login" class="pricing-cta">
          Начать бесплатно
          <ArrowRight :size="18" :stroke-width="2" />
        </router-link>
      </div>
    </div>
  </section>
</template>

<style scoped>
.pricing-hero {
  text-align: center;
  padding: clamp(40px, 6vh, 72px) 0;
}

.pricing-heading {
  font-family: var(--font-display);
  font-size: clamp(36px, 5vw, 56px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.025em;
  color: var(--color-text);
  margin-bottom: 16px;
}

.pricing-sub {
  font-size: 17px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  max-width: 480px;
  margin: 0 auto 32px;
}

.pricing-checklist {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 36px;
}

.pricing-check-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text);
}

.pricing-check-item svg {
  color: var(--color-success);
}

.pricing-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 16px 36px;
  border-radius: 999px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
  background: var(--color-primary);
  box-shadow: 0 6px 24px rgba(59, 130, 246, 0.28);
  transition: background 0.2s, transform 0.15s, box-shadow 0.2s;
}

.pricing-cta:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
  box-shadow: 0 10px 32px rgba(59, 130, 246, 0.34);
}

@media (max-width: 600px) {
  .pricing-checklist {
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
}
</style>
