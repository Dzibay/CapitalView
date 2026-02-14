<template>
  <div class="page-layout">
    <slot />
  </div>
</template>

<script setup>
// Базовый компонент для страниц с унифицированной шириной
</script>

<style scoped>
.page-layout {
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
  padding: 0 20px;
}
</style>
