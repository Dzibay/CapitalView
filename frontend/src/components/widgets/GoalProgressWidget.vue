<script setup>
import { computed } from 'vue';

const props = defineProps({
  goalData: { type: Object, required: true },
});

const progressPercentage = computed(() => {
  return (props.goalData.currentAmount / props.goalData.targetAmount) * 100;
});
</script>

<template>
  <div class="widget">
    <h3 class="widget-title">Цель: {{ goalData.title }}</h3>
    <div class="progress-bar">
      <div class="progress" :style="{ width: progressPercentage + '%' }"></div>
    </div>
    <div class="progress-info">
      <span>{{ goalData.currentAmount.toLocaleString('ru-RU') }} RUB</span>
      <span>{{ goalData.targetAmount.toLocaleString('ru-RU') }} RUB</span>
    </div>
  </div>
</template>

<style scoped>
.widget {
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}
.widget-title {
  font-size: 1rem;
  color: #6b7280;
  margin: 0 0 1rem;
}
.progress-bar {
  width: 100%;
  height: 10px;
  background-color: #e5e7eb;
  border-radius: 5px;
  overflow: hidden;
}
.progress {
  height: 100%;
  background-color: #4A55A2;
  border-radius: 5px;
  transition: width 0.5s ease;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  color: #4b5563;
}
</style>