<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { Calendar, ChevronDown } from 'lucide-vue-next'
import { normalizeDateToString, formatDateForDisplay } from '../../utils/date'
import CustomSelect from './CustomSelect.vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: '',
  },
  max: {
    type: String,
    default: null,
  },
  min: {
    type: String,
    default: null,
  },
  required: {
    type: Boolean,
    default: false,
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  placeholder: {
    type: String,
    default: '',
  },
  id: {
    type: String,
    default: '',
  },
  name: {
    type: String,
    default: '',
  },
  class: {
    type: String,
    default: '',
  },
  /** Только панель календаря (без поля и телепорта) — для PeriodFilter */
  inlinePanel: {
    type: Boolean,
    default: false,
  },
  /** Для inlinePanel: позиционирование (fixed top/left и т.д.) */
  style: {
    type: [String, Object],
    default: undefined,
  },
  /** Подсветка диапазона (YYYY-MM-DD) */
  rangeStart: {
    type: String,
    default: '',
  },
  rangeEnd: {
    type: String,
    default: '',
  },
  selectBoundMax: {
    type: String,
    default: '',
  },
  selectBoundMin: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue', 'layout-change'])

const MONTHS_FULL = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const MONTHS_SHORT = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']

const CALENDAR_WIDTH = 280
const POPOVER_GAP = 8
/** Выше панели календаря (z-index 10001), чтобы список лет не уходил под неё */
const YEAR_DROPDOWN_Z = 10120

const parseLocalDay = (str) => {
  if (!str) return null
  const d = new Date(str + 'T00:00:00')
  return isNaN(d.getTime()) ? null : d
}

const maxDate = computed(() => {
  if (props.max !== null && props.max !== undefined) {
    const normalized = normalizeDateToString(props.max)
    return normalized || props.max
  }
  return normalizeDateToString(new Date()) || ''
})

const minDate = computed(() => {
  if (props.min !== null && props.min !== undefined && props.min !== '') {
    const normalized = normalizeDateToString(props.min)
    return normalized || undefined
  }
  return undefined
})

const triggerClass = computed(() => {
  const base = 'di-date-trigger'
  return props.class ? `${base} ${props.class}` : base
})

const displayValue = computed(() => formatDateForDisplay(props.modelValue))

function clampModelToBounds() {
  const v = props.modelValue
  if (!v) return
  const n = normalizeDateToString(v)
  if (!n) return
  if (minDate.value && n < minDate.value) {
    emit('update:modelValue', minDate.value)
    return
  }
  if (maxDate.value && n > maxDate.value) {
    emit('update:modelValue', maxDate.value)
  }
}

watch(() => props.min, (newMin, oldMin) => {
  if (newMin && props.modelValue && oldMin !== undefined) {
    clampModelToBounds()
  }
})

watch(() => props.modelValue, () => {
  clampModelToBounds()
}, { immediate: true })

// --- grid ---
const calYear = ref(new Date().getFullYear())
const calMonth = ref(new Date().getMonth())

const syncGridMonthFromModel = () => {
  const p = parseLocalDay(props.modelValue)
    || parseLocalDay(props.min)
    || new Date()
  calYear.value = p.getFullYear()
  calMonth.value = p.getMonth()
}

watch(
  () => [props.modelValue, props.min],
  () => {
    syncGridMonthFromModel()
  },
  { immediate: true }
)

const calDays = computed(() => {
  const y = calYear.value
  const m = calMonth.value
  const first = new Date(y, m, 1)
  let dow = first.getDay()
  if (dow === 0) dow = 7
  dow--
  const dim = new Date(y, m + 1, 0).getDate()
  const prevDim = new Date(y, m, 0).getDate()
  const days = []
  for (let i = dow - 1; i >= 0; i--) {
    days.push({ day: prevDim - i, cur: false, date: new Date(y, m - 1, prevDim - i) })
  }
  for (let d = 1; d <= dim; d++) {
    days.push({ day: d, cur: true, date: new Date(y, m, d) })
  }
  const rem = (7 - (days.length % 7)) % 7
  for (let d = 1; d <= rem; d++) {
    days.push({ day: d, cur: false, date: new Date(y, m + 1, d) })
  }
  /* Всегда 6 недель (42 ячейки), чтобы высота панели не прыгала между месяцами */
  const CELLS = 42
  while (days.length < CELLS) {
    const prev = days[days.length - 1]
    const next = new Date(prev.date.getFullYear(), prev.date.getMonth(), prev.date.getDate() + 1)
    days.push({ day: next.getDate(), cur: false, date: next })
  }
  return days
})

const rangeLo = computed(() => parseLocalDay(props.rangeStart))
const rangeHi = computed(() => parseLocalDay(props.rangeEnd))

const isInRange = (d) => {
  const lo = rangeLo.value
  const hi = rangeHi.value
  if (!lo || !hi) return false
  const t = d.getTime()
  return t >= lo.getTime() && t <= hi.getTime()
}

const isRangeStart = (d) => !!props.rangeStart && normalizeDateToString(d) === props.rangeStart
const isRangeEnd = (d) => !!props.rangeEnd && normalizeDateToString(d) === props.rangeEnd

const showRangeHighlight = computed(() => !!(props.rangeStart && props.rangeEnd))

const isSelectedSingle = (d) => {
  if (showRangeHighlight.value) return false
  if (!props.modelValue) return false
  return normalizeDateToString(d) === normalizeDateToString(props.modelValue)
}

const isDayDisabled = (d, cur) => {
  if (!cur) return true
  const ymd = normalizeDateToString(d)
  if (!ymd) return true
  if (minDate.value && ymd < minDate.value) return true
  if (maxDate.value && ymd > maxDate.value) return true
  if (props.selectBoundMax && ymd > props.selectBoundMax) return true
  if (props.selectBoundMin && ymd < props.selectBoundMin) return true
  return false
}

const pickDay = (date) => {
  const ymd = normalizeDateToString(date)
  if (!ymd) return
  emit('update:modelValue', ymd)
  if (!props.inlinePanel) {
    open.value = false
  }
}

const afterMonthNav = () => {
  nextTick(() => {
    if (props.inlinePanel) {
      emit('layout-change')
    } else {
      positionPopover()
    }
  })
}

const calPrev = () => {
  monthYearOpen.value = false
  calMonth.value--
  if (calMonth.value < 0) {
    calMonth.value = 11
    calYear.value--
  }
  afterMonthNav()
}

const calNext = () => {
  monthYearOpen.value = false
  calMonth.value++
  if (calMonth.value > 11) {
    calMonth.value = 0
    calYear.value++
  }
  afterMonthNav()
}

/** Границы списка лет: min/max пропсы, запас вокруг «сегодня» и вокруг выбранной даты */
const yearBounds = computed(() => {
  const nowY = new Date().getFullYear()
  let yMin = nowY - 120
  let yMax = nowY + 20
  if (minDate.value) {
    const y = parseInt(minDate.value.slice(0, 4), 10)
    if (!Number.isNaN(y)) yMin = Math.max(yMin, y)
  }
  if (maxDate.value) {
    const y = parseInt(maxDate.value.slice(0, 4), 10)
    if (!Number.isNaN(y)) yMax = Math.min(yMax, y)
  }
  const mv = parseLocalDay(props.modelValue)
  if (mv) {
    const y = mv.getFullYear()
    yMin = Math.min(yMin, y)
    yMax = Math.max(yMax, y)
  }
  if (yMin > yMax) return { yMin: yMax, yMax }
  return { yMin, yMax }
})

const yearOptions = computed(() => {
  const { yMin, yMax } = yearBounds.value
  const list = []
  for (let y = yMax; y >= yMin; y--) list.push(y)
  return list
})

const onCalYearSelect = (v) => {
  const y = typeof v === 'number' ? v : Number(v)
  if (Number.isNaN(y)) return
  calYear.value = y
  afterMonthNav()
}

/** Режим выбора месяца/года (классический календарь) */
const monthYearOpen = ref(false)

const toggleMonthYear = () => {
  monthYearOpen.value = !monthYearOpen.value
  afterMonthNav()
}

const isMonthFullyDisabled = (monthIdx) => {
  const y = calYear.value
  const dim = new Date(y, monthIdx + 1, 0).getDate()
  for (let d = 1; d <= dim; d++) {
    const dt = new Date(y, monthIdx, d)
    if (!isDayDisabled(dt, true)) return false
  }
  return true
}

const pickMonthFromSheet = (monthIdx) => {
  if (isMonthFullyDisabled(monthIdx)) return
  calMonth.value = monthIdx
  monthYearOpen.value = false
  afterMonthNav()
}

watch(yearBounds, (b) => {
  if (calYear.value < b.yMin) calYear.value = b.yMin
  if (calYear.value > b.yMax) calYear.value = b.yMax
}, { immediate: true })

const gridRootClass = computed(() => props.class || undefined)

// --- picker popover ---
const open = ref(false)
const wrapperRef = ref(null)
const triggerRef = ref(null)
const popoverRef = ref(null)
const popoverStyle = ref({})

let popoverCleanup = null

const positionPopover = () => {
  const t = triggerRef.value
  const p = popoverRef.value
  if (!t || !p) return
  const tr = t.getBoundingClientRect()
  const ph = p.getBoundingClientRect().height || 318
  const vw = window.innerWidth
  const vh = window.innerHeight
  let left = tr.left
  let top = tr.bottom + POPOVER_GAP
  if (top + ph > vh - 8) {
    top = tr.top - ph - POPOVER_GAP
  }
  if (left + CALENDAR_WIDTH > vw - 8) {
    left = vw - CALENDAR_WIDTH - 8
  }
  if (left < 8) left = 8
  if (top < 8) top = 8
  if (top + ph > vh - 8) {
    top = Math.max(8, vh - ph - 8)
  }
  popoverStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    width: `${CALENDAR_WIDTH}px`,
    zIndex: 10001,
  }
}

const detachPopoverListeners = () => {
  popoverCleanup?.()
  popoverCleanup = null
}

const attachPopoverListeners = () => {
  detachPopoverListeners()
  const onScroll = () => nextTick(positionPopover)
  window.addEventListener('scroll', onScroll, true)
  window.addEventListener('resize', onScroll)
  popoverCleanup = () => {
    window.removeEventListener('scroll', onScroll, true)
    window.removeEventListener('resize', onScroll)
  }
}

const onDocPointerDown = (e) => {
  const el = e.target
  if (!(el instanceof Node)) return
  if (!open.value) return
  if (el instanceof Element && el.closest('.custom-select-dropdown')) return
  if (wrapperRef.value?.contains(el)) return
  if (popoverRef.value?.contains(el)) return
  open.value = false
}

const onKeydown = (e) => {
  if (e.key !== 'Escape') return
  if (monthYearOpen.value) {
    monthYearOpen.value = false
    e.preventDefault()
    return
  }
  if (open.value) open.value = false
}

const toggleOpen = () => {
  if (props.disabled) return
  open.value = !open.value
  if (open.value) {
    monthYearOpen.value = false
    syncGridMonthFromModel()
    nextTick(() => {
      positionPopover()
      attachPopoverListeners()
      nextTick(() => positionPopover())
    })
  } else {
    detachPopoverListeners()
  }
}

watch(open, (v) => {
  if (!v) {
    detachPopoverListeners()
    monthYearOpen.value = false
  }
})

onMounted(() => {
  document.addEventListener('mousedown', onDocPointerDown, true)
  document.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onDocPointerDown, true)
  document.removeEventListener('keydown', onKeydown)
  detachPopoverListeners()
})
</script>

<template>
  <div
    v-if="!inlinePanel"
    ref="wrapperRef"
    class="di-date-field"
  >
    <button
      :id="id"
      type="button"
      ref="triggerRef"
      :class="triggerClass"
      :disabled="disabled"
      :aria-expanded="open"
      aria-haspopup="dialog"
      :aria-required="required"
      @click="toggleOpen"
    >
      <span
        class="di-date-field__text"
        :class="{ 'di-date-field__text--placeholder': !displayValue }"
      >{{ displayValue || placeholder || 'Выберите дату' }}</span>
      <Calendar class="di-date-field__icon" :size="18" stroke-width="2" aria-hidden="true" />
    </button>
    <input
      v-if="name"
      type="hidden"
      :name="name"
      :value="modelValue"
    >
    <Teleport to="body">
      <div
        v-if="open"
        ref="popoverRef"
        class="di-calendar-panel di-date-popover"
        :style="popoverStyle"
        role="dialog"
        aria-modal="false"
        @click.stop
        @mousedown.stop
      >
        <div class="di-cal-header">
          <button type="button" class="di-cal-nav" @click="calPrev">&#8249;</button>
          <button
            type="button"
            class="di-cal-title-btn"
            :aria-expanded="monthYearOpen"
            aria-haspopup="dialog"
            @click="toggleMonthYear"
          >
            <span class="di-cal-title-btn__label">{{ MONTHS_FULL[calMonth] }} {{ calYear }}</span>
            <ChevronDown
              class="di-cal-title-chevron"
              :class="{ 'di-cal-title-chevron--open': monthYearOpen }"
              :size="18"
              stroke-width="2"
              aria-hidden="true"
            />
          </button>
          <button type="button" class="di-cal-nav" @click="calNext">&#8250;</button>
        </div>
        <div class="di-cal-body">
          <div v-show="!monthYearOpen" class="di-cal-grid">
            <span v-for="dn in DAY_NAMES" :key="dn" class="di-cal-dn">{{ dn }}</span>
            <span
              v-for="(cell, i) in calDays"
              :key="i"
              class="di-cal-day"
              :class="{
                other: !cell.cur,
                disabled: isDayDisabled(cell.date, cell.cur),
                'in-range': cell.cur && !isDayDisabled(cell.date, cell.cur) && isInRange(cell.date),
                'range-start': cell.cur && !isDayDisabled(cell.date, cell.cur) && (isRangeStart(cell.date) || isSelectedSingle(cell.date)),
                'range-end': cell.cur && !isDayDisabled(cell.date, cell.cur) && isRangeEnd(cell.date),
              }"
              @click="cell.cur && !isDayDisabled(cell.date, cell.cur) && pickDay(cell.date)"
            >{{ cell.day }}</span>
          </div>
          <div
            v-if="monthYearOpen"
            class="di-cal-month-year"
            role="group"
            aria-label="Месяц и год"
          >
            <div class="di-cal-year-wrap">
              <CustomSelect
                :model-value="calYear"
                :options="yearOptions"
                :show-empty-option="false"
                min-width="100%"
                flex="1"
                compact
                :dropdown-z-index="YEAR_DROPDOWN_Z"
                @update:model-value="onCalYearSelect"
              />
            </div>
            <div class="di-cal-months-grid">
              <button
                v-for="(m, idx) in MONTHS_SHORT"
                :key="idx"
                type="button"
                class="di-cal-month-cell"
                :class="{
                  'di-cal-month-cell--current': idx === calMonth,
                  'di-cal-month-cell--disabled': isMonthFullyDisabled(idx),
                }"
                :disabled="isMonthFullyDisabled(idx)"
                @click="pickMonthFromSheet(idx)"
              >{{ m }}</button>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
  <div
    v-else
    class="di-calendar-panel"
    :class="gridRootClass"
    :style="props.style"
    @click.stop
    @mousedown.stop
  >
    <div class="di-cal-header">
      <button type="button" class="di-cal-nav" @click="calPrev">&#8249;</button>
      <button
        type="button"
        class="di-cal-title-btn"
        :aria-expanded="monthYearOpen"
        aria-haspopup="dialog"
        @click="toggleMonthYear"
      >
        <span class="di-cal-title-btn__label">{{ MONTHS_FULL[calMonth] }} {{ calYear }}</span>
        <ChevronDown
          class="di-cal-title-chevron"
          :class="{ 'di-cal-title-chevron--open': monthYearOpen }"
          :size="18"
          stroke-width="2"
          aria-hidden="true"
        />
      </button>
      <button type="button" class="di-cal-nav" @click="calNext">&#8250;</button>
    </div>
    <div class="di-cal-body">
      <div v-show="!monthYearOpen" class="di-cal-grid">
        <span v-for="dn in DAY_NAMES" :key="dn" class="di-cal-dn">{{ dn }}</span>
        <span
          v-for="(cell, i) in calDays"
          :key="i"
          class="di-cal-day"
          :class="{
            other: !cell.cur,
            disabled: isDayDisabled(cell.date, cell.cur),
            'in-range': cell.cur && !isDayDisabled(cell.date, cell.cur) && isInRange(cell.date),
            'range-start': cell.cur && !isDayDisabled(cell.date, cell.cur) && (isRangeStart(cell.date) || isSelectedSingle(cell.date)),
            'range-end': cell.cur && !isDayDisabled(cell.date, cell.cur) && isRangeEnd(cell.date),
          }"
          @click="cell.cur && !isDayDisabled(cell.date, cell.cur) && pickDay(cell.date)"
        >{{ cell.day }}</span>
      </div>
      <div
        v-if="monthYearOpen"
        class="di-cal-month-year"
        role="group"
        aria-label="Месяц и год"
      >
        <div class="di-cal-year-wrap">
          <CustomSelect
            :model-value="calYear"
            :options="yearOptions"
            :show-empty-option="false"
            min-width="100%"
            flex="1"
            compact
            :dropdown-z-index="YEAR_DROPDOWN_Z"
            @update:model-value="onCalYearSelect"
          />
        </div>
        <div class="di-cal-months-grid">
          <button
            v-for="(m, idx) in MONTHS_SHORT"
            :key="idx"
            type="button"
            class="di-cal-month-cell"
            :class="{
              'di-cal-month-cell--current': idx === calMonth,
              'di-cal-month-cell--disabled': isMonthFullyDisabled(idx),
            }"
            :disabled="isMonthFullyDisabled(idx)"
            @click="pickMonthFromSheet(idx)"
          >{{ m }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.di-date-field {
  width: 100%;
}

.di-date-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 9px 12px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  transition: all 0.2s ease;
  background: #fff;
  color: #111827;
  box-sizing: border-box;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
}

.di-date-trigger:hover:not(:disabled) {
  border-color: #d1d5db;
  background: #fafafa;
}

.di-date-trigger:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: #fff;
}

.di-date-trigger:disabled {
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
}

.di-date-field__text {
  min-width: 0;
  flex: 1;
}

.di-date-field__text--placeholder {
  color: #9ca3af;
}

.di-date-field__icon {
  flex-shrink: 0;
  color: #6b7280;
}

.di-calendar-panel {
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.06);
  padding: 14px;
  width: 280px;
  box-sizing: border-box;
  animation: di-cal-in 0.15s ease;
  overflow: visible;
}

@keyframes di-cal-in {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.di-cal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 4px;
  margin-bottom: 10px;
}

.di-cal-title-btn {
  flex: 1;
  min-width: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 6px;
  margin: 0 2px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-family: inherit;
  font-weight: 600;
  font-size: 14px;
  color: #111827;
  cursor: pointer;
  transition: background 0.15s;
}

.di-cal-title-btn:hover {
  background: #f3f4f6;
}

.di-cal-title-btn:focus {
  outline: none;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.25);
  border-radius: 8px;
}

.di-cal-title-btn__label {
  text-align: center;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.di-cal-title-chevron {
  flex-shrink: 0;
  color: #6b7280;
  transition: transform 0.2s ease;
}

.di-cal-title-chevron--open {
  transform: rotate(180deg);
}

.di-cal-body {
  min-height: 248px;
  overflow: visible;
}

.di-cal-month-year {
  padding-top: 2px;
  overflow: visible;
}

.di-cal-year-wrap {
  width: 100%;
}

.di-cal-year-wrap :deep(.custom-select-wrapper) {
  min-width: 0 !important;
  width: 100%;
  max-width: 100%;
}

.di-cal-year-wrap :deep(.custom-select-value) {
  font-variant-numeric: tabular-nums;
}

.di-cal-months-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-top: 12px;
}

.di-cal-month-cell {
  padding: 10px 4px;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #fff;
  font-size: 13px;
  font-weight: 500;
  font-family: inherit;
  color: #374151;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.di-cal-month-cell:hover:not(:disabled) {
  border-color: #d1d5db;
  background: #fafafa;
}

.di-cal-month-cell--current {
  border-color: #2563eb;
  color: #2563eb;
  background: #eff6ff;
}

.di-cal-month-cell--current:hover:not(:disabled) {
  background: #dbeafe;
}

.di-cal-month-cell--disabled,
.di-cal-month-cell:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.di-cal-nav {
  background: none;
  border: none;
  font-size: 20px;
  color: #6b7280;
  cursor: pointer;
  padding: 4px 10px;
  border-radius: 6px;
  line-height: 1;
  transition: all 0.15s;
  font-family: inherit;
}
.di-cal-nav:hover {
  background: #f3f4f6;
  color: #374151;
}

.di-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  grid-template-rows: auto repeat(6, 32px);
  gap: 1px;
  text-align: center;
  align-items: stretch;
}

.di-cal-dn {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 600;
  padding: 4px 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.di-cal-day {
  font-size: 13px;
  padding: 0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s;
  color: #374151;
  user-select: none;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 32px;
  box-sizing: border-box;
}
.di-cal-day:hover {
  background: #f3f4f6;
}
.di-cal-day.other {
  color: #d1d5db;
  cursor: default;
}
.di-cal-day.other:hover {
  background: transparent;
}
.di-cal-day.disabled {
  color: #e5e7eb;
  cursor: not-allowed;
  pointer-events: none;
}
.di-cal-day.disabled:hover {
  background: transparent;
}
.di-cal-day.in-range {
  background: #eff6ff;
  color: #2563eb;
}
.di-cal-day.range-start,
.di-cal-day.range-end {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}
.di-cal-day.range-start:hover,
.di-cal-day.range-end:hover {
  background: #1d4ed8;
}
</style>
