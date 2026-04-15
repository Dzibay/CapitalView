<script setup>
import LandingBackground from '../components/home/LandingBackground.vue'
import LandingHeader from '../components/home/LandingHeader.vue'
import LandingFooter from '../components/home/LandingFooter.vue'

import '../styles/landing-page.css'
import '../styles/seo-pages.css'
</script>

<template>
  <div class="site-public cv-landing">
    <LandingBackground />
    <LandingHeader />
    <main class="site-public__main">
      <router-view />
    </main>
    <LandingFooter />
  </div>
</template>

<style scoped>
.site-public {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.site-public__main {
  flex: 1;
  min-height: 0;
}
</style>
