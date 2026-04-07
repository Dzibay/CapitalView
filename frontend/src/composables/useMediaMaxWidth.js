import { ref, onMounted, onUnmounted } from 'vue'

/**
 * Реактивное совпадение с media query (max-width: Npx).
 */
export function useMediaMaxWidth(px) {
  const query = `(max-width: ${px}px)`
  const matches = ref(
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false
  )
  let mql = null

  function sync() {
    matches.value = !!mql?.matches
  }

  onMounted(() => {
    if (typeof window === 'undefined') return
    mql = window.matchMedia(query)
    sync()
    mql.addEventListener('change', sync)
  })

  onUnmounted(() => {
    mql?.removeEventListener('change', sync)
  })

  return matches
}
