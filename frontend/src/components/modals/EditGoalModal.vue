<script setup>
import { ref, watch, defineEmits } from 'vue';
import { Check, Target, DollarSign, TrendingUp, BarChart3, Percent } from 'lucide-vue-next'
import { Button, ToggleSwitch } from '../base'
import ModalBase from './ModalBase.vue'

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
const error = ref('');

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
  error.value = '';
  
  // Валидация
  if (!newTargetAmount.value || newTargetAmount.value <= 0) {
    error.value = 'Введите целевой капитал'
    return
  }
  
  if (newMonthlyContribution.value < 0) {
    error.value = 'Ежемесячные пополнения не могут быть отрицательными'
    return
  }
  
  if (newAnnualReturn.value !== '' && (newAnnualReturn.value < 0 || newAnnualReturn.value > 100)) {
    error.value = 'Годовая доходность должна быть от 0 до 100%'
    return
  }
  
  if (newUseInflation.value && (newInflationRate.value < 0 || newInflationRate.value > 100)) {
    error.value = 'Уровень инфляции должен быть от 0 до 100%'
    return
  }
  
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
  <ModalBase :show="show" title="Изменить цель" :icon="Target" @close="$emit('close')">
    <form @submit.prevent="save">
      <div class="form-section">
        <label class="form-label">
          <DollarSign :size="16" class="label-icon" />
          Целевой капитал (RUB)
        </label>
        <input 
          v-model.number="newTargetAmount" 
          type="number" 
          min="0" 
          step="0.01" 
          class="form-input" 
          required
        />
      </div>

      <div class="form-section">
        <label class="form-label">
          <TrendingUp :size="16" class="label-icon" />
          Ежемесячные пополнения (RUB)
        </label>
        <input 
          v-model.number="newMonthlyContribution" 
          type="number" 
          min="0" 
          step="0.01" 
          class="form-input" 
          placeholder="0" 
        />
        <small class="form-hint">Сумма, которую вы планируете добавлять каждый месяц</small>
      </div>

      <div class="form-section">
        <label class="form-label">
          <BarChart3 :size="16" class="label-icon" />
          Годовая доходность (%)
        </label>
        <input 
          v-model.number="newAnnualReturn" 
          type="number" 
          min="0" 
          max="100" 
          step="0.01" 
          class="form-input" 
          :placeholder="props.annualReturn ? props.annualReturn.toFixed(2) + '%' : 'Автоматически из портфеля'" 
        />
        <small class="form-hint">Ожидаемая годовая доходность. По умолчанию используется доходность вашего портфеля</small>
      </div>

      <div class="form-section">
        <div class="toggle-wrapper">
          <ToggleSwitch v-model="newUseInflation" />
          <span class="toggle-label-text">
            Учитывать инфляцию
          </span>
        </div>
        <small class="form-hint">Целевая сумма будет ежегодно увеличиваться на уровень инфляции</small>
        
        <div v-if="newUseInflation" class="inflation-input-wrapper">
          <label class="form-label">
            <Percent :size="16" class="label-icon" />
            Уровень инфляции (%)
          </label>
          <input 
            v-model.number="newInflationRate" 
            type="number" 
            min="0" 
            max="100" 
            step="0.1" 
            class="form-input" 
          />
        </div>
      </div>

      <div v-if="error" class="error">{{ error }}</div>

      <div class="form-actions">
        <Button variant="secondary" type="button" @click="$emit('close')">Отмена</Button>
        <Button variant="primary" type="submit">
          <template #icon>
            <Check :size="16" />
          </template>
          Сохранить
        </Button>
      </div>
    </form>
  </ModalBase>
</template>

<style scoped>
.form-section {
  margin-bottom: 20px;
}

.form-section:last-of-type {
  margin-bottom: 16px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--lx-ink, #374151);
  letter-spacing: -0.01em;
}

.label-icon {
  color: var(--lx-ink-2, #6b7280);
  flex-shrink: 0;
}

.form-input {
  width: 100%;
  padding: 9px 12px;
  border: 1.5px solid var(--lx-line, #e5e7eb);
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: var(--lx-surface, #fff);
  color: var(--lx-ink, #111827);
  box-sizing: border-box;
  font-family: inherit;
}

.form-input::placeholder {
  color: var(--lx-mut, #9ca3af);
}

.form-input:hover {
  border-color: var(--lx-line, #d1d5db);
  background: var(--lx-surface, #fafafa);
}

.form-input:focus {
  outline: none;
  border-color: var(--lx-accent, #3b82f6);
  box-shadow: 0 0 0 3px var(--lx-accent-soft, rgba(59,130,246,0.1));
  background: var(--lx-surface, #fff);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--lx-line, #f3f4f6);
}

.form-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--lx-ink-2, #6b7280);
  line-height: 1.4;
}

.toggle-wrapper {
  margin-bottom: 12px;
  padding: 8px 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.toggle-label-text {
  font-size: 13px;
  color: var(--lx-ink, #374151);
  font-weight: 500;
}

.inflation-input-wrapper {
  margin-top: 12px;
  padding-left: 0;
}

.error {
  padding: 10px 14px;
  background: var(--lx-surface, #fef2f2);
  border: 1px solid var(--lx-line, #fecaca);
  border-radius: 10px;
  color: var(--lx-down, #dc2626);
  font-size: 13px;
  margin-bottom: 12px;
}
</style>
