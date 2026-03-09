<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal-content">
      <div class="modal-header">
        <div class="header-content">
          <div class="header-icon-wrapper">
            <FolderPlus :size="20" />
          </div>
          <h2>Добавить портфель</h2>
        </div>
        <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
          <X :size="16" />
        </button>
      </div>

      <div v-if="saving" class="modal-loading">
        <Loader2 :size="32" class="spinner-icon" />
        <span>Сохраняем...</span>
      </div>

      <form v-else @submit.prevent="submitForm" class="form-content">
        <div class="form-section">
          <CustomSelect
            v-model="form.parent_portfolio_id"
            :options="portfolios"
            label="Родительский портфель"
            placeholder="Выберите портфель"
            :show-empty-option="false"
            option-label="name"
            option-value="id"
            :min-width="'100%'"
            :flex="'none'"
          />
        </div>

        <div class="form-section">
          <FormInput
            v-model="form.name"
            label="Название"
            :icon="FileText"
            type="text"
            placeholder="Введите название портфеля"
            required
          />
        </div>

        <div class="form-section">
          <label class="form-label">
            <AlignLeft :size="16" class="label-icon" />
            Описание
          </label>
          <textarea v-model="form.description" class="form-input textarea" placeholder="Введите описание портфеля (необязательно)"></textarea>
        </div>

        <div class="form-actions">
          <Button variant="secondary" type="button" @click="$emit('close')">Отмена</Button>
          <Button variant="primary" type="submit" :loading="saving">
            <template #icon>
              <Check :size="16" />
            </template>
            Добавить портфель
          </Button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { Check, X, FolderPlus, FileText, AlignLeft, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'

const props = defineProps({
  portfolios: Array, // список портфелей для выбора родителя
  onSave: Function   // функция сохранения портфеля из родителя
})

const emit = defineEmits(['close'])

const form = reactive({
  parent_portfolio_id: null,
  name: '',
  description: ''
})

const saving = ref(false)

// Устанавливаем первый портфель по умолчанию
watch(() => props.portfolios, (newPortfolios) => {
  if (newPortfolios && newPortfolios.length > 0 && !form.parent_portfolio_id) {
    form.parent_portfolio_id = newPortfolios[0].id
  }
}, { immediate: true })

const submitForm = async () => {
  if (!props.onSave) return
  saving.value = true
  try {
    await props.onSave({ ...form }) // ждём промис от родителя
    emit('close')
  } catch (err) {
    console.error(err)
    alert('Ошибка при сохранении портфеля')
  } finally {
    saving.value = false
  }
}
</script>

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

.modal-content {
  background: white;
  width: 100%;
  max-width: 480px;
  max-height: 90vh;
  border-radius: 20px;
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
  padding: 20px 24px;
  border-bottom: 1px solid #f3f4f6;
  background: #fff;
  flex-shrink: 0;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #3b82f6;
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


.form-content {
  padding: 24px;
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
  margin-bottom: 24px;
}

.form-section:last-of-type {
  margin-bottom: 20px;
}

.form-label {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.form-input {
  width: 100%;
  padding: 11px 14px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
}

.form-input::placeholder {
  color: #9ca3af;
}

.form-input.textarea {
  min-height: 100px;
  resize: vertical;
  line-height: 1.5;
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

.modal-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
  font-weight: 500;
  font-size: 14px;
  color: #6b7280;
}

.spinner-icon {
  color: #3b82f6;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
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
