<script setup>
import CustomSelect from './base/CustomSelect.vue'

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

const handleChange = (value) => {
  emit('update:modelValue', value ? Number(value) : null)
}
</script>

<template>
  <CustomSelect
    :modelValue="modelValue"
    :options="portfolios"
    :option-label="'name'"
    :option-value="'id'"
    placeholder="Выберите портфель"
    :show-empty-option="false"
    :min-width="'200px'"
    :flex="'none'"
    @update:modelValue="handleChange"
  />
</template>