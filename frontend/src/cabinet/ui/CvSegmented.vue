<script setup>
/** Сегментный переключатель со скользящей подложкой. */
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], required: true },
  options: { type: Array, required: true }, // [{ value, label }]
  size: { type: String, default: 'md' },
  ariaLabel: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const root = ref(null)
const pill = ref({ x: 0, w: 0, ready: false })

function measure() {
  const el = root.value?.querySelector('.is-active')
  if (!el) {
    // ни один вариант не выбран (например, ручной зум графика) — прячем подложку
    pill.value = { ...pill.value, ready: false }
    return
  }
  pill.value = { x: el.offsetLeft, w: el.offsetWidth, ready: true }
}

let ro
onMounted(() => {
  measure()
  ro = new ResizeObserver(measure)
  ro.observe(root.value)
  document.fonts?.ready?.then(measure)
})
onBeforeUnmount(() => ro?.disconnect())
watch(() => [props.modelValue, props.options.length], () => nextTick(measure))
</script>

<template>
  <div ref="root" class="cv-seg" :class="`cv-seg--${size}`" role="tablist" :aria-label="ariaLabel">
    <span
      class="cv-seg__pill"
      :class="{ 'is-ready': pill.ready }"
      :style="{ transform: `translateX(${pill.x}px)`, width: `${pill.w}px` }"
      aria-hidden="true"
    />
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      role="tab"
      class="cv-seg__btn"
      :class="{ 'is-active': o.value === modelValue }"
      :aria-selected="o.value === modelValue"
      @click="emit('update:modelValue', o.value)"
    >
      {{ o.label }}
    </button>
  </div>
</template>

<style scoped>
.cv-seg {
  position: relative; display: inline-flex; padding: 3px; gap: 2px;
  border-radius: 11px; background: rgba(255, 255, 255, .04);
  box-shadow: inset 0 0 0 1px var(--cv-line);
}
.cv-seg__pill {
  position: absolute; top: 3px; bottom: 3px; left: 0; border-radius: 8px;
  background: linear-gradient(180deg, rgba(255, 255, 255, .11), rgba(255, 255, 255, .07));
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, .08), 0 2px 8px -2px rgba(0, 0, 0, .5);
  opacity: 0;
}
.cv-seg__pill.is-ready {
  opacity: 1;
  transition: transform .38s var(--cv-ease), width .38s var(--cv-ease);
}
.cv-seg__btn {
  position: relative; z-index: 1; height: 28px; padding: 0 11px; border: 0; border-radius: 8px;
  background: transparent; color: var(--cv-mut); font-size: 12.5px; font-weight: 550; cursor: pointer;
  transition: color .2s; white-space: nowrap;
}
.cv-seg__btn:hover { color: var(--cv-ink-2); }
.cv-seg__btn.is-active { color: var(--cv-ink); }
.cv-seg--sm .cv-seg__btn { height: 24px; padding: 0 9px; font-size: 12px; }
</style>
