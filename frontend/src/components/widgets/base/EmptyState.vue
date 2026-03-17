<script setup>
defineProps({
  message: {
    type: String,
    default: 'Нет данных'
  }
})
</script>

<template>
  <div class="empty-state">
    <p>{{ message }}</p>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--text-caption-size);
  padding: 40px 20px;
  min-height: 200px;
}

.empty-state p {
  margin: 0;
}
</style>
