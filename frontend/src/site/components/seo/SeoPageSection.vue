<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  /** Якорь для оглавления (например overview-start). */
  sectionId: {
    type: String,
    default: '',
  },
})
</script>

<template>
  <section class="seo-section" :id="sectionId || undefined">
    <h2>{{ title }}</h2>
    <slot />
  </section>
</template>
