<script setup>
defineProps({
  title: {
    type: String,
    required: true,
  },
  lead: {
    type: String,
    default: '',
  },
  highlightedKeywords: {
    type: Array,
    default: () => [],
  },
  sections: {
    type: Array,
    default: () => [
      {
        title: 'Содержание раздела',
        body: 'Здесь появится текст и визуал. Каркас страницы можно оформить отдельно.',
      },
      {
        title: 'Возможности',
        body: 'Краткое описание функций под этот запрос и сценарий использования.',
      },
      {
        title: 'Следующие шаги',
        body: 'Призыв попробовать сервис или перейти к связанным разделам.',
      },
    ],
  },
})
</script>

<template>
  <article class="site-article">
    <h1 class="site-article__title">{{ title }}</h1>
    <p v-if="lead" class="site-article__lead">{{ lead }}</p>
    <div v-if="highlightedKeywords.length" class="site-article__keywords" aria-label="Выделенные ключевые запросы">
      <span
        v-for="keyword in highlightedKeywords"
        :key="keyword"
        class="site-article__keyword-chip"
      >
        {{ keyword }}
      </span>
    </div>
    <section
      v-for="(block, i) in sections"
      :key="i"
      class="site-article__section"
    >
      <h2 class="site-article__h2">{{ block.title }}</h2>
      <p class="site-article__body">{{ block.body }}</p>
    </section>
  </article>
</template>

<style scoped>
.site-article {
  width: 100%;
}

.site-article__title {
  font-size: clamp(1.75rem, 4vw, 2.25rem);
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 12px;
  color: #0f172a;
  line-height: 1.2;
}

.site-article__lead {
  font-size: 1.05rem;
  line-height: 1.6;
  color: #475569;
  margin: 0 0 40px;
}

.site-article__keywords {
  margin: -10px 0 32px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.site-article__keyword-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.22);
  color: #1d4ed8;
  font-size: 13px;
  line-height: 1.2;
  font-weight: 600;
}

.site-article__section {
  margin-bottom: 28px;
}

.site-article__section:last-child {
  margin-bottom: 0;
}

.site-article__h2 {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 0 0 10px;
  color: #0f172a;
}

.site-article__body {
  font-size: 0.95rem;
  line-height: 1.65;
  color: #64748b;
  margin: 0;
}
</style>
