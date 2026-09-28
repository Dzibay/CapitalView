<template>
  <div class="site-seo-page">
    <div class="container site-seo-page__inner">
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
    radial-gradient(ellipse 72% 36% at 12% 6%, rgba(47, 95, 143, 0.1), transparent 64%),
    radial-gradient(ellipse 56% 30% at 90% 10%, rgba(74, 122, 173, 0.08), transparent 62%),
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
</style>
