<script setup>
defineProps({
  message: {
    type: String,
    default: 'Загрузка данных...'
  }
})
</script>

<template>
  <div class="loading-state">
    <div class="loader"></div>
    <span>{{ message }}</span>
  </div>
</template>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  gap: 1rem;
}

.loader {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
