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
    <div class="widget-title">
      <div class="widget-title-icon-rect">

      </div>
      <h2>Цель: {{ goalData.title }}</h2>
    </div>

    <p class="medium-text">Достижение цели: {{ progressPercentage.toFixed(1) }}%</p>

    <div>
      <div class="progress-bar">
        <div class="progress" :style="{ width: progressPercentage + '%' }"></div>
      </div>
      <div class="progress-info">
        <span>{{ goalData.currentAmount.toLocaleString('ru-RU') }} RUB</span>
        <span>{{ goalData.targetAmount.toLocaleString('ru-RU') }} RUB</span>
      </div>
    </div>

  </div>
</template>

<style scoped>
.widget {
  grid-row: span 1;
  grid-column: span 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
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
  background-color: #5478EA;
  border-radius: 5px;
  transition: width 0.5s ease;
}
.progress-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #4b5563;
}
</style>