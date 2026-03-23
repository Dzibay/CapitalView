<script setup>
defineProps({
  items: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section id="how-it-works" class="section snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Три шага к полному контролю</h2>
      <p class="section-subheading reveal">
        Никаких сложных настроек. Подключите брокера, дождитесь синхронизации и начните анализировать.
        Вся настройка занимает не более 2 минут.
      </p>
      <div class="steps-grid">
        <div v-for="(step, i) in items" :key="i" class="step-card reveal">
          <div class="step-number">{{ step.number }}</div>
          <h3>{{ step.title }}</h3>
          <p>{{ step.desc }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
