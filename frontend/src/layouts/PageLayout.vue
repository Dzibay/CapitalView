<template>
  <div class="page-layout">
    <slot />
  </div>
</template>

<script setup>
</script>

<style scoped>
.page-layout {
  margin: 0 auto;
  width: 100%;
  padding: 0 16px;
  min-width: 0;
  max-width: min(1400px, 100%);
  overflow-x: hidden;
  box-sizing: border-box;
}

@media (max-width: 768px) {
  .page-layout {
    padding: 0 10px;
  }
}

@media (max-width: 480px) {
  .page-layout {
    padding: 0 8px;
  }
}
</style>
