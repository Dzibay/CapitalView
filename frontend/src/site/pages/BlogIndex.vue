<script setup>
import SiteArticle from '../components/SiteArticle.vue'
import SiteSeoPage from '../components/SiteSeoPage.vue'
</script>

<template>
  <SiteSeoPage>
    <SiteArticle
      title="Блог и материалы"
      lead="Каркас списка публикаций; позже — статьи под информационные запросы из семантики."
      :sections="[
        {
          title: 'Публикации',
          body: 'Список статей и фильтры по темам появятся здесь.',
        },
        {
          title: 'Темы',
          body: 'Личные инвестиции, портфель, налоги, интеграции с брокерами — по мере наполнения.',
        },
      ]"
    />
  </SiteSeoPage>
</template>
