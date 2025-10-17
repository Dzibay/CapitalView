<template>
  <div class="modal-overlay">
    <div class="modal-content">
      <h2>Добавить портфель</h2>

      <div v-if="saving" class="modal-loading">Сохраняем...</div>

      <form v-else @submit.prevent="submitForm">
        <div>
          <label>Родительский портфель:</label>
          <select v-model="form.parent_portfolio_id">
            <option :value="null">— Нет —</option>
            <option v-for="p in portfolios" :key="p.id" :value="p.id">
              {{ p.name }} 
            </option>
          </select>
        </div>

        <div>
          <label>Название:</label>
          <input v-model="form.name" type="text" required />
        </div>

        <div>
          <label>Описание:</label>
          <textarea v-model="form.description"></textarea>
        </div>

        <div class="buttons">
          <button type="submit">Добавить</button>
          <button type="button" @click="$emit('close')">Закрыть</button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'

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
}
.modal-content {
  background: white;
  padding: 20px;
  width: 420px;
  border-radius: 8px;
  position: relative;
}
.modal-content form div {
  margin-bottom: 10px;
}
.buttons {
  display: flex;
  justify-content: space-between;
  margin-top: 15px;
}
.modal-loading {
  text-align: center;
  padding: 40px 0;
  font-weight: bold;
  font-size: 16px;
}
</style>
