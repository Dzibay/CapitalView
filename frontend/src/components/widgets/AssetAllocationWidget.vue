<script setup>
import { Doughnut } from 'vue-chartjs';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

defineProps({
  assetsData: { type: Object, required: true },
});

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'bottom',
    },
  },
};
</script>

<template>
  <div class="widget">
    <h3 class="widget-title">Распределение активов</h3>
    <div class="chart-container">
      <Doughnut :data="assetsData" :options="chartOptions" />
    </div>
  </div>
</template>

<style scoped>
.widget {
  grid-row: span 2;
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  display: flex;
  flex-direction: column;
}
.widget-title {
  font-size: 1rem;
  color: #6b7280;
  margin: 0 0 1rem;
}
.chart-container {
  position: relative;
  height: 200px;
  flex-grow: 1;
}
</style>