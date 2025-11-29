/**
 * Композабл для управления состоянием модальных окон
 * Устраняет дублирование логики открытия/закрытия модалок
 */
import { ref } from 'vue';

export function useModal() {
  const isOpen = ref(false);

  const open = () => {
    isOpen.value = true;
  };

  const close = () => {
    isOpen.value = false;
  };

  const toggle = () => {
    isOpen.value = !isOpen.value;
  };

  return {
    isOpen,
    open,
    close,
    toggle,
  };
}

/**
 * Композабл для управления несколькими модалками одновременно
 */
export function useModals(modalNames = []) {
  const modals = ref({});

  // Инициализация всех модалок
  modalNames.forEach(name => {
    modals.value[name] = false;
  });

  const open = (name) => {
    if (modals.value.hasOwnProperty(name)) {
      modals.value[name] = true;
    }
  };

  const close = (name) => {
    if (modals.value.hasOwnProperty(name)) {
      modals.value[name] = false;
    }
  };

  const closeAll = () => {
    Object.keys(modals.value).forEach(key => {
      modals.value[key] = false;
    });
  };

  const isOpen = (name) => {
    return modals.value[name] || false;
  };

  return {
    modals,
    open,
    close,
    closeAll,
    isOpen,
  };
}

