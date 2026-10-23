<script setup>
/** Изменение со стрелкой и знаком — направление никогда не передаётся только цветом. */
import { computed } from 'vue'
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-vue-next'
import { pct, money, moneyCompact } from '../format'

const props = defineProps({
  value: { type: Number, default: 0 },
  kind: { type: String, default: 'pct' }, // pct | money | compact
  pill: { type: Boolean, default: true },
  digits: { type: Number, default: 1 },
})

const dir = computed(() => (props.value > 0 ? 1 : props.value < 0 ? -1 : 0))
const label = computed(() => {
  if (props.kind === 'money') return money(props.value, { sign: true })
  if (props.kind === 'compact') return moneyCompact(props.value, { sign: true })
  return pct(props.value, { digits: props.digits })
})
const icon = computed(() => (dir.value > 0 ? ArrowUpRight : dir.value < 0 ? ArrowDownRight : Minus))
</script>

<template>
  <span
    class="cv-num"
    :class="[pill ? 'cv-delta' : 'cv-delta-inline', { 'is-up': dir > 0, 'is-down': dir < 0 }]"
  >
    <component :is="icon" :size="pill ? 13 : 14" :stroke-width="2.4" aria-hidden="true" />
    {{ label }}
  </span>
</template>

<style scoped>
.cv-delta-inline {
  display: inline-flex; align-items: center; gap: 2px;
  font-weight: 600; color: var(--cv-ink-2); white-space: nowrap;
}
.cv-delta-inline.is-up { color: var(--cv-up); }
.cv-delta-inline.is-down { color: var(--cv-down); }
</style>
