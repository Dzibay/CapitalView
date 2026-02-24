<script setup>
const props = defineProps({
  title: { type: String, required: true },
  compact: { type: Boolean, default: false },
  icon: { type: Object, default: null } // Компонент иконки из lucide-vue-next
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
    
    <div class="widget-content" :class="{ 'widget-content--compact': compact }">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  transition: box-shadow 0.2s;
}

.widget:hover {
  box-shadow: 0 8px 16px rgba(0,0,0,0.06);
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
  border-radius: 8px;
  background-color: #F3F4F6; /* Единый светло-серый фон */
  color: #4B5563; /* Тёмно-серый цвет иконки */
  flex-shrink: 0;
}

.widget-title-icon-placeholder {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background-color: #F3F4F6;
}

.widget-title h2 {
  font-size: 0.95rem;
  font-weight: 500;
  color: #6B7280;
  letter-spacing: 0.3px;
  margin: 0;
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