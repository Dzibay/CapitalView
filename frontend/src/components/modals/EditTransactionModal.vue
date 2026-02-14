<script setup>
import { ref, watch } from 'vue'
import { Check } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'

const props = defineProps({
  transaction: Object,
  visible: Boolean
})

const emit = defineEmits(['close', 'save'])

const editedTx = ref({ ...props.transaction })

watch(
  () => props.transaction,
  newTx => {
    editedTx.value = { ...newTx }
  }
)

const handleSave = () => {
  emit('save', editedTx.value)
  emit('close')
}
</script>

<template>
  <div v-if="visible" class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>Редактировать транзакцию</h2>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      
      <form @submit.prevent="handleSave" class="form-content">
        <div class="form-section">
          <div class="asset-info">
            <span class="asset-icon">📈</span>
            <div>
              <strong>{{ editedTx.asset_name }}</strong>
            </div>
          </div>
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <label class="form-label">
            <span class="label-icon">🔄</span>
            Тип
          </label>
          <CustomSelect
            v-model="editedTx.transaction_type"
            :options="[
              { value: 'Покупка', label: 'Покупка' },
              { value: 'Продажа', label: 'Продажа' }
            ]"
            placeholder="Выберите тип"
            :show-empty-option="false"
            option-label="label"
            option-value="value"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <div class="form-section">
          <div class="section-divider"></div>
          <div class="form-row">
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">🔢</span>
                Количество
              </label>
              <input type="number" v-model.number="editedTx.quantity" step="0.0001" class="form-input" />
            </div>
            <div class="form-field">
              <label class="form-label">
                <span class="label-icon">💰</span>
                Цена
              </label>
              <input type="number" v-model.number="editedTx.price" step="0.01" class="form-input" />
            </div>
          </div>
          <div class="form-field">
            <label class="form-label">
              <span class="label-icon">📅</span>
              Дата
            </label>
            <input type="date" v-model="editedTx.transaction_date" class="form-input" />
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
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
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

.asset-info {
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 10px;
  border: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 14px;
}

.asset-icon {
  font-size: 18px;
  opacity: 0.8;
}

.asset-info strong {
  color: #111827;
  font-weight: 600;
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

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid #f3f4f6;
}

</style>
