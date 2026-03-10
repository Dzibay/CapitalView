<template>
  <ModalBase title="Добавить портфель" :icon="FolderPlus" @close="$emit('close')">
    <div v-if="saving" class="modal-loading">
      <Loader2 :size="32" class="spinner-icon" />
      <span>Сохраняем...</span>
    </div>

    <form v-else @submit.prevent="submitForm">
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
  </ModalBase>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { Check, FolderPlus, FileText, AlignLeft, Loader2 } from 'lucide-vue-next'
import { Button } from '../base'
import CustomSelect from '../base/CustomSelect.vue'
import FormInput from '../base/FormInput.vue'
import ModalBase from './ModalBase.vue'

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
  color: #374151;
  letter-spacing: -0.01em;
}

.label-icon {
  color: #6b7280;
  flex-shrink: 0;
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
