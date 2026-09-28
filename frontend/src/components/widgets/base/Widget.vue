<script setup>
const props = defineProps({
  title: { type: String, required: true },
  compact: { type: Boolean, default: false },
  icon: { type: [Object, Function], default: null } // Компонент иконки из lucide-vue-next (может быть функцией или объектом)
})
</script>

<template>
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title">
        <div class="widget-title-icon" v-if="icon">
          <component :is="icon" :size="18" stroke-width="1.5" />
        </div>
        <div class="widget-title-icon-placeholder" v-else></div>
        <h2>{{ title }}</h2>
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
  background-color: var(--surface, #fff);
  border-radius: var(--radius-md, 8px);
  border: 1px solid var(--border-subtle, #d8dee6);
  padding: 1rem 1.25rem;
  box-shadow: none;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  transition: border-color 0.15s ease;
}
@media (max-width: 768px) {
  .widget {
    padding: 0.75rem 1rem;
  }
}

.widget:hover {
  box-shadow: none;
  border-color: var(--border-strong, #c5ced8);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.widget-title {
  display: flex;
  gap: 8px;
  align-items: center;
  flex: 1;
}

.widget-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.widget-title-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm, 6px);
  background-color: var(--bg-tertiary, #e4e8ed);
  color: var(--text-secondary, #3d4654);
  flex-shrink: 0;
}

.widget-title-icon-placeholder {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-sm, 6px);
  background-color: var(--bg-tertiary, #e4e8ed);
}

.widget-title h2 {
  font-size: var(--text-heading-3-size);
  font-weight: var(--text-heading-3-weight);
  color: var(--text-heading-3-color);
  letter-spacing: 0.3px;
  margin: 0;
}

.widget-subheader {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.5rem;
  flex-wrap: wrap;
}

.widget-content {
  margin-top: 0.75rem;
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.widget-content--compact {
  margin-top: 0;
}
</style>