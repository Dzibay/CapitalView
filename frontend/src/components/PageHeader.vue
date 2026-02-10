<template>
  <div class="page-header">
    <div class="page-header-content">
      <div>
        <h1>{{ title }}</h1>
        <h2 v-if="subtitle">{{ subtitle }}</h2>
      </div>
      <div v-if="$slots.actions" class="page-header-actions">
        <slot name="actions" />
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
  margin-bottom: var(--spacing);
}

.page-header-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.page-header h1 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #111827;
  margin: 0;
  line-height: 1.2;
}

.page-header h2 {
  font-size: 1rem;
  color: #6B7280;
  font-weight: 400;
  margin: 0;
  margin-top: 0.25rem;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

@media (max-width: 768px) {
  .page-header-content {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .page-header-actions {
    width: 100%;
  }
}
</style>
