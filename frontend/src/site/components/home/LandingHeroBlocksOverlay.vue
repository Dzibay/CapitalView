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
let detachResizeListeners = null
let resizeRaf = null
let blocksResizeObserver = null

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
  const observeTargetEl = triggerEl || blocksLayer.value

  const blocks = Array.from(blocksLayer.value.querySelectorAll('.asset-block'))
  if (blocks.length !== 6) return

  function scheduleReflow(fn) {
    if (resizeRaf != null) return
    resizeRaf = requestAnimationFrame(() => {
      resizeRaf = null
      fn()
    })
  }

  function placeBlocksAtPathEnd() {
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
  }

  if (prefersReduced || isNarrow) {
    placeBlocksAtPathEnd()
    const onResize = () => scheduleReflow(placeBlocksAtPathEnd)
    window.addEventListener('resize', onResize, { passive: true })
    window.addEventListener('orientationchange', onResize, { passive: true })
    if (typeof ResizeObserver !== 'undefined' && observeTargetEl) {
      blocksResizeObserver = new ResizeObserver(() => onResize())
      blocksResizeObserver.observe(observeTargetEl)
    }
    detachResizeListeners = () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
      blocksResizeObserver?.disconnect()
      blocksResizeObserver = null
    }
    return
  }

  function buildTimeline() {
    const timeline = gsap.timeline({ paused: true })
    blocks.forEach((el, i) => {
      const sel = `#${pathId(i)}`
      const startRot = HERO_BLOCK_ROTATION_START_DEG[i] ?? 0
      const endRot = HERO_BLOCK_ROTATION_END_DEG[i] ?? 0

      // Движение по кривой (от 0 до 1)
      timeline.to(el, {
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

      timeline.fromTo(
        el,
        { rotation: startRot },
        {
          rotation: endRot,
          duration: HERO_BLOCK_ROTATION_DURATION,
          ease: 'power2.out'
        },
        0
      )

      // Исчезновение в самом конце
      timeline.to(el, {
        opacity: 0,
        scale: 0.5,
        duration: 0.15,
        ease: 'power1.in'
      }, 0.85)
    })
    return timeline
  }

  // 1. Создаем базовый таймлайн путей
  let tl = buildTimeline()

  // 2. Объект состояния (остается из предыдущего совета)
  const motionState = {
    intro: 0,
    scroll: 0
  }

  // Фикс: при открытии страницы “не с верха” сначала синхронизируем
  // положение по пути в progress=0, чтобы кубики не были в (0,0) до onUpdate.
  tl.progress(0)

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

  // 4. ScrollTrigger
  let lastScrollProgress = null
  scrollScrubTween = ScrollTrigger.create({
    trigger: triggerEl,
    start: `top ${HEADER_SCROLL_OFFSET}px`,
    end: 'bottom 22%',
    scrub: 0.8,
    onUpdate: (self) => {
      motionState.scroll = self.progress
      updateVisuals()

      // Если идём обратно вверх из зоны fade-out — один раз принудительно возвращаем видимость.
      // Это дешевле, чем gsap.set на каждом onUpdate.
      if (lastScrollProgress != null && self.progress < 0.84 && lastScrollProgress >= 0.84) {
        gsap.set(blocks, { opacity: 1, scale: 1 })
      }
      lastScrollProgress = self.progress
    }
  })

  // Синхронизируем текущий скролл сразу после создания триггера.
  // Это устраняет "скачок" и неправильную стартовую позицию при открытии не с верха.
  const initialScrollProgress = scrollScrubTween.progress ?? 0
  motionState.scroll = initialScrollProgress

  // 5. Интро запускаем по факту старта страницы (scrollY близко к 0),
  // а не по progress ScrollTrigger — он может быть > 0 даже при загрузке сверху.
  const pageIsNearTop = (typeof window !== 'undefined' ? window.scrollY : 0) <= 24
  if (pageIsNearTop) {
    introTween = gsap.to(motionState, {
      intro: INTRO_PROGRESS,
      duration: 1.6,
      ease: 'power2.out',
      delay: 0.1,
      onUpdate: updateVisuals
    })
  } else {
    // Если страница уже прокручена, считаем интро завершенным.
    motionState.intro = INTRO_PROGRESS
  }
  updateVisuals()

  // На resize/повороте экрана пересчитываем геометрию ScrollTrigger и позицию кубиков.
  const onResize = () =>
    scheduleReflow(() => {
      ScrollTrigger.refresh()
      // MotionPath кэширует геометрию кривых: при ширинном resize
      // надежнее пересобрать timeline, чем пытаться invalidate().
      const currentProgress = tl.progress()
      tl.kill()
      tl = buildTimeline()
      tl.progress(currentProgress)
      const st = scrollScrubTween
      motionState.scroll = st ? st.progress : motionState.scroll
      updateVisuals()
    })
  window.addEventListener('resize', onResize, { passive: true })
  window.addEventListener('orientationchange', onResize, { passive: true })
  if (typeof ResizeObserver !== 'undefined' && blocksLayer.value) {
    blocksResizeObserver = new ResizeObserver(() => onResize())
    blocksResizeObserver.observe(observeTargetEl)
  }
  detachResizeListeners = () => {
    window.removeEventListener('resize', onResize)
    window.removeEventListener('orientationchange', onResize)
    blocksResizeObserver?.disconnect()
    blocksResizeObserver = null
  }
})

onUnmounted(() => {
  detachResizeListeners?.()
  detachResizeListeners = null
  if (resizeRaf != null) {
    cancelAnimationFrame(resizeRaf)
    resizeRaf = null
  }
  blocksResizeObserver?.disconnect()
  blocksResizeObserver = null
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
  top: 0;
  bottom: 0;
  left: 50%;
  right: auto;
  /* Чтобы траектория кубиков была в том же “коридоре”, что и дашборд (max-width: 1000px). */
  width: min(100%, 1200px);
  transform: translateX(-50%);
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
