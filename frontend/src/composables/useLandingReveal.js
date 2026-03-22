import { nextTick, onMounted, onUnmounted } from 'vue'

const OBSERVER_OPTIONS = { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }

/**
 * Появление блоков .reveal при скролле (корень — обёртка лендинга).
 */
export function useLandingReveal(rootRef) {
  let observer

  function attach() {
    observer?.disconnect()
    const root = rootRef.value
    if (!root) return
    observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible')
          observer.unobserve(entry.target)
        }
      })
    }, OBSERVER_OPTIONS)
    root.querySelectorAll('.reveal').forEach((el) => observer.observe(el))
  }

  onMounted(async () => {
    await nextTick()
    await nextTick()
    attach()
  })

  onUnmounted(() => {
    observer?.disconnect()
  })
}
