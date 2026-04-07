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
const selectMinWidth = computed(() =>
  isMobileBar.value ? 'min(200px, calc(100vw - 128px))' : '200px'
)

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
