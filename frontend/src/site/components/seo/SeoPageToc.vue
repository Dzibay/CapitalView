<script setup>
defineProps({
  title: {
    type: String,
    default: 'На этой странице',
  },
  ariaLabel: {
    type: String,
    default: 'Разделы страницы',
  },
  /** { href: string (якорь или URL), label: string } */
  items: {
    type: Array,
    required: true,
  },
})
</script>

<template>
  <nav class="seo-toc seo-toc--editorial" :aria-label="ariaLabel">
    <p class="seo-toc__title">{{ title }}</p>
    <ul class="seo-toc__list">
      <li v-for="(item, index) in items" :key="`${item.href}-${index}`">
        <a :href="item.href">{{ item.label }}</a>
      </li>
    </ul>
  </nav>
</template>
