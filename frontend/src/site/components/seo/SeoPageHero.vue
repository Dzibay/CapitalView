<script setup>
import { computed } from 'vue'

const props = defineProps({
  eyebrow: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    required: true,
  },
  lead: {
    type: String,
    default: '',
  },
})

/** HTML-атрибуты не превращают `\n` в перевод строки — только реальные LF или такая подстановка. */
const leadDisplay = computed(() => {
  if (!props.lead) return ''
  return props.lead.replace(/\\n/g, '\n')
})
</script>

<template>
  <header class="seo-hero">
    <div class="seo-hero__content">
      <p v-if="eyebrow" class="seo-hero__eyebrow">{{ eyebrow }}</p>
      <h1>{{ title }}</h1>
      <p v-if="leadDisplay" class="seo-hero__lead">{{ leadDisplay }}</p>
    </div>
  </header>
</template>
