<script setup>
import { ArrowRight, Check } from 'lucide-vue-next'

defineProps({
  trialDays: { type: Number, default: 14 },
  features: { type: Array, required: true },
  tariffs: { type: Array, default: () => [] },
})

function formatPrice(v) {
  return Number(v || 0).toLocaleString('ru-RU', { maximumFractionDigits: 0 })
}

function daysLabel(n) {
  const d = Number(n) || 0
  if (d % 10 === 1 && d % 100 !== 11) return `${d} день`
  if (d % 10 >= 2 && d % 10 <= 4 && (d % 100 < 10 || d % 100 >= 20)) return `${d} дня`
  return `${d} дней`
}
</script>

<template>
  <section id="pricing" class="section snap-section">
    <div class="container">
      <div class="pricing-hero reveal">
        <h2 class="pricing-heading">Тарифы и<br>пробный период</h2>
        <p class="pricing-sub">
          Новым пользователям доступен пробный период {{ daysLabel(trialDays) }} —
          полный доступ ко всем функциям без ограничений.
        </p>

        <div class="pricing-checklist">
          <span v-for="feat in features" :key="feat" class="pricing-check-item">
            <Check :size="15" :stroke-width="2.5" />
            {{ feat }}
          </span>
        </div>

        <div v-if="tariffs.length" class="tariff-row">
          <article v-for="t in tariffs" :key="t.id" class="tariff-card">
            <h3>{{ t.name }}</h3>
            <p class="price">{{ formatPrice(t.price_rub) }} ₽ <span>/ {{ t.period_days }} дн.</span></p>
            <p v-if="t.description" class="desc">{{ t.description }}</p>
          </article>
        </div>

        <router-link to="/login" class="pricing-cta">
          Попробовать {{ daysLabel(trialDays) }}
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
  max-width: 520px;
  margin: 0 auto 32px;
}

.pricing-checklist {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
  margin-bottom: 28px;
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

.tariff-row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 14px;
  margin-bottom: 28px;
}

.tariff-card {
  min-width: 200px;
  max-width: 280px;
  flex: 1;
  padding: 16px 18px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 16px;
  text-align: left;
  background: rgba(255, 255, 255, 0.7);
}

.tariff-card h3 {
  margin: 0 0 6px;
  font-size: 16px;
}

.price {
  margin: 0;
  font-size: 24px;
  font-weight: 700;
}

.price span {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.desc {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--color-text-secondary);
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
