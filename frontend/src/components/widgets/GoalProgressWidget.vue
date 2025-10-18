<script setup>
import { computed, ref } from 'vue'
import EditGoalModal from '../modals/EditGoalModal.vue'

const props = defineProps({
  goalData: { type: Object, required: true },
  onSaveGoal: { type: Function, required: true }
})

const showModal = ref(false)

function openModal() {
  showModal.value = true
}

function saveGoal(newGoal) {
  if (!props.goalData?.portfolioId) return

  props.onSaveGoal({
    portfolioId: props.goalData.portfolioId,
    title: newGoal.title,
    targetAmount: newGoal.targetAmount
  })
    .then(() => {
      props.goalData.title = newGoal.title
      props.goalData.targetAmount = newGoal.targetAmount
      showModal.value = false
    })
    .catch(err => console.error('Ошибка при обновлении цели:', err))
}

const hasGoal = computed(() => !!props.goalData?.title && props.goalData.title !== 'Цель не задана')

const progressPercentage = computed(() => {
  if (!hasGoal.value || !props.goalData.targetAmount) return 0
  return (props.goalData.currentAmount / props.goalData.targetAmount) * 100
})
</script>

<template>
  <div class="widget">
    <div class="widget-title">
      <h2>{{ hasGoal ? 'Цель: ' + props.goalData.title : 'Цель не задана' }}</h2>
      <button @click="openModal" class="edit-button">Изменить цель</button>
    </div>

    <template v-if="hasGoal">
      <p class="medium-text">Достижение цели: {{ progressPercentage.toFixed(1) }}%</p>
      <div class="progress-bar">
        <div class="progress" :style="{ width: progressPercentage + '%' }"></div>
      </div>
      <div class="progress-info">
        <span>{{ props.goalData.currentAmount?.toLocaleString('ru-RU') || 0 }} RUB</span>
        <span>{{ props.goalData.targetAmount?.toLocaleString('ru-RU') || 0 }} RUB</span>
      </div>
    </template>

    <EditGoalModal
      :show="showModal"
      :title="props.goalData.title"
      :targetAmount="props.goalData.targetAmount"
      @close="showModal = false"
      @save="saveGoal"
    />
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
  position: relative;
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
.edit-button {
  margin-left: auto;
  background: #5478EA;
  color: white;
  border: none;
  border-radius: 6px;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  font-size: 0.75rem;
}
</style>
