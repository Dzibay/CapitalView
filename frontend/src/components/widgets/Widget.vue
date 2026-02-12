<script setup>
const props = defineProps({
  title: { type: String, required: true }
})
</script>

<template>
  <div class="widget">
    <div class="widget-header">
      <div class="widget-title">
        <div class="widget-title-icon-rect"></div>
        <h2>{{ title }}</h2>
      </div>
      <div v-if="$slots.header" class="widget-header-actions">
        <slot name="header" />
      </div>
    </div>
    
    <slot />
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
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
  gap: 5px;
  align-items: center;
  flex: 1;
}

.widget-header-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.widget-title-icon-rect {
  padding: 5px;
  width: 25px;
  height: 25px;
  border-radius: 6px;
  background-color: #F6F6F6;
}

.widget-title h2 {
  font-size: 1rem;
  font-weight: 400;
  color: #6B7280;
  margin: 0;
}
</style>
