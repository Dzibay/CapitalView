<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { seoKeywordPlanByPath } from '../content/seoKeywordPlan'

const route = useRoute()

const seoPlan = computed(() => seoKeywordPlanByPath[route.path] ?? null)
</script>

<template>
  <div class="site-seo-page">
    <div class="container site-seo-page__inner">
      <section v-if="seoPlan" class="site-seo-keywords" aria-label="Временный SEO-план по странице">
        <p class="site-seo-keywords__caption">Временный SEO-кластер</p>
        <h2 class="site-seo-keywords__title">{{ seoPlan.cluster }}</h2>
        <ul class="site-seo-keywords__list">
          <li v-for="keyword in seoPlan.keywords" :key="keyword" class="site-seo-keywords__item">
            {{ keyword }}
          </li>
        </ul>
      </section>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.site-seo-page {
  position: relative;
  z-index: 1;
  overflow: hidden;
  /* Фиксированная шапка .cv-landing .header-inner: 64px (60px <=767px) */
  padding-top: calc(64px + 24px);
  padding-bottom: 64px;
}

.site-seo-page::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: -1;
  pointer-events: none;
  background:
    radial-gradient(ellipse 72% 36% at 12% 6%, rgba(59, 130, 246, 0.12), transparent 64%),
    radial-gradient(ellipse 56% 30% at 90% 10%, rgba(139, 92, 246, 0.11), transparent 62%),
    linear-gradient(180deg, rgba(250, 251, 253, 0.76) 0%, rgba(248, 249, 251, 0.9) 42%, rgba(248, 249, 251, 0.95) 100%);
}

@media (max-width: 767px) {
  .site-seo-page {
    padding-top: calc(60px + 20px);
  }
}

.site-seo-page__inner {
  position: relative;
  z-index: 1;
  width: 100%;
  padding-top: 8px;
  padding-bottom: 32px;
}

.site-seo-keywords {
  margin-bottom: 24px;
  padding: 14px;
  border: 1px dashed rgba(59, 130, 246, 0.4);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
}

.site-seo-keywords__caption {
  margin: 0 0 8px;
  font-size: 12px;
  line-height: 1.25;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #3b82f6;
  font-weight: 700;
}

.site-seo-keywords__title {
  margin: 0 0 10px;
  font-size: 18px;
  line-height: 1.2;
  color: #0f172a;
}

.site-seo-keywords__list {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.site-seo-keywords__item {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(100, 116, 139, 0.28);
  background: rgba(248, 250, 252, 0.9);
  color: #334155;
  font-size: 13px;
  line-height: 1.2;
}
</style>
