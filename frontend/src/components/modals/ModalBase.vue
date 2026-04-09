<script setup>
import { X } from 'lucide-vue-next'

const props = defineProps({
  title: { type: String, required: true },
  icon: { type: [Object, Function], default: null },
  show: { type: Boolean, default: true },
  wide: { type: Boolean, default: false } // Для модалок, которым нужна большая ширина
})

const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="show" class="modal-backdrop" @click.self="$emit('close')">
    <div class="modal" :class="{ wide: wide }">
      <div class="modal-header">
        <div class="header-content">
          <div v-if="icon" class="header-icon-wrapper">
            <component :is="icon" :size="20" />
          </div>
          <h2>{{ title }}</h2>
        </div>
        <slot name="close-button">
          <button class="close-btn" @click="$emit('close')" aria-label="Закрыть">
            <X :size="16" />
          </button>
        </slot>
      </div>

      <div class="form-content">
        <slot />
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-backdrop {
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

@media (max-width: 768px) {
  .modal-backdrop {
    padding-bottom: calc(
      var(--bottomNavHeight, 76px) + env(safe-area-inset-bottom, 0px) + 12px
    );
  }
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
  max-height: 85vh;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
}

/* Переопределение max-width для модалок, которым нужна большая ширина */
.modal.wide {
  max-width: 600px;
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
  padding: 20px;
  overflow-y: auto;
  overflow-x: visible;
  flex: 1;
  position: relative;
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
</style>
