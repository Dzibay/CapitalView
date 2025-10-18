<script setup>
import { ref, watch, defineEmits, defineProps } from 'vue';

const props = defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: '' },
  targetAmount: { type: Number, default: 0 },
});

const emits = defineEmits(['close', 'save']);

const newTitle = ref(props.title);
const newTargetAmount = ref(props.targetAmount);

// Обновляем локальные значения, если пропсы меняются
watch(() => props.title, (val) => newTitle.value = val);
watch(() => props.targetAmount, (val) => newTargetAmount.value = val);

function save() {
  emits('save', {
    title: newTitle.value,
    targetAmount: Number(newTargetAmount.value)
  });
}
</script>

<template>
  <div v-if="show" class="modal-overlay">
    <div class="modal">
      <h3>Изменить цель</h3>
      <label>
        Название цели:
        <input v-model="newTitle" type="text" />
      </label>
      <label>
        Сумма цели (RUB):
        <input v-model="newTargetAmount" type="number" min="0" />
      </label>
      <div class="modal-buttons">
        <button @click="save">Сохранить</button>
        <button @click="$emit('close')">Отмена</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0,0,0,0.4);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}
.modal {
  background: #fff;
  padding: 1.5rem;
  border-radius: 12px;
  min-width: 300px;
  max-width: 90%;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}
.modal input {
  width: 100%;
  padding: 0.25rem 0.5rem;
  border: 1px solid #ccc;
  border-radius: 6px;
}
.modal-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
}
.modal-buttons button {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  border: none;
  cursor: pointer;
}
.modal-buttons button:first-child {
  background-color: #5478EA;
  color: white;
}
.modal-buttons button:last-child {
  background-color: #e5e7eb;
}
</style>
