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
  color: #6b7280;
  font-size: 14px;
  padding: 40px 20px;
  min-height: 200px;
}

.empty-state p {
  margin: 0;
}
</style>
