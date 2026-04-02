<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Teleport } from 'vue'
import CustomSelect from './CustomSelect.vue'
import { normalizeDateToString } from '../../utils/date'
import { Calendar } from 'lucide-vue-next'

const props = defineProps({
  preset: { type: String, default: 'all' },
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  /** Левая граница шкалы и выбора — первая дата операции/транзакции (YYYY-MM-DD). Пусто — запас 6 лет назад. */
  trackMinDate: { type: String, default: '' },
  /** Показывать ползунковую шкалу под блоком дат */
  showTrack: { type: Boolean, default: false },
})

const emit = defineEmits(['update:preset', 'update:startDate', 'update:endDate'])

const PRESET_OPTIONS = [
  { value: 'week', label: 'Неделя' },
  { value: 'month', label: 'Месяц' },
  { value: 'quarter', label: 'Квартал' },
  { value: 'year', label: 'Год' },
  { value: 'all', label: 'Всё время' },
]

const MONTHS_SHORT = ['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек']
const MONTHS_FULL = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь']
const DAY_NAMES = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс']
const MS_PER_DAY = 86400000

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))
const addDays = (d, n) => { const r = new Date(d.getTime() + n * MS_PER_DAY); r.setHours(0,0,0,0); return r }
const parseDate = (str) => {
  if (!str) return null
  const d = new Date(str + 'T00:00:00')
  return isNaN(d.getTime()) ? null : d
}

const startOfToday = () => {
  const t = new Date()
  t.setHours(0, 0, 0, 0)
  return t
}

const trackMin = computed(() => {
  const p = parseDate(props.trackMinDate)
  if (p) {
    p.setHours(0, 0, 0, 0)
    return p
  }
  const t = startOfToday()
  return new Date(t.getFullYear() - 6, 0, 1)
})

const trackMax = computed(() => startOfToday())

/** Календарный день в пределах [trackMin, trackMax] */
const clampDayToTrack = (d) => {
  const x = new Date(d.getTime())
  x.setHours(0, 0, 0, 0)
  const lo = trackMin.value.getTime()
  const hi = trackMax.value.getTime()
  if (x.getTime() < lo) return new Date(lo)
  if (x.getTime() > hi) return new Date(hi)
  return x
}

const trackRef = ref(null)
const leftThumbRef = ref(null)
const rightThumbRef = ref(null)
/** Ряд кнопок дат — якорь: календарь строго над этим блоком */
const datesInnerRef = ref(null)
/** Весь блок «Даты» — клик внутри не закрывает попап */
const datesAnchorRef = ref(null)

let calendarRepositionCleanup = null

const visibleStart = ref(new Date(trackMin.value))
const visibleEnd = ref(new Date(trackMax.value))
const selStart = ref(new Date(trackMin.value))
const selEnd = ref(new Date(trackMax.value))

const activeThumb = ref(null)
const isDragging = ref(false)
const dragStartPos = ref(0)
const dragStartTime = ref(0)
const lastClientX = ref(0)
const expandTimer = ref(null)
const noTransition = ref(false)

const calendarTarget = ref(null)
const _t0 = startOfToday()
const calYear = ref(_t0.getFullYear())
const calMonth = ref(_t0.getMonth())
const calendarStyle = ref({})

let lastAppliedPreset = null

const daysBetween = (a, b) => Math.round((b - a) / MS_PER_DAY)

const dateToFrac = (date) => {
  const total = visibleEnd.value.getTime() - visibleStart.value.getTime()
  if (total <= 0) return 0
  return clamp((date.getTime() - visibleStart.value.getTime()) / total, 0, 1)
}

const fracToDate = (frac) => {
  const total = visibleEnd.value.getTime() - visibleStart.value.getTime()
  const d = new Date(visibleStart.value.getTime() + frac * total)
  d.setHours(0, 0, 0, 0)
  return clampDayToTrack(d)
}

const fmtCompact = (d) => {
  if (!d || isNaN(d.getTime())) return '—'
  return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth()+1).padStart(2,'0')}.${String(d.getFullYear()).slice(2)}`
}

const fmtShort = (d) => `${d.getDate()} ${MONTHS_SHORT[d.getMonth()]}`

const thumbLeftPct = computed(() => dateToFrac(selStart.value) * 100)
const thumbRightPct = computed(() => dateToFrac(selEnd.value) * 100)

const dateLeftDisplay = computed(() => {
  if (props.preset === 'all') return 'все'
  return fmtCompact(selStart.value)
})
const dateRightDisplay = computed(() => {
  if (props.preset === 'all') return 'время'
  return fmtCompact(selEnd.value)
})

const ticks = computed(() => {
  const vs = visibleStart.value
  const ve = visibleEnd.value
  const days = daysBetween(vs, ve)
  if (days <= 0) return []

  let stepFn, labelFn, alignFn
  if (days <= 14) {
    alignFn = (c) => addDays(c, 1)
    stepFn = (c) => addDays(c, 1)
    labelFn = (d) => String(d.getDate())
  } else if (days <= 40) {
    alignFn = (c) => { return addDays(c, 7 - ((c.getDay() + 6) % 7)) }
    stepFn = (c) => addDays(c, 7)
    labelFn = (d) => fmtShort(d)
  } else if (days <= 120) {
    alignFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 1, 1); r.setHours(0,0,0,0); return r }
    stepFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 1, 1); r.setHours(0,0,0,0); return r }
    labelFn = (d) => MONTHS_SHORT[d.getMonth()]
  } else if (days <= 400) {
    alignFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 1, 1); r.setHours(0,0,0,0); return r }
    stepFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 2, 1); r.setHours(0,0,0,0); return r }
    labelFn = (d) => MONTHS_SHORT[d.getMonth()]
  } else if (days <= 900) {
    alignFn = (c) => {
      const m = c.getMonth()
      const next = m + (3 - m % 3)
      const r = new Date(c.getFullYear(), next, 1); r.setHours(0,0,0,0); return r
    }
    stepFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 3, 1); r.setHours(0,0,0,0); return r }
    labelFn = (d) => `${MONTHS_SHORT[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`
  } else {
    alignFn = (c) => {
      const m = c.getMonth()
      const next = m + (6 - m % 6)
      const r = new Date(c.getFullYear(), next, 1); r.setHours(0,0,0,0); return r
    }
    stepFn = (c) => { const r = new Date(c.getFullYear(), c.getMonth() + 6, 1); r.setHours(0,0,0,0); return r }
    labelFn = (d) => `${MONTHS_SHORT[d.getMonth()]} ${d.getFullYear()}`
  }

  const result = []
  let cursor = alignFn(new Date(vs))
  const maxTicks = 20
  while (cursor <= ve && result.length < maxTicks) {
    const f = dateToFrac(cursor)
    if (f > 0.03 && f < 0.97) {
      result.push({ frac: f, label: labelFn(cursor) })
    }
    cursor = stepFn(cursor)
  }
  return result
})

const presetSelectValue = computed(() => {
  return PRESET_OPTIONS.some(o => o.value === props.preset) ? props.preset : null
})

const handlePresetChange = (val) => {
  if (!val) return
  lastAppliedPreset = val
  applyPreset(val)
}

const applyPreset = (preset) => {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  let start, end

  if (preset === 'week') { start = addDays(now, -7); end = new Date(now) }
  else if (preset === 'month') { start = new Date(now); start.setMonth(start.getMonth() - 1); end = new Date(now) }
  else if (preset === 'quarter') { start = new Date(now); start.setMonth(start.getMonth() - 3); end = new Date(now) }
  else if (preset === 'year') { start = new Date(now); start.setFullYear(start.getFullYear() - 1); end = new Date(now) }
  else { start = null; end = null }

  if (!start) {
    selStart.value = new Date(trackMin.value)
    selEnd.value = new Date(trackMax.value)
    visibleStart.value = new Date(trackMin.value)
    visibleEnd.value = new Date(trackMax.value)
    emit('update:preset', 'all')
    emit('update:startDate', '')
    emit('update:endDate', '')
  } else {
    start = new Date(Math.max(trackMin.value.getTime(), start.getTime()))
    end = new Date(Math.min(trackMax.value.getTime(), end.getTime()))
    if (start.getTime() > end.getTime()) start = new Date(end)
    selStart.value = start
    selEnd.value = end
    const rangeDays = daysBetween(start, end)
    const padL = Math.max(1, Math.round(rangeDays * 0.12))
    const padR = Math.max(1, Math.round(rangeDays * 0.05))
    visibleStart.value = new Date(Math.max(trackMin.value.getTime(), addDays(start, -padL).getTime()))
    visibleEnd.value = new Date(Math.min(trackMax.value.getTime() + MS_PER_DAY, addDays(end, padR).getTime()))
    emit('update:preset', preset)
    emit('update:startDate', normalizeDateToString(start))
    emit('update:endDate', normalizeDateToString(end))
  }
}

const getTrackFrac = (clientX) => {
  if (!trackRef.value) return 0
  const rect = trackRef.value.getBoundingClientRect()
  return clamp((clientX - rect.left) / rect.width, 0, 1)
}

const startDrag = (e, thumb) => {
  e.preventDefault()
  e.stopPropagation()
  const cx = e.touches ? e.touches[0].clientX : e.clientX
  activeThumb.value = thumb
  isDragging.value = false
  noTransition.value = false
  dragStartPos.value = cx
  dragStartTime.value = Date.now()
  lastClientX.value = cx
  calendarTarget.value = null

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', endDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', endDrag)
}

const onDrag = (e) => {
  if (e.cancelable) e.preventDefault()
  const cx = e.touches ? e.touches[0].clientX : e.clientX
  lastClientX.value = cx

  if (!isDragging.value) {
    if (Math.abs(cx - dragStartPos.value) < 4 && Date.now() - dragStartTime.value < 250) return
    isDragging.value = true
    noTransition.value = true
  }

  const frac = getTrackFrac(cx)
  const date = fracToDate(frac)

  if (activeThumb.value === 'left') {
    if (date.getTime() <= selEnd.value.getTime() - MS_PER_DAY) {
      selStart.value = date
      emit('update:startDate', normalizeDateToString(date))
      emit('update:preset', 'custom')
    }
    if (frac < 0.08) startAutoExpand('left')
    else stopAutoExpand()
  } else {
    if (date.getTime() >= selStart.value.getTime() + MS_PER_DAY) {
      selEnd.value = date
      emit('update:endDate', normalizeDateToString(date))
      emit('update:preset', 'custom')
    }
    if (frac > 0.92) startAutoExpand('right')
    else stopAutoExpand()
  }
}

const endDrag = () => {
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', endDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', endDrag)
  stopAutoExpand()

  if (isDragging.value) {
    settleVisibleRange()
  }

  activeThumb.value = null
  isDragging.value = false
  noTransition.value = false
}

const startAutoExpand = (dir) => {
  if (expandTimer.value) return
  expandTimer.value = setInterval(() => {
    const dur = visibleEnd.value.getTime() - visibleStart.value.getTime()
    const exp = dur * 0.03

    if (dir === 'left') {
      visibleStart.value = new Date(Math.max(trackMin.value.getTime(), visibleStart.value.getTime() - exp))
    } else {
      visibleEnd.value = new Date(Math.min(trackMax.value.getTime() + MS_PER_DAY, visibleEnd.value.getTime() + exp))
    }

    const frac = getTrackFrac(lastClientX.value)
    const date = fracToDate(frac)
    if (activeThumb.value === 'left' && date.getTime() <= selEnd.value.getTime() - MS_PER_DAY) {
      selStart.value = date
      emit('update:startDate', normalizeDateToString(date))
    } else if (activeThumb.value === 'right' && date.getTime() >= selStart.value.getTime() + MS_PER_DAY) {
      selEnd.value = date
      emit('update:endDate', normalizeDateToString(date))
    }
  }, 50)
}

const stopAutoExpand = () => {
  if (expandTimer.value) { clearInterval(expandTimer.value); expandTimer.value = null }
}

const settleVisibleRange = () => {
  const dur = selEnd.value.getTime() - selStart.value.getTime()
  const pad = Math.max(MS_PER_DAY, dur * 0.1)
  visibleStart.value = new Date(Math.max(trackMin.value.getTime(), selStart.value.getTime() - pad))
  visibleEnd.value = new Date(Math.min(trackMax.value.getTime() + MS_PER_DAY, selEnd.value.getTime() + pad * 0.4))
}

const onTrackClick = (e) => {
  if (isDragging.value || activeThumb.value) return
  if (calendarTarget.value) { calendarTarget.value = null; return }

  noTransition.value = false
  const frac = getTrackFrac(e.clientX)
  const date = fracToDate(frac)
  const dL = Math.abs(frac - dateToFrac(selStart.value))
  const dR = Math.abs(frac - dateToFrac(selEnd.value))

  if (dL <= dR) {
    if (date.getTime() <= selEnd.value.getTime() - MS_PER_DAY) {
      selStart.value = date
      emit('update:startDate', normalizeDateToString(date))
    }
  } else {
    if (date.getTime() >= selStart.value.getTime() + MS_PER_DAY) {
      selEnd.value = date
      emit('update:endDate', normalizeDateToString(date))
    }
  }
  emit('update:preset', 'custom')
  settleVisibleRange()
}

const CALENDAR_WIDTH = 280
const CALENDAR_EST_HEIGHT = 318
const CALENDAR_GAP = 8

const positionCalendar = () => {
  const el = datesInnerRef.value
  if (!el) return
  const r = el.getBoundingClientRect()
  const vw = window.innerWidth
  const vh = window.innerHeight
  const cw = CALENDAR_WIDTH
  const calEl = typeof document !== 'undefined' ? document.querySelector('.pf-period-calendar-popover') : null
  const ch = calEl?.getBoundingClientRect().height || CALENDAR_EST_HEIGHT
  let left = r.left + r.width / 2 - cw / 2
  let top = r.top - ch - CALENDAR_GAP
  if (top < 8) {
    top = r.bottom + CALENDAR_GAP
  }
  if (left < 8) left = 8
  if (left + cw > vw - 8) left = vw - cw - 8
  if (top + ch > vh - 8) top = Math.max(8, vh - ch - 8)
  calendarStyle.value = {
    position: 'fixed',
    left: `${left}px`,
    top: `${top}px`,
    width: `${cw}px`,
    zIndex: 10001,
  }
}

const detachCalendarReposition = () => {
  calendarRepositionCleanup?.()
  calendarRepositionCleanup = null
}

const attachCalendarReposition = () => {
  detachCalendarReposition()
  const fn = () => nextTick(positionCalendar)
  window.addEventListener('scroll', fn, true)
  window.addEventListener('resize', fn)
  calendarRepositionCleanup = () => {
    window.removeEventListener('scroll', fn, true)
    window.removeEventListener('resize', fn)
  }
}

const showCalendar = (thumb) => {
  calendarTarget.value = thumb
  const targetDate = thumb === 'left' ? selStart.value : selEnd.value
  calYear.value = targetDate.getFullYear()
  calMonth.value = targetDate.getMonth()
  nextTick(() => {
    positionCalendar()
    attachCalendarReposition()
    nextTick(() => positionCalendar())
  })
}

watch(calendarTarget, (v) => {
  if (!v) detachCalendarReposition()
})

const calDays = computed(() => {
  const y = calYear.value, m = calMonth.value
  const first = new Date(y, m, 1)
  let dow = first.getDay(); if (dow === 0) dow = 7; dow--
  const dim = new Date(y, m + 1, 0).getDate()
  const prevDim = new Date(y, m, 0).getDate()
  const days = []
  for (let i = dow - 1; i >= 0; i--) days.push({ day: prevDim - i, cur: false, date: new Date(y, m - 1, prevDim - i) })
  for (let d = 1; d <= dim; d++) days.push({ day: d, cur: true, date: new Date(y, m, d) })
  const rem = (7 - days.length % 7) % 7
  for (let d = 1; d <= rem; d++) days.push({ day: d, cur: false, date: new Date(y, m + 1, d) })
  return days
})

const isInRange = (d) => d >= selStart.value && d <= selEnd.value
const isStart = (d) => normalizeDateToString(d) === normalizeDateToString(selStart.value)
const isEnd = (d) => normalizeDateToString(d) === normalizeDateToString(selEnd.value)

const pickDate = (date) => {
  const raw = new Date(date.getFullYear(), date.getMonth(), date.getDate())
  const day = clampDayToTrack(raw)
  if (calendarTarget.value === 'left') {
    if (day.getTime() <= selEnd.value.getTime()) {
      selStart.value = new Date(day)
      emit('update:startDate', normalizeDateToString(day))
    }
  } else {
    if (day.getTime() >= selStart.value.getTime()) {
      selEnd.value = new Date(day)
      emit('update:endDate', normalizeDateToString(day))
    }
  }
  emit('update:preset', 'custom')
  calendarTarget.value = null
  settleVisibleRange()
}

const isCalDayDisabled = (d, cur) => {
  if (!cur) return true
  const day = new Date(d.getFullYear(), d.getMonth(), d.getDate())
  day.setHours(0, 0, 0, 0)
  if (day.getTime() < trackMin.value.getTime() || day.getTime() > trackMax.value.getTime()) return true
  if (calendarTarget.value === 'left' && day.getTime() > selEnd.value.getTime()) return true
  if (calendarTarget.value === 'right' && day.getTime() < selStart.value.getTime()) return true
  return false
}

const calPrev = () => {
  calMonth.value--
  if (calMonth.value < 0) { calMonth.value = 11; calYear.value-- }
  nextTick(() => positionCalendar())
}
const calNext = () => {
  calMonth.value++
  if (calMonth.value > 11) { calMonth.value = 0; calYear.value++ }
  nextTick(() => positionCalendar())
}

watch(() => props.preset, (val) => {
  if (val === lastAppliedPreset) { lastAppliedPreset = null; return }
  if (val && val !== 'custom') applyPreset(val)
  if (val === 'custom') {
    nextTick(() => {
      const s = parseDate(props.startDate)
      const e = parseDate(props.endDate)
      if (s) selStart.value = clampDayToTrack(s)
      if (e) selEnd.value = clampDayToTrack(e)
      if (s || e) settleVisibleRange()
    })
  }
})

watch(
  () => props.trackMinDate,
  () => {
    nextTick(() => {
      const mi = trackMin.value
      const ma = trackMax.value
      if (selStart.value.getTime() < mi.getTime()) {
        selStart.value = new Date(mi)
        if (props.preset !== 'all') emit('update:startDate', normalizeDateToString(selStart.value))
      }
      if (selEnd.value.getTime() > ma.getTime()) {
        selEnd.value = new Date(ma)
        if (props.preset !== 'all') emit('update:endDate', normalizeDateToString(selEnd.value))
      }
      if (selEnd.value.getTime() < selStart.value.getTime()) {
        selEnd.value = new Date(selStart.value)
        if (props.preset !== 'all') emit('update:endDate', normalizeDateToString(selEnd.value))
      }
      if (visibleStart.value.getTime() < mi.getTime()) visibleStart.value = new Date(mi)
      if (visibleEnd.value.getTime() > ma.getTime() + MS_PER_DAY) {
        visibleEnd.value = new Date(ma.getTime() + MS_PER_DAY)
      }
    })
  }
)

watch([() => props.startDate, () => props.endDate], ([ns, ne]) => {
  if (props.preset !== 'custom') return
  const s = parseDate(ns)
  const e = parseDate(ne)
  let changed = false
  if (s && normalizeDateToString(s) !== normalizeDateToString(selStart.value)) { selStart.value = clampDayToTrack(s); changed = true }
  if (e && normalizeDateToString(e) !== normalizeDateToString(selEnd.value)) { selEnd.value = clampDayToTrack(e); changed = true }
  if (changed) settleVisibleRange()
})

const handleDocClick = (e) => {
  if (!calendarTarget.value) return
  const cal = document.querySelector('.pf-period-calendar-popover')
  if (cal?.contains(e.target)) return
  if (datesAnchorRef.value?.contains(e.target)) return
  calendarTarget.value = null
}

onMounted(() => {
  document.addEventListener('mousedown', handleDocClick, true)
  if (props.preset && props.preset !== 'custom') {
    applyPreset(props.preset)
  } else if (props.startDate || props.endDate) {
    const s = parseDate(props.startDate)
    const e = parseDate(props.endDate)
    if (s) selStart.value = clampDayToTrack(s)
    if (e) selEnd.value = clampDayToTrack(e)
    settleVisibleRange()
  }
})

onUnmounted(() => {
  document.removeEventListener('mousedown', handleDocClick, true)
  stopAutoExpand()
  detachCalendarReposition()
})
</script>

<template>
  <div class="period-filter">
    <div class="pf-controls">
      <CustomSelect
        :modelValue="presetSelectValue"
        :options="PRESET_OPTIONS"
        label="Период"
        placeholder="Произвольный"
        :show-empty-option="false"
        min-width="145px"
        flex="0 0 auto"
        @change="handlePresetChange"
      />
      <div ref="datesAnchorRef" class="pf-dates" :class="{ 'pf-dates--all': preset === 'all' }">
        <span class="pf-dates-label">Даты</span>
        <div ref="datesInnerRef" class="pf-dates-inner">
          <button
            type="button"
            class="pf-date-chip"
            :class="{ active: calendarTarget === 'left' }"
            @click.stop="showCalendar('left')"
          >
            <Calendar class="pf-date-chip-icon" :size="15" stroke-width="2" aria-hidden="true" />
            <span class="pf-date-chip-text">{{ dateLeftDisplay }}</span>
          </button>
          <span class="pf-dates-divider" aria-hidden="true" />
          <button
            type="button"
            class="pf-date-chip"
            :class="{ active: calendarTarget === 'right' }"
            @click.stop="showCalendar('right')"
          >
            <Calendar class="pf-date-chip-icon" :size="15" stroke-width="2" aria-hidden="true" />
            <span class="pf-date-chip-text">{{ dateRightDisplay }}</span>
          </button>
        </div>
      </div>
      <div v-if="$slots['controls-suffix']" class="pf-controls-suffix">
        <slot name="controls-suffix" />
      </div>
    </div>

    <div v-show="showTrack" class="pf-slider-area">
      <div
        ref="trackRef"
        class="pf-track-wrap"
        @mousedown.prevent="onTrackClick"
      >
        <div class="pf-track"></div>
        <div
          class="pf-range"
          :class="{ 'no-transition': noTransition }"
          :style="{ left: thumbLeftPct + '%', width: (thumbRightPct - thumbLeftPct) + '%' }"
        ></div>
        <div
          ref="leftThumbRef"
          class="pf-thumb"
          :class="{ 'no-transition': noTransition, active: activeThumb === 'left' }"
          :style="{ left: thumbLeftPct + '%' }"
          @mousedown.stop="startDrag($event, 'left')"
          @touchstart.stop="startDrag($event, 'left')"
        ></div>
        <div
          ref="rightThumbRef"
          class="pf-thumb"
          :class="{ 'no-transition': noTransition, active: activeThumb === 'right' }"
          :style="{ left: thumbRightPct + '%' }"
          @mousedown.stop="startDrag($event, 'right')"
          @touchstart.stop="startDrag($event, 'right')"
        ></div>
      </div>

      <div class="pf-ticks">
        <span
          v-for="(t, i) in ticks"
          :key="i"
          class="pf-tick"
          :style="{ left: (t.frac * 100) + '%' }"
        >
          <span class="pf-tick-mark"></span>
          <span class="pf-tick-label">{{ t.label }}</span>
        </span>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="calendarTarget"
        class="pf-calendar pf-period-calendar-popover"
        :style="calendarStyle"
        @click.stop
        @mousedown.stop
      >
        <div class="pf-cal-header">
          <button class="pf-cal-nav" @click="calPrev">&#8249;</button>
          <span class="pf-cal-title">{{ MONTHS_FULL[calMonth] }} {{ calYear }}</span>
          <button class="pf-cal-nav" @click="calNext">&#8250;</button>
        </div>
        <div class="pf-cal-grid">
          <span v-for="dn in DAY_NAMES" :key="dn" class="pf-cal-dn">{{ dn }}</span>
          <span
            v-for="(d, i) in calDays"
            :key="i"
            class="pf-cal-day"
            :class="{
              'other': !d.cur,
              'disabled': isCalDayDisabled(d.date, d.cur),
              'in-range': d.cur && !isCalDayDisabled(d.date, d.cur) && isInRange(d.date),
              'range-start': d.cur && !isCalDayDisabled(d.date, d.cur) && isStart(d.date),
              'range-end': d.cur && !isCalDayDisabled(d.date, d.cur) && isEnd(d.date),
            }"
            @click="d.cur && !isCalDayDisabled(d.date, d.cur) && pickDate(d.date)"
          >{{ d.day }}</span>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.period-filter {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pf-controls {
  display: flex;
  align-items: flex-end;
  gap: 14px;
  flex-wrap: wrap;
}

.pf-controls-suffix {
  display: flex;
  align-items: center;
  align-self: flex-end;
  min-height: 42px;
  flex-shrink: 0;
}

.pf-controls-suffix :deep(.toggle-switch) {
  margin-bottom: 0;
}

/* Блок дат в стиле CustomSelect / полей формы страницы */
.pf-dates {
  position: relative;
  flex-shrink: 0;
}

.pf-dates-label {
  position: absolute;
  top: -8px;
  left: 12px;
  font-size: 11px;
  font-weight: 600;
  color: #6b7280;
  background: #fff;
  padding: 0 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  z-index: 2;
  pointer-events: none;
  line-height: 1;
}

.pf-dates-inner {
  display: flex;
  align-items: stretch;
  min-height: 42px;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.pf-dates:focus-within .pf-dates-inner,
.pf-dates-inner:hover {
  border-color: #d1d5db;
}

.pf-dates:focus-within .pf-dates-inner {
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.pf-dates-divider {
  width: 1px;
  align-self: stretch;
  margin: 8px 0;
  background: linear-gradient(180deg, transparent, #e5e7eb 15%, #e5e7eb 85%, transparent);
  flex-shrink: 0;
}

.pf-date-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1 1 0;
  min-width: 0;
  padding: 8px 14px;
  border: none;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  color: #111827;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.pf-date-chip-text {
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.02em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pf-date-chip-icon {
  flex-shrink: 0;
  color: #9ca3af;
  transition: color 0.15s ease;
}

.pf-date-chip:hover {
  background: #f9fafb;
  color: #2563eb;
}

.pf-date-chip:hover .pf-date-chip-icon {
  color: #3b82f6;
}

.pf-date-chip.active {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fafc 100%);
  color: #2563eb;
}

.pf-date-chip.active .pf-date-chip-icon {
  color: #2563eb;
}

.pf-dates--all .pf-date-chip-text {
  font-weight: 600;
  color: #6b7280;
  text-transform: lowercase;
  letter-spacing: 0.04em;
}

.pf-dates--all .pf-date-chip:hover .pf-date-chip-text,
.pf-dates--all .pf-date-chip.active .pf-date-chip-text {
  color: #2563eb;
}

.pf-slider-area {
  position: relative;
  width: 100%;
  padding: 0 2px;
}

.pf-track-wrap {
  position: relative;
  height: 28px;
  cursor: pointer;
  touch-action: none;
}

.pf-track {
  position: absolute;
  top: 12px;
  left: 0;
  right: 0;
  height: 5px;
  background: #e5e7eb;
  border-radius: 3px;
}

.pf-range {
  position: absolute;
  top: 12px;
  height: 5px;
  background: linear-gradient(90deg, #3b82f6, #60a5fa);
  border-radius: 3px;
  transition: left 0.25s ease, width 0.25s ease;
  pointer-events: none;
}
.pf-range.no-transition { transition: none; }

.pf-thumb {
  position: absolute;
  top: 5px;
  width: 20px;
  height: 20px;
  background: #fff;
  border: 2.5px solid #3b82f6;
  border-radius: 50%;
  transform: translateX(-50%);
  cursor: grab;
  z-index: 2;
  transition: left 0.25s ease, box-shadow 0.15s, transform 0.15s;
  box-shadow: 0 1px 4px rgba(0,0,0,0.1);
}
.pf-thumb.no-transition {
  transition: box-shadow 0.15s, transform 0.15s;
}
.pf-thumb:hover {
  box-shadow: 0 0 0 6px rgba(59,130,246,0.12), 0 1px 4px rgba(0,0,0,0.1);
  transform: translateX(-50%) scale(1.1);
}
.pf-thumb.active {
  box-shadow: 0 0 0 8px rgba(59,130,246,0.15), 0 2px 8px rgba(0,0,0,0.12);
  transform: translateX(-50%) scale(1.15);
  cursor: grabbing;
}

.pf-ticks {
  position: relative;
  height: 22px;
  margin-top: -2px;
  pointer-events: none;
  overflow: hidden;
}

.pf-tick {
  position: absolute;
  transform: translateX(-50%);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.pf-tick-mark {
  width: 1px;
  height: 6px;
  background: #d1d5db;
}

.pf-tick-label {
  font-size: 10px;
  color: #9ca3af;
  white-space: nowrap;
  margin-top: 1px;
  letter-spacing: 0.01em;
}

@media (max-width: 600px) {
  .pf-controls { gap: 8px; }
  .pf-date-btn { padding: 5px 8px; font-size: 12px; }
}

@media (max-width: 420px) {
  .pf-slider-area { display: none; }
}
</style>

<style>
.pf-calendar {
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(0,0,0,0.12), 0 4px 12px rgba(0,0,0,0.06);
  padding: 14px;
  z-index: 10001;
  animation: pfCalIn 0.15s ease;
}
@keyframes pfCalIn {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.pf-cal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pf-cal-nav {
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
.pf-cal-nav:hover { background: #f3f4f6; color: #374151; }

.pf-cal-title {
  font-weight: 600;
  font-size: 14px;
  color: #111827;
}

.pf-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 1px;
  text-align: center;
}

.pf-cal-dn {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 600;
  padding: 4px 0;
}

.pf-cal-day {
  font-size: 13px;
  padding: 5px 0;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.12s;
  color: #374151;
  user-select: none;
}
.pf-cal-day:hover { background: #f3f4f6; }
.pf-cal-day.other { color: #d1d5db; cursor: default; }
.pf-cal-day.other:hover { background: transparent; }
.pf-cal-day.disabled {
  color: #e5e7eb;
  cursor: not-allowed;
  pointer-events: none;
}
.pf-cal-day.disabled:hover { background: transparent; }
.pf-cal-day.in-range { background: #eff6ff; color: #2563eb; }
.pf-cal-day.range-start,
.pf-cal-day.range-end {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}
.pf-cal-day.range-start:hover,
.pf-cal-day.range-end:hover {
  background: #1d4ed8;
}

@media (max-width: 600px) {
  .period-filter .pf-controls { gap: 8px; }
  .period-filter .pf-date-chip {
    padding: 8px 10px;
    font-size: 12px;
    gap: 6px;
  }
  .period-filter .pf-controls-suffix :deep(.toggle-switch-label) {
    font-size: 12px;
    max-width: 120px;
  }
}
</style>
