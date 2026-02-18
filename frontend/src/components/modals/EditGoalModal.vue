<script setup>
import { ref, watch, defineEmits } from 'vue';
import { Check } from 'lucide-vue-next'
import { Button } from '../base'

const props = defineProps({
  show: { type: Boolean, required: true },
  targetAmount: { type: Number, default: 0 },
  monthlyContribution: { type: Number, default: 0 },
  annualReturn: { type: Number, default: 0 },
  useInflation: { type: Boolean, default: false },
  inflationRate: { type: Number, default: 7.5 },
});

const emits = defineEmits(['close', 'save']);

const newTargetAmount = ref(props.targetAmount);
const newMonthlyContribution = ref(props.monthlyContribution || 0);
// Если annualReturn не задан, оставляем пустым для placeholder
const newAnnualReturn = ref(props.annualReturn || '');
const newUseInflation = ref(props.useInflation !== undefined && props.useInflation !== null ? props.useInflation : false);
const newInflationRate = ref(props.inflationRate !== undefined && props.inflationRate !== null ? props.inflationRate : 7.5);

// Обновляем локальные значения, если пропсы меняются
watch(() => props.targetAmount, (val) => newTargetAmount.value = val);
watch(() => props.monthlyContribution, (val) => {
  newMonthlyContribution.value = val || 0
});
watch(() => props.annualReturn, (val) => {
  // Если значение не задано, оставляем пустым для placeholder
  newAnnualReturn.value = val || ''
});
watch(() => props.useInflation, (val) => {
  newUseInflation.value = val !== undefined && val !== null ? Boolean(val) : false
}, { immediate: true });
watch(() => props.inflationRate, (val) => {
  newInflationRate.value = val !== undefined && val !== null ? Number(val) : 7.5
}, { immediate: true });

function save() {
  emits('save', {
    targetAmount: Number(newTargetAmount.value),
    monthlyContribution: Number(newMonthlyContribution.value) || 0,
    annualReturn: newAnnualReturn.value ? Number(newAnnualReturn.value) : null,
    useInflation: newUseInflation.value,
    inflationRate: Number(newInflationRate.value) || 7.5
  });
}
</script>

<template>
  <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Изменить цель</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <form @submit.prevent="save" class="form-content">
        <div class="form-section">
          <label class="form-label">
            <span class="label-icon">💰</span>
            Целевой капитал (RUB)
          </label>
          <input v-model="newTargetAmount" type="number" min="0" step="0.01" class="form-input" />
        </div>

        <div class="form-section">
          <label class="form-label">
            <span class="label-icon">📈</span>
            Ежемесячные пополнения (RUB)
          </label>
          <input v-model="newMonthlyContribution" type="number" min="0" step="0.01" class="form-input" placeholder="0" />
          <p class="form-hint">Сумма, которую вы планируете добавлять каждый месяц</p>
        </div>

        <div class="form-section">
          <label class="form-label">
            <span class="label-icon">📊</span>
            Годовая доходность (%)
          </label>
          <input 
            v-model="newAnnualReturn" 
            type="number" 
            min="0" 
            max="100" 
            step="0.01" 
            class="form-input" 
            :placeholder="props.annualReturn ? props.annualReturn.toFixed(2) + '%' : 'Автоматически из портфеля'" 
          />
          <p class="form-hint">Ожидаемая годовая доходность. По умолчанию используется доходность вашего портфеля</p>
        </div>

        <div class="form-section">
          <div class="checkbox-wrapper">
            <label class="checkbox-label">
              <input 
                v-model="newUseInflation" 
                type="checkbox" 
                class="checkbox-input"
              />
              <span class="checkbox-custom"></span>
              <span class="checkbox-text">
                <span class="label-icon">📈</span>
                Учитывать инфляцию
              </span>
            </label>
            <p class="form-hint">Целевая сумма будет ежегодно увеличиваться на уровень инфляции</p>
          </div>
          
          <div v-if="newUseInflation" class="inflation-input-wrapper">
            <label class="form-label">
              <span class="label-icon">💹</span>
              Уровень инфляции (%)
            </label>
            <input 
              v-model="newInflationRate" 
              type="number" 
              min="0" 
              max="100" 
              step="0.1" 
              class="form-input" 
            />
          </div>
        </div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')">Отмена</Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            Сохранить
          </Button>
        </div>
      </form>
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
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
  padding: 16px;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: white;
  border-radius: 20px;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes slideUp {
  from {
    transform: scale(0.95) translateY(10px);
    opacity: 0;
  }
  to {
    transform: scale(1) translateY(0);
    opacity: 1;
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 20px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
  letter-spacing: -0.01em;
}

.close-btn {
  background: #f3f4f6;
  border: none;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #6b7280;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
  transform: scale(1.05);
}

.close-btn:active {
  transform: scale(0.95);
}

.close-btn svg {
  width: 16px;
  height: 16px;
}

.form-content {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.form-content::-webkit-scrollbar {
  width: 6px;
}

.form-content::-webkit-scrollbar-track {
  background: #f9fafb;
}

.form-content::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}

.form-section {
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
}

.section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 16px 0;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  font-size: 14px;
  opacity: 0.8;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.form-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
  background: #fff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}


.form-hint {
  margin: 6px 0 0 0;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.4;
}

.checkbox-wrapper {
  margin-top: 4px;
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-custom {
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  position: relative;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.checkbox-input:checked + .checkbox-custom {
  background: #3b82f6;
  border-color: #3b82f6;
}

.checkbox-input:checked + .checkbox-custom::after {
  content: '';
  position: absolute;
  left: 6px;
  top: 2px;
  width: 5px;
  height: 10px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
}

.checkbox-text {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.inflation-input-wrapper {
  margin-top: 12px;
  padding-left: 30px;
}
</style>
