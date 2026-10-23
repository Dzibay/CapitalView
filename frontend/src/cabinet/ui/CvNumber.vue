<script setup>
/**
 * «Одометр»: каждая цифра — колонка 0–9, которая прокручивается к новому значению.
 * Разряды выровнены по правому краю, поэтому при смене длины числа колонки не прыгают.
 * В приватном режиме показывается маска (formatter сам возвращает «••••• ₽»).
 */
import { computed, onMounted, ref } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  format: { type: Function, required: true },
  /** при монтировании «прокрутить» от нуля */
  intro: { type: Boolean, default: true },
  stagger: { type: Number, default: 28 },
  /** длительность прокрутки, мс (при наведении на график — короче) */
  duration: { type: Number, default: 1100 },
  /** приглушить дробную часть и единицы (₽, %, млн) — для крупных чисел */
  dim: { type: Boolean, default: false },
})

const DIGITS = '0123456789'
const ready = ref(!props.intro)

const text = computed(() => props.format(props.value))

const chars = computed(() => {
  const list = [...text.value]
  const n = list.length
  let unitFrom = n
  let fracFrom = n
  if (props.dim) {
    // единицы — всё после последней цифры (или точки маски), дробь — от запятой до единиц
    let last = -1
    list.forEach((ch, i) => { if (DIGITS.includes(ch) || ch === '•') last = i })
    unitFrom = last + 1
    const comma = list.lastIndexOf(',', last)
    if (comma > 0 && DIGITS.includes(list[comma - 1] || '')) fracFrom = comma
    else fracFrom = unitFrom
  }
  return list.map((ch, i) => ({
    ch,
    digit: DIGITS.includes(ch) ? Number(ch) : -1,
    // ключ от правого края: разряд единиц всегда один и тот же элемент
    key: `${n - i}`,
    order: n - i,
    part: i >= unitFrom ? 'unit' : i >= fracFrom ? 'frac' : '',
  }))
})

onMounted(() => {
  if (ready.value) return
  requestAnimationFrame(() => requestAnimationFrame(() => { ready.value = true }))
})
</script>

<template>
  <span class="cv-odo cv-num" :aria-label="text" role="text">
    <span
      v-for="c in chars"
      :key="c.key"
      class="cv-odo__cell"
      :class="[{ 'is-digit': c.digit >= 0 }, c.part && `is-${c.part}`]"
      aria-hidden="true"
    >
      <template v-if="c.digit >= 0">
        <span
          class="cv-odo__strip"
          :style="{
            transform: `translateY(${-(ready ? c.digit : 0) * 10}%)`,
            transitionDelay: `${Math.min(c.order, 14) * stagger}ms`,
            transitionDuration: `${duration}ms`,
          }"
        >
          <span v-for="d in DIGITS" :key="d">{{ d }}</span>
        </span>
        <span class="cv-odo__ghost">{{ c.ch }}</span>
      </template>
      <template v-else>{{ c.ch }}</template>
    </span>
  </span>
</template>

<style scoped>
.cv-odo {
  display: inline-flex;
  align-items: baseline;
  white-space: pre;
  line-height: 1.1;
}
.cv-odo__cell {
  position: relative;
  display: inline-block;
}
.cv-odo__cell.is-frac { opacity: .4; }
.cv-odo__cell.is-unit { opacity: .4; font-size: .66em; font-weight: 500; letter-spacing: 0; }
.cv-odo__cell.is-digit {
  overflow: hidden;
  /* небольшой запас сверху/снизу, чтобы не обрезать выносные элементы */
  padding: .06em 0;
  margin: -.06em 0;
}
/* невидимая цифра задаёт ширину и базовую линию */
.cv-odo__ghost {
  visibility: hidden;
}
.cv-odo__strip {
  position: absolute;
  left: 0;
  right: 0;
  top: .06em;
  display: flex;
  flex-direction: column;
  text-align: center;
  transition: transform 1.1s cubic-bezier(.16, 1, .3, 1);
  will-change: transform;
}
.cv-odo__strip > span {
  display: block;
  height: 1.1em;
  line-height: 1.1;
}
</style>
