<script setup>
import { nextTick, onMounted, onUnmounted, provide, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { useLandingContent } from '../../composables/useLandingContent'
import { useLandingReveal } from '../../composables/useLandingReveal'
import LandingBackground from './LandingBackground.vue'
import LandingHeader from './LandingHeader.vue'
import LandingFooter from './LandingFooter.vue'
import LandingHeroScrollScene from './LandingHeroScrollScene.vue'
import LandingHeroBlocksOverlay from './LandingHeroBlocksOverlay.vue'
import LandingDashboardMock from './LandingDashboardMock.vue'
import LandingPainSection from './sections/LandingPainSection.vue'
import LandingFeaturesSection from './sections/LandingFeaturesSection.vue'
import LandingStepsSection from './sections/LandingStepsSection.vue'
import LandingIntegrationSection from './sections/LandingIntegrationSection.vue'
import LandingPricingSection from './sections/LandingPricingSection.vue'
import LandingTestimonialsSection from './sections/LandingTestimonialsSection.vue'
import LandingFaqSection from './sections/LandingFaqSection.vue'

import './landing-page.css'

gsap.registerPlugin(ScrollTrigger)

const HEADER_SCROLL_OFFSET = 72

const rootRef = ref(null)
const heroStageRef = ref(null)
const heroSectionRef = ref(null)
const dashboardSpacerRef = ref(null)
const dashboardPullRef = ref(null)

provide('landingHeroScrollTrigger', heroSectionRef)

useLandingReveal(rootRef)

let dashboardScrollTween = null
let detachReleasedDashboardListeners = null

onMounted(async () => {
  document.documentElement.classList.add('cv-landing-snap')

  await nextTick()
  const stage = heroStageRef.value
  const spacer = dashboardSpacerRef.value
  const pull = dashboardPullRef.value
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
      width: 'min(1000px, calc(100vw - 32px))',
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
      width: 'min(1000px, calc(100vw - 32px))',
      maxWidth: 960
    })
    return
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
      yPercent: 75,
      zIndex: 5,
      width: 'min(1000px, calc(100vw - 32px))',
      maxWidth: 960
    },
    {
      top: '50%',
      bottom: 'auto',
      yPercent: -50,
      width: 'min(1000px, calc(100vw - 32px))',
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
      <LandingHeroBlocksOverlay />
      <section ref="heroSectionRef" class="landing-hero-section">
        <LandingHeroScrollScene />
      </section>
    </div>

    <div
      ref="dashboardPullRef"
      class="landing-dashboard-floating"
      aria-label="Пример интерфейса"
    >
      <div class="container landing-dashboard-overlap">
        <LandingDashboardMock />
      </div>
    </div>

    <section ref="dashboardSpacerRef" class="landing-dashboard-section snap-section" />

    <LandingPainSection :items="painPoints" />
    <LandingFeaturesSection :items="features" />
    <LandingStepsSection :items="steps" />
    <LandingIntegrationSection
      :integration-features="integrationFeatures"
      :coming-soon-brokers="comingSoonBrokers"
    />
    <LandingPricingSection :plans="pricing" />
    <LandingTestimonialsSection :items="testimonials" />
    <LandingFaqSection :items="faq" />
    <LandingFooter />
  </div>
</template>
