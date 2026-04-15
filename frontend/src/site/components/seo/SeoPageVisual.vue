<script setup>
defineProps({
  placeholder: {
    type: String,
    required: true,
  },
  caption: {
    type: String,
    required: true,
  },
})
</script>

<template>
  <figure class="seo-visual">
    <div class="seo-visual__placeholder">{{ placeholder }}</div>
    <figcaption>{{ caption }}</figcaption>
  </figure>
</template>
