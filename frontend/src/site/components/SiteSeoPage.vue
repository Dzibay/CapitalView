<template>
  <div class="landing-light-surface site-seo-page">
    <div class="container site-seo-page__inner">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.site-seo-page {
  /* Фиксированная шапка .cv-landing .header-inner: 64px (60px ≤767px) */
  padding-top: calc(64px + 24px);
  padding-bottom: 64px;
}

@media (max-width: 767px) {
  .site-seo-page {
    padding-top: calc(60px + 20px);
  }
}

.site-seo-page__inner {
  padding-top: 8px;
  padding-bottom: 32px;
}
</style>
