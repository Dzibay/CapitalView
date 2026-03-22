<script setup>
defineProps({
  items: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section class="section section-alt snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Знакомо?</h2>
      <p class="section-intro reveal">
        Управление инвестициями не должно отнимать часы. Но для многих инвесторов реальность выглядит
        иначе: разрозненные данные, ручные расчёты, риск ошибок. Вот три типичные проблемы, с которыми
        сталкиваются частные инвесторы.
      </p>
      <div class="pain-grid">
        <div v-for="(pain, i) in items" :key="i" class="pain-card reveal">
          <div class="pain-icon">
            <component :is="pain.icon" :size="28" :stroke-width="1.5" />
          </div>
          <h3>{{ pain.title }}</h3>
          <p>{{ pain.desc }}</p>
        </div>
      </div>
    </div>
  </section>
</template>
