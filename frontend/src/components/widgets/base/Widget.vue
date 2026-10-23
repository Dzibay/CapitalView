<script setup>
const props = defineProps({
  title: { type: String, required: true },
  compact: { type: Boolean, default: false },
  icon: { type: [Object, Function], default: null } // Компонент иконки из lucide-vue-next (может быть функцией или объектом)
})
</script>

<template>
  <div class="widget cv-card">
    <div class="widget-header">
      <div class="widget-title">
        <h2 class="cv-eyebrow">{{ title }}</h2>
      </div>
      <div v-if="$slots.header" class="widget-header-actions">
        <slot name="header" />
      </div>
    </div>

    <div v-if="$slots.subheader" class="widget-subheader">
      <slot name="subheader" />
    </div>
    
    <div class="widget-content" :class="{ 'widget-content--compact': compact }">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.widget {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-width: 0;
  padding: 22px 24px 24px;
}
@media (max-width: 768px) {
  .widget { padding: 18px 16px 18px; }
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px 16px;
  min-height: 30px;
}

.widget-title { display: flex; align-items: center; flex: 1; min-width: 0; }

.widget-title h2 {
  margin: 0;
  font-family: var(--cv-text);
  font-size: 11px;
  font-weight: 550;
  line-height: 1.3;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--cv-mut);
}

.widget-header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.widget-subheader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.widget-content {
  margin-top: 16px;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.widget-content--compact { margin-top: 0; }
</style>
