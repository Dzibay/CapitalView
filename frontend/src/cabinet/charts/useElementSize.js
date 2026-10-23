import { onBeforeUnmount, onMounted, ref } from 'vue'

/** Размер элемента через ResizeObserver (округлён до пикселя). */
export function useElementSize(target) {
  const width = ref(0)
  const height = ref(0)
  let ro

  onMounted(() => {
    const el = target.value
    if (!el) return
    const apply = () => {
      width.value = Math.round(el.clientWidth)
      height.value = Math.round(el.clientHeight)
    }
    apply()
    ro = new ResizeObserver(apply)
    ro.observe(el)
  })
  onBeforeUnmount(() => ro?.disconnect())

  return { width, height }
}

export const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
