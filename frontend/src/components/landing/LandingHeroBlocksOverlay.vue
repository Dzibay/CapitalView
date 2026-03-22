<script setup>
import { inject, ref, onMounted, onUnmounted, nextTick } from 'vue'
import { gsap } from 'gsap'
import { MotionPathPlugin } from 'gsap/MotionPathPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import {
  HERO_ASSET_PATHS,
  HERO_MOTION_INTRO_PROGRESS,
  HERO_BLOCK_WEBP_SRCS,
  HERO_BLOCK_ROTATION_START_DEG,
  HERO_BLOCK_ROTATION_END_DEG,
  HERO_BLOCK_ROTATION_DURATION
} from './config/heroAssetPaths'

gsap.registerPlugin(MotionPathPlugin, ScrollTrigger)

const PATHS = HERO_ASSET_PATHS
const BLOCK_ICONS = HERO_BLOCK_WEBP_SRCS
const INTRO_PROGRESS = HERO_MOTION_INTRO_PROGRESS

const landingHeroScrollTrigger = inject('landingHeroScrollTrigger')
const blocksLayer = ref(null)

let introTween = null
let scrollScrubTween = null

const HEADER_SCROLL_OFFSET = 72

function pathId(i) {
  return `hero-asset-path-${i}`
}

onMounted(async () => {
  await nextTick()
  const prefersReduced =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const isNarrow = typeof window !== 'undefined' && window.matchMedia('(max-width: 767px)').matches

  const triggerEl = landingHeroScrollTrigger?.value
  if (!triggerEl || !blocksLayer.value) return

  const blocks = Array.from(blocksLayer.value.querySelectorAll('.asset-block'))
  if (blocks.length !== 6) return

  if (prefersReduced || isNarrow) {
    blocks.forEach((el, i) => {
      const sel = `#${pathId(i)}`
      const endRot = HERO_BLOCK_ROTATION_END_DEG[i] ?? 0
      gsap.set(el, {
        opacity: 1,
        scale: 1,
        rotation: endRot,
        xPercent: -50,
        yPercent: -50,
        motionPath: {
          path: sel,
          align: sel,
          alignOrigin: [0.5, 0.5],
          autoRotate: false,
          end: 1
        }
      })
    })
    return
  }

  // 1. Создаем базовый таймлайн путей
  const tl = gsap.timeline({ paused: true })
  blocks.forEach((el, i) => {
    const sel = `#${pathId(i)}`
    const startRot = HERO_BLOCK_ROTATION_START_DEG[i] ?? 0
    const endRot = HERO_BLOCK_ROTATION_END_DEG[i] ?? 0

    // Движение по кривой (от 0 до 1)
    tl.to(el, {
      motionPath: {
        path: sel,
        align: sel,
        alignOrigin: [0.5, 0.5],
        autoRotate: false,
        end: 1
      },
      duration: 1,
      ease: 'none'
    }, 0)

    tl.fromTo(
      el,
      { rotation: startRot },
      {
        rotation: endRot,
        duration: HERO_BLOCK_ROTATION_DURATION,
        ease: 'power2.out'
      },
      0
    )

    // ДОБАВЛЯЕМ: Исчезновение в самом конце (например, с 0.85 до 1.0 прогресса)
    tl.to(el, {
      opacity: 0,
      scale: 0.5,
      duration: 0.15, // Занимает последние 15% таймлайна
      ease: 'power1.in'
    }, 0.85) // Начинаем за 0.15 до конца
  })

  // 2. Объект состояния (остается из предыдущего совета)
  const motionState = {
    intro: 0,
    scroll: 0
  }

  const updateVisuals = () => {
    const totalProgress = motionState.intro + (motionState.scroll * (1 - motionState.intro))
    tl.progress(totalProgress)
  }

  // 3. Начальное появление (быстрый fade-in в самом начале)
  // Убираем старый gsap.to(blocks, {opacity: 1...}), так как теперь opacity управляет tl
  gsap.set(blocks, { 
    opacity: 0, 
    scale: 0.85, 
    xPercent: -50, 
    yPercent: -50 
  })
  
  // Добавляем короткую анимацию появления "из небытия" отдельно
  gsap.to(blocks, {
    opacity: 1,
    scale: 1,
    duration: 0.4,
    stagger: 0.05,
    ease: 'power2.out'
  })

  // 4. Движение интро
  introTween = gsap.to(motionState, {
    intro: INTRO_PROGRESS,
    duration: 1.6,
    ease: 'power2.out',
    delay: 0.1,
    onUpdate: updateVisuals
  })

  // 5. ScrollTrigger
  scrollScrubTween = ScrollTrigger.create({
    trigger: triggerEl,
    start: `top ${HEADER_SCROLL_OFFSET}px`,
    end: 'bottom 22%',
    scrub: 0.8,
    onUpdate: (self) => {
      motionState.scroll = self.progress
      updateVisuals()
    }
  })
})

onUnmounted(() => {
  introTween?.kill()
  scrollScrubTween?.scrollTrigger?.kill()
  scrollScrubTween?.kill()
})
</script>

<template>
  <div ref="blocksLayer" class="landing-hero-blocks-overlay" aria-hidden="true">
    <svg
      class="hero-motion-svg"
      viewBox="0 0 100 100"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        v-for="(d, i) in PATHS"
        :id="pathId(i)"
        :key="i"
        :d="d"
        class="curve-path"
        fill="none"
      />
    </svg>
    <div v-for="(_, i) in PATHS" :key="'block-' + i" class="asset-block">
      <img
        class="asset-block__icon"
        :src="BLOCK_ICONS[i]"
        width="48"
        height="48"
        decoding="async"
        draggable="false"
        alt=""
      />
    </div>
  </div>
</template>

<style scoped>
.landing-hero-blocks-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 2;
}

.hero-motion-svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: visible;
}

/* Пути нужны MotionPathPlugin; линии не рисуем */
.curve-path {
  fill: none;
  stroke: none;
  pointer-events: none;
}

.asset-block {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: clamp(44px, 5.2vw, 62px);
  height: clamp(44px, 5.2vw, 62px);
  border-radius: 16px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow:
    0 0 0 1px rgba(15, 23, 42, 0.06),
    0 12px 32px rgba(15, 23, 42, 0.1),
    0 4px 12px rgba(15, 23, 42, 0.04);
  overflow: hidden;
  will-change: transform;
}

.asset-block__icon {
  width: clamp(34px, 5.1vw, 52px);
  height: clamp(34px, 5.1vw, 52px);
  object-fit: contain;
  pointer-events: none;
  user-select: none;
}

@media (max-width: 767px) {
  .asset-block {
    opacity: 0.55;
  }
}
</style>
