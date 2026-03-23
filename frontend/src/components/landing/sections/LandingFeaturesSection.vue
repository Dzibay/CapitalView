<script setup>
defineProps({
  items: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section id="features" class="section snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Всё, что нужно инвестору</h2>
      <p class="section-subheading reveal">
        Три инструмента, которые заменят десяток таблиц и приложений. CapitalView объединяет учёт
        сделок, аналитику доходности и календарь выплат в единую платформу с автоматической
        синхронизацией данных.
      </p>
      <div class="features-grid">
        <div v-for="(feat, i) in items" :key="i" class="feature-card reveal">
          <div class="feature-icon">
            <component :is="feat.icon" :size="28" :stroke-width="1.5" />
          </div>
          <h3>{{ feat.title }}</h3>
          <p>{{ feat.desc }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
