<script setup>
import { provide, computed } from 'vue'
import { SEO_STEP_FLOW_LAYOUT_KEY } from './seoStepFlowContext'

const props = defineProps({
  ariaLabel: {
    type: String,
    default: 'Последовательность шагов',
  },
  /** stack — вертикальная цепочка со стрелками; grid — сетка 2×2 в стиле блоков лендинга */
  layout: {
    type: String,
    default: 'stack',
    validator: (v) => ['stack', 'grid'].includes(v),
  },
})

const layoutMode = computed(() => props.layout)
provide(SEO_STEP_FLOW_LAYOUT_KEY, layoutMode)
</script>

<template>
  <ol
    class="seo-step-flow"
    :class="{ 'seo-step-flow--grid': layout === 'grid' }"
    :aria-label="ariaLabel"
  >
    <slot />
  </ol>
</template>
