import { defineStore } from 'pinia'

export const useImportTasksStore = defineStore('importTasks', {
  state: () => ({
    // Активные задачи импорта: Map<taskId, { portfolioId, portfolioName, createdAt }>
    activeTasks: new Map(),
    // Открытые модалки: Set<taskId>
    openModals: new Set()
  }),

  actions: {
    /**
     * Добавляет задачу импорта
     */
    addTask(taskId, portfolioId = null, portfolioName = null) {
      this.activeTasks.set(taskId, {
        portfolioId,
        portfolioName,
        createdAt: new Date().toISOString()
      })
    },

    /**
     * Удаляет задачу импорта
     */
    removeTask(taskId) {
      this.activeTasks.delete(taskId)
      this.openModals.delete(taskId)
    },

    /**
     * Открывает модалку для задачи
     */
    openModal(taskId) {
      this.openModals.add(taskId)
    },

    /**
     * Закрывает модалку для задачи (но задача остается активной)
     */
    closeModal(taskId) {
      this.openModals.delete(taskId)
    },

    /**
     * Проверяет, открыта ли модалка для задачи
     */
    isModalOpen(taskId) {
      return this.openModals.has(taskId)
    },

    /**
     * Получает все активные задачи
     */
    getActiveTasks() {
      return Array.from(this.activeTasks.keys())
    },

    /**
     * Получает информацию о задаче
     */
    getTaskInfo(taskId) {
      return this.activeTasks.get(taskId)
    }
  }
})
