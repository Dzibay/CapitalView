<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  text: {
    type: String,
    required: true,
  },
  primaryTo: {
    type: String,
    default: '/login',
  },
  primaryText: {
    type: String,
    default: 'Зарегистрироваться',
  },
  secondaryTo: {
    type: String,
    default: '/templates',
  },
  secondaryText: {
    type: String,
    default: 'Смотреть шаблоны',
  },
})
</script>

<template>
  <section class="seo-cta">
    <h2>{{ title }}</h2>
    <p>{{ text }}</p>
    <div class="seo-cta__actions">
      <router-link :to="primaryTo" class="btn-primary-sm">{{ primaryText }}</router-link>
      <router-link :to="secondaryTo" class="btn-ghost">{{ secondaryText }}</router-link>
    </div>
  </section>
</template>
