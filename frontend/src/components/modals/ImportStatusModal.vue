<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { X } from 'lucide-vue-next'
import { Button } from '../base'
import taskService from '../../services/taskService'
import { useImportTasksStore } from '../../stores/importTasks.store'

const props = defineProps({
  taskId: {
    type: Number,
    required: true
  },
  onComplete: Function,
  onError: Function
})

const emit = defineEmits(['close'])

const importTasksStore = useImportTasksStore()

const status = ref('pending')
const progress = ref(0)
const progressMessage = ref('')
const errorMessage = ref(null)
const result = ref(null)
const completedAt = ref(null)

let pollInterval = null
const POLL_INTERVAL = 2000 // 2 секунды

// Функция для проверки статуса задачи
const checkStatus = async () => {
  try {
    const response = await taskService.getTaskStatus(props.taskId)
    if (response.success) {
      status.value = response.status
      progress.value = response.progress || 0
      progressMessage.value = response.progress_message || ''
      errorMessage.value = response.error_message
      result.value = response.result
      completedAt.value = response.completed_at

      // Если задача завершена, останавливаем polling
      if (response.status === 'completed') {
        stopPolling()
        // Удаляем задачу из активных через небольшую задержку
        setTimeout(() => {
          importTasksStore.removeTask(props.taskId)
        }, 3000)
        if (props.onComplete) {
          props.onComplete(response.result)
        }
      } else if (response.status === 'failed') {
        stopPolling()
        // Удаляем задачу из активных через небольшую задержку
        setTimeout(() => {
          importTasksStore.removeTask(props.taskId)
        }, 5000)
        if (props.onError) {
          props.onError(response.error_message)
        }
      } else if (response.status === 'cancelled') {
        stopPolling()
        importTasksStore.removeTask(props.taskId)
        // Задача отменена - просто закрываем модалку
        setTimeout(() => {
          emit('close')
        }, 1000)
      }
    }
  } catch (error) {
    console.error('Ошибка при проверке статуса задачи:', error)
    // Не останавливаем polling при ошибке сети, продолжаем попытки
    // Но если задача не найдена (404), останавливаем
    if (error.response?.status === 404) {
      stopPolling()
      errorMessage.value = 'Задача не найдена'
      status.value = 'failed'
    }
  }
}

// Запуск polling
const startPolling = () => {
  // Первая проверка сразу
  checkStatus()
  
  // Затем каждые POLL_INTERVAL миллисекунд
  pollInterval = setInterval(checkStatus, POLL_INTERVAL)
}

// Остановка polling
const stopPolling = () => {
  if (pollInterval) {
    clearInterval(pollInterval)
    pollInterval = null
  }
}

// Отмена задачи
const cancelTask = async () => {
  try {
    await taskService.cancelTask(props.taskId)
    stopPolling()
    status.value = 'cancelled'
    // Закрываем модалку через небольшую задержку
    setTimeout(() => {
      emit('close')
    }, 1000)
  } catch (error) {
    console.error('Ошибка при отмене задачи:', error)
  }
}

// Обработка клика на overlay
const handleOverlayClick = () => {
  // Разрешаем закрытие в любое время (модалку можно открыть снова)
  emit('close')
}

// Обработка закрытия модалки
const handleClose = () => {
  // Закрываем модалку, но задача остается активной
  importTasksStore.closeModal(props.taskId)
  emit('close')
}

// При монтировании отмечаем модалку как открытую
onMounted(() => {
  importTasksStore.openModal(props.taskId)
  if (props.taskId) {
    startPolling()
  }
})

// При размонтировании закрываем модалку в store
onUnmounted(() => {
  importTasksStore.closeModal(props.taskId)
  stopPolling()
})

// Отслеживаем изменения taskId
watch(() => props.taskId, (newId) => {
  if (newId) {
    stopPolling()
    importTasksStore.openModal(newId)
    startPolling()
  }
})

// Иконки для статусов
const statusIcon = {
  pending: '⏳',
  processing: '🔄',
  completed: '✅',
  failed: '❌',
  cancelled: '🚫'
}

const statusText = {
  pending: 'Ожидание',
  processing: 'Выполняется',
  completed: 'Завершено',
  failed: 'Ошибка',
  cancelled: 'Отменено'
}

const statusColor = {
  pending: '#6b7280',
  processing: '#3b82f6',
  completed: '#10b981',
  failed: '#ef4444',
  cancelled: '#9ca3af'
}
</script>

<template>
  <div class="modal-overlay" @click.self="handleOverlayClick">
    <div class="modal-content status-modal">
      <div class="modal-header">
        <h2>Импорт портфеля</h2>
        <button 
          v-if="status === 'pending' || status === 'processing'"
          class="close-btn" 
          @click="cancelTask" 
          aria-label="Отменить"
          title="Отменить импорт"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        <button 
          v-else
          class="close-btn" 
          @click="handleClose" 
          aria-label="Закрыть"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>

      <div class="status-content">
        <!-- Статус -->
        <div class="status-info">
          <div class="status-badge" :style="{ color: statusColor[status] }">
            <span class="status-icon">{{ statusIcon[status] }}</span>
            <span class="status-text">{{ statusText[status] }}</span>
          </div>
        </div>

        <!-- Прогресс-бар -->
        <div v-if="status === 'processing' || status === 'pending'" class="progress-section">
          <div class="progress-bar-container">
            <div 
              class="progress-bar" 
              :style="{ width: `${progress}%`, backgroundColor: statusColor[status] }"
            ></div>
          </div>
          <div class="progress-text">
            <span class="progress-percent">{{ progress }}%</span>
            <span v-if="progressMessage" class="progress-message">{{ progressMessage }}</span>
          </div>
          <!-- Динамический спиннер загрузки -->
          <div class="loading-spinner-wrapper">
            <div class="loader"></div>
          </div>
        </div>

        

        <!-- Ошибка -->
        <div v-if="errorMessage" class="error-box">
          <span class="error-icon">⚠️</span>
          <span>{{ errorMessage }}</span>
        </div>

        <!-- Результат -->
        <div v-if="result && status === 'completed'" class="result-box">
          <div class="result-header">
            <span class="result-icon">✅</span>
            <span class="result-title">Импорт завершен успешно</span>
          </div>
          <div v-if="result.portfolio_id" class="result-info">
            <span>Портфель ID: {{ result.portfolio_id }}</span>
          </div>
        </div>

        <!-- Время завершения -->
        <div v-if="completedAt" class="completed-time">
          Завершено: {{ new Date(completedAt).toLocaleString('ru-RU') }}
        </div>
      </div>

      <div class="modal-actions">
        <Button 
          v-if="status === 'pending' || status === 'processing'"
          variant="secondary" 
          @click="cancelTask"
        >
          Отменить
        </Button>
        <Button 
          v-else
          variant="primary" 
          @click="handleClose"
        >
          Закрыть
        </Button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-modal {
  max-width: 500px;
}

.status-content {
  padding: 24px;
  min-height: 200px;
}

.status-info {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.status-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  background: #f9fafb;
  border-radius: 12px;
  font-weight: 600;
  font-size: 15px;
}

.status-icon {
  font-size: 18px;
}

.progress-section {
  margin-bottom: 20px;
}

.progress-bar-container {
  width: 100%;
  height: 8px;
  background: #e5e7eb;
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: #3b82f6;
  border-radius: 4px;
  transition: width 0.3s ease;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.8;
  }
}

.progress-text {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #6b7280;
}

.progress-percent {
  font-weight: 600;
  color: #374151;
}

.progress-message {
  flex: 1;
  text-align: right;
  margin-left: 12px;
}

.loading-spinner-wrapper {
  display: flex;
  justify-content: center;
  align-items: center;
  margin-top: 20px;
  padding: 20px;
}

.loader {
  width: 40px;
  height: 40px;
  border: 4px solid #e5e7eb;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.message-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 10px;
  color: #1e40af;
  font-size: 13px;
  margin-bottom: 16px;
}

.message-icon {
  font-size: 16px;
}

.error-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 10px;
  color: #dc2626;
  font-size: 13px;
  margin-bottom: 16px;
}

.error-icon {
  font-size: 16px;
}

.result-box {
  padding: 16px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  margin-bottom: 16px;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-weight: 600;
  color: #059669;
  font-size: 14px;
}

.result-icon {
  font-size: 18px;
}

.result-info {
  font-size: 13px;
  color: #047857;
  margin-left: 26px;
}

.completed-time {
  text-align: center;
  font-size: 12px;
  color: #9ca3af;
  margin-top: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.btn {
  padding: 10px 18px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  border: none;
  display: flex;
  align-items: center;
  gap: 6px;
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
}

.close-btn:hover {
  background: #fee2e2;
  color: #dc2626;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(8px);
  padding: 16px;
}

.modal-content {
  background: white;
  width: 100%;
  max-width: 500px;
  border-radius: 20px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid #f3f4f6;
}

.modal-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #111827;
}
</style>
