<script setup>
/**
 * Полоса ключевых показателей страницы: одна карточка, ячейки через разделители.
 * items: [{ key, label, value, format, delta?, deltaKind?, note?, tone? }]
 *  - delta — изменение под числом (CvDelta), note — поясняющий текст рядом;
 *  - tone: 'up' | 'down' — окрасить само число (для прибыли/убытка).
 */
import CvNumber from './CvNumber.vue'
import CvDelta from './CvDelta.vue'

defineProps({
  items: { type: Array, required: true },
})
</script>

<template>
  <section class="cv-kpi cv-card" :style="{ '--n': items.length }">
    <div v-for="(k, i) in items" :key="k.key" class="cv-kpi__cell" :style="{ '--i': i }">
      <span class="cv-kpi__label">{{ k.label }}</span>
      <b class="cv-kpi__value" :class="k.tone ? `cv-${k.tone}` : ''">
        <CvNumber :value="Number(k.value) || 0" :format="k.format" :stagger="18" />
      </b>
      <span v-if="k.delta != null || k.note" class="cv-kpi__sub">
        <CvDelta v-if="k.delta != null" :value="k.delta" :kind="k.deltaKind || 'pct'" />
        <span v-if="k.note" class="cv-kpi__note">{{ k.note }}</span>
      </span>
    </div>
  </section>
</template>

<style scoped>
.cv-kpi {
  display: grid; grid-template-columns: repeat(var(--n), minmax(0, 1fr));
  padding: 20px 0;
}
.cv-kpi__cell {
  display: flex; flex-direction: column; gap: 6px; min-width: 0; padding: 0 24px;
  animation: cv-kpi-rise .7s var(--cv-ease) backwards; animation-delay: calc(var(--i) * 60ms + 140ms);
}
.cv-kpi__cell + .cv-kpi__cell { border-left: 1px solid var(--cv-line); }
.cv-kpi__label { font-size: 12.5px; color: var(--cv-mut); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-kpi__value {
  font-family: var(--cv-display); font-size: clamp(20px, 1.9vw, 26px); font-weight: 600; letter-spacing: -0.025em; line-height: 1.15;
  color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cv-kpi__value.cv-up { color: var(--cv-up); }
.cv-kpi__value.cv-down { color: var(--cv-down); }
.cv-kpi__sub { display: flex; align-items: center; gap: 8px; min-height: 22px; font-size: 12.5px; }
.cv-kpi__note { color: var(--cv-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

@keyframes cv-kpi-rise { from { opacity: 0; transform: translateY(8px); } }

@media (max-width: 1000px) {
  .cv-kpi { grid-template-columns: repeat(2, minmax(0, 1fr)); row-gap: 18px; }
  .cv-kpi__cell:nth-child(odd) { border-left: 0; }
  .cv-kpi__cell:nth-child(n + 3) { padding-top: 18px; border-top: 1px solid var(--cv-line); }
}
@media (max-width: 768px) {
  .cv-kpi { padding: 16px 0; }
  .cv-kpi__cell { padding: 0 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .cv-kpi__cell { animation: none; }
}
</style>
