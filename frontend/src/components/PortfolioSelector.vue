<script setup>
import { computed } from 'vue'
import CustomSelect from './base/CustomSelect.vue'
import { useMediaMaxWidth } from '../composables/useMediaMaxWidth'

defineProps({
  portfolios: {
    type: Array,
    required: true,
    default: () => []
  },
  modelValue: {
    type: [String, Number],
    default: null
  }
})

const emit = defineEmits(['update:modelValue'])

const isMobileBar = useMediaMaxWidth(768)
const isNarrowMobile = useMediaMaxWidth(480)
/** Ширина совпадает с фиксированной колонкой `.header-mobile-end` в AppHeader */
const selectMinWidth = computed(() => {
  if (!isMobileBar.value) return '200px'
  return isNarrowMobile.value ? '124px' : '148px'
})

const handleChange = (value) => {
  emit('update:modelValue', value ? Number(value) : null)
}
</script>

<template>
  <Teleport to="#app-header-mobile-end" :disabled="!isMobileBar">
    <CustomSelect
      :modelValue="modelValue"
      :options="portfolios"
      :option-label="'name'"
      :option-value="'id'"
      placeholder="Выберите портфель"
      :show-empty-option="false"
      :min-width="selectMinWidth"
      :flex="'none'"
      :compact="isMobileBar"
      @update:modelValue="handleChange"
    />
  </Teleport>
</template>
