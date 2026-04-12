<script setup>
import { defineAsyncComponent, nextTick, onMounted, onUnmounted, provide, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useLandingContent } from '../composables/useLandingContent'
import { useLandingReveal } from '../composables/useLandingReveal'
import LandingHero from '../components/home/LandingHero.vue'
import LandingHeroBlocksOverlay from '../components/home/LandingHeroBlocksOverlay.vue'
import LandingDashboardMock from '../components/home/LandingDashboardMock.vue'

gsap.registerPlugin(ScrollTrigger)

const LandingAnalyticsSection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingAnalyticsSection.vue')
)
const LandingStepsSection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingStepsSection.vue')
)
const LandingIntegrationSection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingIntegrationSection.vue')
)
const LandingSecuritySection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingSecuritySection.vue')
)
const LandingPricingSection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingPricingSection.vue')
)
const LandingFaqSection = defineAsyncComponent(() =>
  import('../components/home/sections/LandingFaqSection.vue')
)

const rootRef = ref(null)
const heroSectionRef = ref(null)
const dashboardOverlapRef = ref(null)

provide('landingHeroScrollTrigger', heroSectionRef)

useLandingReveal(rootRef)

let dashboardIntroTween = null

const isMobile = ref(false)

onMounted(() => {
  isMobile.value = window.innerWidth < 768
})

onMounted(async () => {
  document.documentElement.classList.add('cv-landing-snap')

  await nextTick()
  const overlap = dashboardOverlapRef.value
  if (!overlap) return

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

  dashboardIntroTween = gsap.fromTo(
    overlap,
    { autoAlpha: 0, y: 26, scale: 0.985, filter: 'blur(8px)' },
    {
      autoAlpha: 1,
      y: 0,
      scale: 1,
      filter: 'blur(0px)',
      duration: 0.95,
      delay: 0.12,
      ease: 'power3.out',
      clearProps: 'filter',
    }
  )
})

onUnmounted(() => {
  document.documentElement.classList.remove('cv-landing-snap')
  dashboardIntroTween?.kill()
  dashboardIntroTween = null
})

const {
  integrationBullets,
  comingSoonBrokers,
  steps,
  securityTabs,
  pricingFeatures,
  faq,
} = useLandingContent()
</script>

<template>
  <div ref="rootRef" class="home-page">
    <div class="landing-hero-dashboard-stage">
      <div class="landing-hero-bg" aria-hidden="true" />
      <section ref="heroSectionRef" class="landing-hero-section">
        <LandingHeroBlocksOverlay v-if="!isMobile" />
        <LandingHero />
      </section>

      <div
        v-if="!isMobile"
        ref="dashboardOverlapRef"
        class="container landing-dashboard-wrap"
        aria-label="Пример интерфейса дашборда CapitalView"
      >
        <LandingDashboardMock />
      </div>
    </div>

    <div class="landing-light-surface">
      <div class="landing-light-vlines" aria-hidden="true">
        <span class="landing-light-vline" /><span class="landing-light-vline" />
        <span class="landing-light-vline" /><span class="landing-light-vline" />
        <span class="landing-light-vline" /><span class="landing-light-vline" />
        <span class="landing-light-vline" /><span class="landing-light-vline" />
      </div>
      <LandingAnalyticsSection />
      <LandingIntegrationSection
        :bullets="integrationBullets"
        :coming-soon-brokers="comingSoonBrokers"
      />
      <LandingStepsSection :items="steps" />
      <LandingSecuritySection :tabs="securityTabs" />
      <LandingPricingSection :features="pricingFeatures" />
      <LandingFaqSection :items="faq" />
    </div>
  </div>
</template>
