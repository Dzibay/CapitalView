<template>
  <div class="page-header">
    <div class="page-header-content">
      <!-- Первый уровень: заголовок + переключатель (actions) -->
      <div class="page-header-row1">
        <div class="page-header-title">
          <h1>{{ title }}</h1>
          <h2 v-if="subtitle">{{ subtitle }}</h2>
        </div>
        <div v-if="$slots.actions" class="page-header-actions">
          <slot name="actions" />
        </div>
      </div>
      <!-- Второй уровень при сужении: только меню кнопок -->
      <div v-if="$slots.menu" class="page-header-menu">
        <slot name="menu" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-header {
  padding: 26px 0 28px;
  animation: ph-rise .7s var(--cv-ease) backwards;
}
@keyframes ph-rise { from { opacity: 0; transform: translateY(10px); } }

.page-header-content {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px 20px;
  flex-wrap: nowrap;
}

.page-header-row1 {
  display: flex;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: nowrap;
  min-width: 0;
  width: 100%;
}

.page-header-title { flex: 1 1 auto; min-width: 0; }

.page-header h1 {
  margin: 0;
  font-family: var(--cv-display);
  font-size: clamp(26px, 2.5vw, 34px);
  font-weight: 550;
  line-height: 1.12;
  letter-spacing: -0.035em;
  color: var(--cv-ink);
}

.page-header h2 {
  margin: 8px 0 0;
  font-family: var(--cv-text);
  font-size: 13.5px;
  font-weight: 400;
  line-height: 1.4;
  letter-spacing: 0;
  color: var(--cv-mut);
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 36px;
  flex: 0 0 auto;
  margin-left: auto;
  flex-wrap: wrap;
}

.page-header-menu {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: nowrap;
  min-width: 0;
  flex-shrink: 0;
}

@media (max-width: 1240px) {
  .page-header-content { flex-direction: column; align-items: flex-start; gap: 14px; }
  .page-header-menu { width: 100%; max-width: 100%; flex-wrap: wrap; }
}

@media (max-width: 768px) {
  .page-header { padding: 14px 0 20px; }
  .page-header-row1 { gap: 12px; align-items: flex-start; flex-wrap: wrap; }
  .page-header-actions { margin-left: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .page-header { animation: none; }
}
</style>
