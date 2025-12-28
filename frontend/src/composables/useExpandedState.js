/**
 * Композабл для управления состоянием раскрытых элементов (портфели, меню и т.д.)
 * Использует localStorage для сохранения состояния
 */
import { ref, watch, onMounted } from 'vue';

export function useExpandedState(storageKey, defaultValue = []) {
  const expanded = ref([]);

  // Загружаем из localStorage при монтировании
  onMounted(() => {
    const saved = localStorage.getItem(storageKey);
    if (saved) {
      try {
        expanded.value = JSON.parse(saved);
      } catch (e) {
        console.error(`Error parsing ${storageKey} from localStorage:`, e);
        expanded.value = defaultValue;
      }
    } else {
      expanded.value = defaultValue;
    }
  });

  // Автоматически сохраняем при изменении
  watch(expanded, (val) => {
    localStorage.setItem(storageKey, JSON.stringify(val));
  }, { deep: true });

  const toggle = (id) => {
    if (expanded.value.includes(id)) {
      expanded.value = expanded.value.filter(i => i !== id);
    } else {
      expanded.value.push(id);
    }
  };

  const isExpanded = (id) => {
    return expanded.value.includes(id);
  };

  const expand = (id) => {
    if (!expanded.value.includes(id)) {
      expanded.value.push(id);
    }
  };

  const collapse = (id) => {
    expanded.value = expanded.value.filter(i => i !== id);
  };

  const expandAll = () => {
    // Можно расширить для работы с массивом ID
  };

  const collapseAll = () => {
    expanded.value = [];
  };

  return {
    expanded,
    toggle,
    isExpanded,
    expand,
    collapse,
    expandAll,
    collapseAll,
  };
}




