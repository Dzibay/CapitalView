<script setup>
import { computed } from 'vue'

/**
 * Универсальный контейнер для виджетов с поддержкой размеров
 * 
 * Использование:
 * <WidgetContainer :gridColumn="3" minHeight="var(--widget-height-small)">
 *   <TotalCapitalWidget :total-amount="1000" :invested-amount="800" />
 * </WidgetContainer>
 */
const props = defineProps({
  // Размеры виджета
  minHeight: {
    type: [String, Number],
    default: null
  },
  height: {
    type: [String, Number],
    default: null
  },
  gridColumn: {
    type: [String, Number],
    default: null
  },
  gridRow: {
    type: [String, Number],
    default: null
  }
})

// Вычисляемые стили для размеров
const containerStyles = computed(() => {
  const styles = {}
  
  if (props.minHeight) {
    styles.minHeight = typeof props.minHeight === 'number' 
      ? `${props.minHeight}px` 
      : props.minHeight
  }
  
  if (props.height) {
    styles.height = typeof props.height === 'number' 
      ? `${props.height}px` 
      : props.height
  }
  
  if (props.gridColumn) {
    styles.gridColumn = typeof props.gridColumn === 'number'
      ? `span ${props.gridColumn}`
      : props.gridColumn
  }
  
  if (props.gridRow) {
    styles.gridRow = typeof props.gridRow === 'number'
      ? `span ${props.gridRow}`
      : props.gridRow
  }
  
  return styles
})
</script>

<template>
  <div class="widget-container" :style="containerStyles">
    <slot />
  </div>
</template>

<style scoped>
.widget-container {
  width: 100%;
  min-width: 0; /* Позволяет контейнеру правильно сжиматься в grid */
  display: flex;
  flex-direction: column;
  height: 100%;
}

/* Виджеты внутри контейнера должны растягиваться на всю высоту */
.widget-container > :deep(.widget),
.widget-container > :deep(div[class*="widget"]) {
  height: 100%;
  flex: 1;
}
</style>
