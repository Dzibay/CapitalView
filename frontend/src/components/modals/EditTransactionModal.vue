<script setup>
import { ref, watch } from 'vue'

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
  <div v-if="visible" class="modal-overlay">
    <div class="modal">
      <h2>Редактировать транзакцию</h2>
      
      <label>
        Актив: {{ editedTx.asset_name }}
      </label>

      <label>
        Тип:
        <select v-model="editedTx.transaction_type">
          <option value="Покупка">Покупка</option>
          <option value="Продажа">Продажа</option>
        </select>
      </label>

      <label>
        Количество:
        <input type="number" v-model.number="editedTx.quantity" />
      </label>

      <label>
        Цена:
        <input type="number" v-model.number="editedTx.price" />
      </label>
      
      <label>
        Дата:
        <input type="date" v-model="editedTx.transaction_date" />
      </label>

      <div class="modal-actions">
        <button @click="handleSave">Сохранить</button>
        <button @click="$emit('close')">Отмена</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal {
  background: white;
  padding: 20px;
  border-radius: 12px;
  width: 400px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.2);
}
.modal label {
  display: flex;
  flex-direction: column;
  margin-bottom: 10px;
}
.modal-actions {
  display: flex;
  justify-content: space-between;
}
</style>
