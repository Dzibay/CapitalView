<script setup>
import { ref } from 'vue';
import { Line } from 'vue-chartjs';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

defineProps({
  chartData: { type: Object, required: true },
});

const selectedPeriod = ref('6M');

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
  },
  scales: {
    y: { beginAtZero: false },
  },
};
</script>

<template>
  <div class="widget">
    <div class="widget-header">
      <h3 class="widget-title">Динамика капитала</h3>
      <div class="time-filters">
        <button :class="{ active: selectedPeriod === '1M' }" @click="selectedPeriod = '1M'">1М</button>
        <button :class="{ active: selectedPeriod === '6M' }" @click="selectedPeriod = '6M'">6М</button>
        <button :class="{ active: selectedPeriod === '1Y' }" @click="selectedPeriod = '1Y'">1Г</button>
        <button :class="{ active: selectedPeriod === 'All' }" @click="selectedPeriod = 'All'">Все</button>
      </div>
    </div>
    <div class="chart-container">
      <Line :data="chartData" :options="chartOptions" />
    </div>
  </div>
</template>

<style scoped>
.widget {
  grid-column: span 2;
  background-color: #fff;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.widget-title {
  font-size: 1.25rem;
  color: #1f2937;
  margin: 0;
}
.time-filters button {
  background-color: #f3f4f6;
  border: none;
  border-radius: 6px;
  padding: 0.5rem 1rem;
  margin-left: 0.5rem;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}
.time-filters button:hover {
  background-color: #e5e7eb;
}
.time-filters button.active {
  background-color: #4A55A2;
  color: #fff;
}
.chart-container {
  height: 300px;
}
</style>