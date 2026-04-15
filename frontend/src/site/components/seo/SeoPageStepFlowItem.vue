<script setup>
import { computed, inject } from 'vue'
import { SEO_STEP_FLOW_LAYOUT_KEY } from './seoStepFlowContext'

const props = defineProps({
  /** Порядковый номер шага (с 1). Задавайте явно — авто-счётчик через inject ломался при повторном монтировании/HMR. */
  step: {
    type: Number,
    required: true,
    validator: (v) => Number.isInteger(v) && v >= 1,
  },
  /** Заголовок шага (как block-heading на лендинге); для layout=&quot;grid&quot; желателен */
  title: {
    type: String,
    default: '',
  },
})

const stepNumber = computed(() => props.step)
const paddedNum = computed(() => String(props.step).padStart(2, '0'))

const layoutMode = inject(
  SEO_STEP_FLOW_LAYOUT_KEY,
  computed(() => 'stack'),
)
const isGrid = computed(() => layoutMode.value === 'grid')
</script>

<template>
  <li class="seo-step-flow__item">
    <template v-if="isGrid">
      <div class="seo-step-flow__tile">
        <div class="seo-step-flow__num" aria-hidden="true">{{ paddedNum }}</div>
        <h3 v-if="title" class="seo-step-flow__heading">{{ title }}</h3>
        <div class="seo-step-flow__desc">
          <slot />
        </div>
      </div>
    </template>
    <template v-else>
      <div class="seo-step-flow__card">
        <span class="seo-step-flow__index" aria-hidden="true">{{ stepNumber }}</span>
        <div class="seo-step-flow__body">
          <slot />
        </div>
      </div>
      <div class="seo-step-flow__connector" aria-hidden="true">
        <svg
          class="seo-step-flow__arrow"
          width="22"
          height="22"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12 5v12M7 14l5 5 5-5"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </div>
    </template>
  </li>
</template>
