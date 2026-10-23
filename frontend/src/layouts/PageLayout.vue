<template>
  <div class="page-layout">
    <slot />
  </div>
</template>

<script setup>
</script>

<style scoped>
/* поля и максимальную ширину задаёт оболочка кабинета */
.page-layout {
  width: 100%;
  min-width: 0;
  padding-bottom: 8px;
  box-sizing: border-box;
  --spacing: var(--cv-gap, 18px);
}
@media (max-width: 768px) {
  .page-layout { --spacing: 12px; }
}
</style>
