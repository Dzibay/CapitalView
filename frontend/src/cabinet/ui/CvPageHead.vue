<script setup>
/**
 * Шапка страницы кабинета в стиле дашборда: надзаголовок, заголовок, строка контекста и действия справа.
 * Пункты строки контекста разделяются точкой: передайте массив строк в `meta`.
 */
defineProps({
  eyebrow: { type: String, default: '' },
  title: { type: String, required: true },
  meta: { type: Array, default: () => [] },
})
</script>

<template>
  <header class="cv-ph">
    <div class="cv-ph__titles">
      <p v-if="eyebrow" class="cv-ph__eyebrow cv-eyebrow">{{ eyebrow }}</p>
      <h1 class="cv-ph__title">{{ title }}</h1>
      <p v-if="meta.length || $slots.meta" class="cv-ph__meta">
        <template v-for="(m, i) in meta.filter(Boolean)" :key="i">
          <span v-if="i" class="cv-ph__dot" />
          <span>{{ m }}</span>
        </template>
        <slot name="meta" />
      </p>
    </div>
    <div v-if="$slots.actions" class="cv-ph__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.cv-ph {
  display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap;
  padding: 26px 0 30px;
}
.cv-ph__titles { min-width: 0; }
.cv-ph__eyebrow { color: var(--cv-dim); animation: cv-ph-rise .7s var(--cv-ease) backwards; }
.cv-ph__title {
  margin: 10px 0 0;
  font-family: var(--cv-display); font-size: clamp(26px, 2.5vw, 34px); font-weight: 550; line-height: 1.12; letter-spacing: -0.035em;
  color: var(--cv-ink);
  animation: cv-ph-rise .7s var(--cv-ease) backwards .04s;
}
.cv-ph__eyebrow + .cv-ph__title { margin-top: 10px; }
.cv-ph__titles > .cv-ph__title:first-child { margin-top: 0; }
.cv-ph__meta {
  display: flex; align-items: center; gap: 9px; flex-wrap: wrap; margin: 8px 0 0;
  font-size: 13.5px; color: var(--cv-mut);
  animation: cv-ph-rise .7s var(--cv-ease) backwards .08s;
}
.cv-ph__dot { width: 3px; height: 3px; border-radius: 50%; background: var(--cv-dim); }
.cv-ph__actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; animation: cv-ph-rise .7s var(--cv-ease) backwards .1s; }

@keyframes cv-ph-rise { from { opacity: 0; transform: translateY(14px); filter: blur(4px); } }

@media (max-width: 768px) {
  .cv-ph { padding: 14px 0 20px; align-items: flex-start; }
}
@media (prefers-reduced-motion: reduce) {
  .cv-ph__eyebrow, .cv-ph__title, .cv-ph__meta, .cv-ph__actions { animation: none; }
}
</style>
