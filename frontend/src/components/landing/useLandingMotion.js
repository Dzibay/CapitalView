import { onMounted, onUnmounted } from 'vue'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

gsap.registerPlugin(ScrollTrigger)

/**
 * Плавный скролл (Lenis), синхронизированный с GSAP ScrollTrigger.
 * Возвращает геттер инстанса — нужен для якорных ссылок.
 */
export function useSmoothScroll() {
  let lenis = null
  let tick = null

  onMounted(() => {
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual'
    if (!location.hash) { window.scrollTo(0, 0); requestAnimationFrame(() => window.scrollTo(0, 0)) }
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    lenis = new Lenis({ duration: 1.15, smoothWheel: true, wheelMultiplier: 0.95 })
    lenis.on('scroll', ScrollTrigger.update)
    tick = (time) => lenis?.raf(time * 1000)
    gsap.ticker.add(tick)
    gsap.ticker.lagSmoothing(0)
  })

  onUnmounted(() => {
    if (tick) gsap.ticker.remove(tick)
    lenis?.destroy()
    lenis = null
  })

  function scrollTo(target) {
    const el = typeof target === 'string' ? document.querySelector(target) : target
    if (!el) return
    if (lenis) lenis.scrollTo(el, { offset: -20 })
    else el.scrollIntoView({ behavior: 'smooth' })
  }

  return { scrollTo, getLenis: () => lenis }
}

/** Подключает Google Fonts только для лендинга. */
export function useLandingFonts(href) {
  let link = null
  onMounted(() => {
    if (document.querySelector(`link[data-landing-font="${href}"]`)) return
    link = document.createElement('link')
    link.rel = 'stylesheet'
    link.href = href
    link.dataset.landingFont = href
    document.head.appendChild(link)
  })
  onUnmounted(() => link?.remove())
}

/** Склонение-независимый формат рублей: 1 234 567 ₽ */
export function formatRub(value) {
  return Math.round(value).toLocaleString('ru-RU').replace(/,/g, ' ') + ' ₽'
}

export function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
}
