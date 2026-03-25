<script setup>
import { defineAsyncComponent, nextTick, onMounted, onUnmounted, provide, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useLandingContent } from '../../composables/useLandingContent'
import { useLandingReveal } from '../../composables/useLandingReveal'
import LandingBackground from './LandingBackground.vue'
import LandingHeader from './LandingHeader.vue'
import LandingHeroScrollScene from './LandingHeroScrollScene.vue'
import LandingHeroBlocksOverlay from './LandingHeroBlocksOverlay.vue'
import LandingDashboardMock from './LandingDashboardMock.vue'
import LandingFooter from './LandingFooter.vue'

import './landing-page.css'

gsap.registerPlugin(ScrollTrigger)

// Секции ниже первого экрана можно грузить лениво:
// это уменьшает стартовый JS и ускоряет первичную отрисовку.
const LandingPainSection = defineAsyncComponent(() => import('./sections/LandingPainSection.vue'))
const LandingFeaturesSection = defineAsyncComponent(() => import('./sections/LandingFeaturesSection.vue'))
const LandingStepsSection = defineAsyncComponent(() => import('./sections/LandingStepsSection.vue'))
const LandingIntegrationSection = defineAsyncComponent(() => import('./sections/LandingIntegrationSection.vue'))
const LandingPricingSection = defineAsyncComponent(() => import('./sections/LandingPricingSection.vue'))
const LandingFaqSection = defineAsyncComponent(() => import('./sections/LandingFaqSection.vue'))

const HEADER_SCROLL_OFFSET = 72
const DASHBOARD_ENTRY_Y_BASE_PERCENT = 60
const DASHBOARD_ENTRY_Y_MIN_PERCENT = 40
const DASHBOARD_ENTRY_Y_MAX_PERCENT = 118
const DASHBOARD_ENTRY_REF_VIEWPORT_HEIGHT = 900

const rootRef = ref(null)
const heroStageRef = ref(null)
const heroSectionRef = ref(null)
const dashboardSpacerRef = ref(null)
const dashboardPullRef = ref(null)
const dashboardOverlapRef = ref(null)

provide('landingHeroScrollTrigger', heroSectionRef)

useLandingReveal(rootRef)

let dashboardScrollTween = null
let detachReleasedDashboardListeners = null
let dashboardIntroTween = null

const isMobile = ref(false)

onMounted(() => {
  isMobile.value = window.innerWidth < 768
})

onMounted(async () => {
  document.documentElement.classList.add('cv-landing-snap')

  await nextTick()
  const stage = heroStageRef.value
  const spacer = dashboardSpacerRef.value
  const pull = dashboardPullRef.value
  const overlap = dashboardOverlapRef.value
  if (!stage || !spacer || !pull) return

  let dashboardInSectionFlow = false
  let syncPullRaf = null

  function syncPullToSpacerCenter() {
    if (!dashboardInSectionFlow || !spacer || !pull) return
    const r = spacer.getBoundingClientRect()
    const y = r.top + r.height * 0.5
    gsap.set(pull, {
      position: 'fixed',
      top: y,
      left: '50%',
      right: 'auto',
      bottom: 'auto',
      xPercent: -50,
      yPercent: -50,
      zIndex: 5,
      width: 'min(1200px, calc(100vw - 32px))',
      maxWidth: 960
    })
  }

  function scheduleSyncPullToSpacer() {
    if (syncPullRaf != null) return
    syncPullRaf = requestAnimationFrame(() => {
      syncPullRaf = null
      syncPullToSpacerCenter()
    })
  }

  function onScrollReleasedDashboard() {
    const st = dashboardScrollTween?.scrollTrigger
    if (!dashboardInSectionFlow || !st) return
    if (st.scroll() < st.end) {
      restoreDashboardFixedScrub()
      return
    }
    scheduleSyncPullToSpacer()
  }

  function releaseDashboardToSectionFlow() {
    if (dashboardInSectionFlow) return
    dashboardInSectionFlow = true
    const st = dashboardScrollTween?.scrollTrigger
    if (st) st.disable(false)
    window.addEventListener('scroll', onScrollReleasedDashboard, { passive: true })
    window.addEventListener('resize', scheduleSyncPullToSpacer, { passive: true })
    detachReleasedDashboardListeners = () => {
      window.removeEventListener('scroll', onScrollReleasedDashboard)
      window.removeEventListener('resize', scheduleSyncPullToSpacer)
    }
    scheduleSyncPullToSpacer()
  }

  function restoreDashboardFixedScrub() {
    if (!dashboardInSectionFlow) return
    detachReleasedDashboardListeners?.()
    detachReleasedDashboardListeners = null
    if (syncPullRaf != null) {
      cancelAnimationFrame(syncPullRaf)
      syncPullRaf = null
    }
    dashboardInSectionFlow = false
    const st = dashboardScrollTween?.scrollTrigger
    if (st) {
      st.enable()
      st.update()
    }
    ScrollTrigger.refresh()
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    gsap.set(pull, {
      position: 'fixed',
      left: '50%',
      right: 'auto',
      xPercent: -50,
      top: '50%',
      bottom: 'auto',
      yPercent: -50,
      zIndex: 5,
      width: 'min(1200px, calc(100vw - 32px))',
      maxWidth: 960
    })
    return
  }

  // Локальный интро-подъём контента дашборда (без конфликта с scroll-анимацией контейнера).
  if (overlap) {
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
        clearProps: 'filter'
      }
    )
  }

  function getDashboardStartYPercent() {
    const viewportHeight = window.innerHeight || DASHBOARD_ENTRY_REF_VIEWPORT_HEIGHT
    const k = viewportHeight / DASHBOARD_ENTRY_REF_VIEWPORT_HEIGHT
    const y = DASHBOARD_ENTRY_Y_BASE_PERCENT / k
    return Math.max(DASHBOARD_ENTRY_Y_MIN_PERCENT, Math.min(DASHBOARD_ENTRY_Y_MAX_PERCENT, y))
  }

  dashboardScrollTween = gsap.fromTo(
    pull,
    {
      position: 'fixed',
      left: '50%',
      right: 'auto',
      xPercent: -50,
      bottom: 0,
      top: 'auto',
      yPercent: () => getDashboardStartYPercent(),
      zIndex: 5,
      width: 'min(1200px, calc(100vw - 32px))',
      maxWidth: 960
    },
    {
      top: '50%',
      bottom: 'auto',
      yPercent: -50,
      width: 'min(1200px, calc(100vw - 32px))',
      maxWidth: 960,
      ease: 'none',
      immediateRender: true,
      scrollTrigger: {
        trigger: stage,
        start: `top ${HEADER_SCROLL_OFFSET}px`,
        endTrigger: spacer,
        end: 'top top',
        scrub: 0,
        invalidateOnRefresh: true,
        onUpdate(self) {
          if (self.progress >= 1) {
            releaseDashboardToSectionFlow()
          }
        }
      }
    }
  )

  ScrollTrigger.refresh()
  const stInit = dashboardScrollTween.scrollTrigger
  if (stInit && stInit.progress >= 1) {
    releaseDashboardToSectionFlow()
  }
})

onUnmounted(() => {
  document.documentElement.classList.remove('cv-landing-snap')
  detachReleasedDashboardListeners?.()
  detachReleasedDashboardListeners = null
  dashboardIntroTween?.kill()
  dashboardIntroTween = null
  dashboardScrollTween?.scrollTrigger?.kill()
  dashboardScrollTween?.kill()
  dashboardScrollTween = null
})

const {
  painPoints,
  features,
  steps,
  integrationFeatures,
  comingSoonBrokers,
  pricing,
  testimonials,
  faq
} = useLandingContent()
</script>

<template>
  <div ref="rootRef" class="cv-landing">
    <LandingBackground />
    <LandingHeader />

    <div ref="heroStageRef" class="landing-hero-dashboard-stage">
      <div class="landing-hero-bg" aria-hidden="true" />
      <LandingHeroBlocksOverlay v-if="!isMobile" />
      <section ref="heroSectionRef" class="landing-hero-section">
        <LandingHeroScrollScene />
      </section>
    </div>

    <div
      v-if="!isMobile"
      ref="dashboardPullRef"
      class="landing-dashboard-floating"
      aria-label="Пример интерфейса"
    >
      <div ref="dashboardOverlapRef" class="container landing-dashboard-overlap">
        <LandingDashboardMock />
      </div>
    </div>

    <section v-if="!isMobile" ref="dashboardSpacerRef" class="landing-dashboard-section snap-section" />

    <LandingPainSection :items="painPoints" />
    <LandingFeaturesSection :items="features" />
    <LandingStepsSection :items="steps" />
    <LandingIntegrationSection
      :integration-features="integrationFeatures"
      :coming-soon-brokers="comingSoonBrokers"
    />
    <LandingPricingSection :plans="pricing" />
    <LandingFaqSection :items="faq" />
    <LandingFooter />
  </div>
</template>
