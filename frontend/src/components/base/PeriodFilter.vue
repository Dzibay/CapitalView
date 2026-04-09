<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { Teleport } from 'vue'
import CustomSelect from './CustomSelect.vue'
import DateInput from './DateInput.vue'
import { normalizeDateToString } from '../../utils/date'
import { Calendar } from 'lucide-vue-next'

const props = defineProps({
  preset: { type: String, default: 'all' },
  startDate: { type: String, default: '' },
  endDate: { type: String, default: '' },
  /** Левая граница шкалы и выбора — первая дата операции/транзакции (YYYY-MM-DD). Пусто — запас 6 лет назад. */
  trackMinDate: { type: String, default: '' },
  /** Правая граница шкалы (YYYY-MM-DD). Пусто — сегодня. Нужна для диапазонов с будущими датами (прогнозы выплат). */
  trackMaxDate: { type: String, default: '' },
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

const trackMax = computed(() => {
  const p = parseDate(props.trackMaxDate)
  if (p) {
    p.setHours(0, 0, 0, 0)
    return p
  }
  return startOfToday()
})

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
const calendarStyle = ref({})

/** На узком экране диапазон дат — только системный date picker, без плавающего поля */
const NATIVE_RANGE_MQ = '(max-width: 768px)'
const isMobileNativeRange = ref(
  typeof window !== 'undefined' && window.matchMedia(NATIVE_RANGE_MQ).matches,
)
const nativeRangeInputRef = ref(null)
let nativeRangeMqCleanup = null

/** После повторного клика по чипу — ввод даты с клавиатуры ('left' | 'right') */
const inlineEditThumb = ref(null)
const editDraft = ref('')
const editInputLeftRef = ref(null)
const editInputRightRef = ref(null)

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

const fmtEditDraft = (d) => {
  if (!d || isNaN(d.getTime())) return ''
  return `${String(d.getDate()).padStart(2,'0')}.${String(d.getMonth() + 1).padStart(2,'0')}.${d.getFullYear()}`
}

/** Календарный день: день, месяц (1–12), полный год. Без new Date(string) — он даёт MM.DD для «01.11.2025». */
const buildValidCalendarDate = (day, month, year) => {
  if (month < 1 || month > 12 || day < 1 || day > 31) return null
  const d = new Date(year, month - 1, day)
  d.setHours(0, 0, 0, 0)
  if (d.getFullYear() !== year || d.getMonth() !== month - 1 || d.getDate() !== day) return null
  return d
}

/**
 * ДД.ММ.ГГГГ / ДД.ММ.ГГ / ДД/ММ/ГГГГ (европейский порядок),
 * только цифры: 8 = ДДММГГГГ, 6 = ДДММГГ (год 20xx),
 * YYYY-MM-DD.
 */
const parseTypedDate = (str) => {
  const t = str.trim()
  if (!t) return null
  if (/^\d{4}-\d{2}-\d{2}$/.test(t)) {
    const d = parseDate(t)
    return d && !isNaN(d.getTime()) ? d : null
  }
  const m = t.match(/^(\d{1,2})[./](\d{1,2})[./](\d{2}|\d{4})$/)
  if (m) {
    const day = parseInt(m[1], 10)
    const month = parseInt(m[2], 10)
    let year = parseInt(m[3], 10)
    if (m[3].length === 2) year += 2000
    return buildValidCalendarDate(day, month, year)
  }
  const digits = t.replace(/\D/g, '')
  if (digits.length === 8) {
    const day = parseInt(digits.slice(0, 2), 10)
    const month = parseInt(digits.slice(2, 4), 10)
    const year = parseInt(digits.slice(4, 8), 10)
    return buildValidCalendarDate(day, month, year)
  }
  if (digits.length === 6) {
    const day = parseInt(digits.slice(0, 2), 10)
    const month = parseInt(digits.slice(2, 4), 10)
    const yy = parseInt(digits.slice(4, 6), 10)
    return buildValidCalendarDate(day, month, 2000 + yy)
  }
  return null
}

/** Из ввода оставляем до 8 цифр и показываем ДД.ММ.ГГГГ без необходимости вводить точки */
const digitsToDraftDisplay = (digits) => {
  const d = digits.slice(0, 8)
  if (d.length === 0) return ''
  if (d.length <= 2) return d
  if (d.length <= 4) return `${d.slice(0, 2)}.${d.slice(2)}`
  return `${d.slice(0, 2)}.${d.slice(2, 4)}.${d.slice(4)}`
}

const onEditDraftInput = (e) => {
  const digits = e.target.value.replace(/\D/g, '').slice(0, 8)
  editDraft.value = digitsToDraftDisplay(digits)
  nextTick(() => {
    const el = e.target
    if (el && document.activeElement === el) {
      const pos = editDraft.value.length
      el.setSelectionRange(pos, pos)
    }
  })
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
  inlineEditThumb.value = null

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
  if (inlineEditThumb.value) {
    const ae = document.activeElement
    if (ae instanceof HTMLElement && ae.classList.contains('pf-date-chip-input')) {
      ae.blur()
    }
  }

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
  const cw = vw <= 768 ? Math.min(vw - 24, 360) : CALENDAR_WIDTH
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
  inlineEditThumb.value = null
  calendarTarget.value = thumb
  if (isMobileNativeRange.value) {
    nextTick(() => {
      requestAnimationFrame(() => {
        const el = nativeRangeInputRef.value
        if (!el || !calendarTarget.value) return
        try {
          el.showPicker?.()
        } catch {
          el.focus()
        }
      })
    })
    return
  }
  nextTick(() => {
    positionCalendar()
    attachCalendarReposition()
    nextTick(() => positionCalendar())
  })
}

const onDateChipClick = (thumb) => {
  if (inlineEditThumb.value === thumb) return
  if (calendarTarget.value === thumb) {
    calendarTarget.value = null
    inlineEditThumb.value = thumb
    editDraft.value = fmtEditDraft(thumb === 'left' ? selStart.value : selEnd.value)
    nextTick(() => {
      const el = thumb === 'left' ? editInputLeftRef.value : editInputRightRef.value
      el?.focus()
      el?.select()
    })
    return
  }
  showCalendar(thumb)
}

const commitDateEdit = (thumb) => {
  if (inlineEditThumb.value !== thumb) return
  const raw = editDraft.value.trim()
  inlineEditThumb.value = null
  if (!raw) return
  const parsed = parseTypedDate(raw)
  if (!parsed) return
  const day = clampDayToTrack(parsed)
  if (thumb === 'left') {
    if (day.getTime() > selEnd.value.getTime()) {
      selStart.value = new Date(selEnd.value)
    } else {
      selStart.value = day
    }
    emit('update:startDate', normalizeDateToString(selStart.value))
  } else {
    if (day.getTime() < selStart.value.getTime()) {
      selEnd.value = new Date(selStart.value)
    } else {
      selEnd.value = day
    }
    emit('update:endDate', normalizeDateToString(selEnd.value))
  }
  emit('update:preset', 'custom')
  settleVisibleRange()
}

const cancelDateEdit = () => {
  inlineEditThumb.value = null
}

const gridModelValue = computed(() => {
  if (!calendarTarget.value) return ''
  return calendarTarget.value === 'left'
    ? normalizeDateToString(selStart.value)
    : normalizeDateToString(selEnd.value)
})

const mobilePickerMin = computed(() => {
  if (!calendarTarget.value) return undefined
  const a = normalizeDateToString(trackMin.value)
  const b = calendarTarget.value === 'right' ? normalizeDateToString(selStart.value) : ''
  if (a && b) return a > b ? a : b
  return a || b || undefined
})

const mobilePickerMax = computed(() => {
  if (!calendarTarget.value) return undefined
  const a = normalizeDateToString(trackMax.value)
  const b = calendarTarget.value === 'left' ? normalizeDateToString(selEnd.value) : ''
  if (a && b) return a < b ? a : b
  return a || b || undefined
})

const onDateGridPick = (ymd) => {
  const day = clampDayToTrack(parseDate(ymd))
  if (calendarTarget.value === 'left') {
    if (day.getTime() <= selEnd.value.getTime()) {
      selStart.value = new Date(day)
      emit('update:startDate', normalizeDateToString(day))
    }
  } else if (calendarTarget.value === 'right') {
    if (day.getTime() >= selStart.value.getTime()) {
      selEnd.value = new Date(day)
      emit('update:endDate', normalizeDateToString(day))
    }
  }
  emit('update:preset', 'custom')
  calendarTarget.value = null
  settleVisibleRange()
}

const onNativeRangeChange = (e) => {
  const ymd = e.target?.value
  if (!ymd || !calendarTarget.value) return
  onDateGridPick(ymd)
}

watch(calendarTarget, (v) => {
  if (!v) detachCalendarReposition()
})

watch(() => props.preset, (val) => {
  inlineEditThumb.value = null
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
  () => [props.trackMinDate, props.trackMaxDate],
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
  /* На мобильном нет DOM-попапа: не гасим target по документу — иначе ломается выбор в системном пикере */
  if (isMobileNativeRange.value) return
  const t = e.target
  if (t instanceof Element && t.closest('.custom-select-dropdown')) return
  const cal = document.querySelector('.pf-period-calendar-popover')
  if (cal?.contains(t)) return
  if (datesAnchorRef.value?.contains(t)) return
  calendarTarget.value = null
}

const initNativeRangeMq = () => {
  if (typeof window === 'undefined') return
  const mq = window.matchMedia(NATIVE_RANGE_MQ)
  const apply = () => {
    isMobileNativeRange.value = mq.matches
  }
  apply()
  if (typeof mq.addEventListener === 'function') {
    mq.addEventListener('change', apply)
    nativeRangeMqCleanup = () => mq.removeEventListener('change', apply)
  } else {
    mq.addListener(apply)
    nativeRangeMqCleanup = () => mq.removeListener(apply)
  }
}

onMounted(() => {
  initNativeRangeMq()
  document.addEventListener('mousedown', handleDocClick, true)
  document.addEventListener('pointerdown', handleDocClick, true)
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
  nativeRangeMqCleanup?.()
  nativeRangeMqCleanup = null
  document.removeEventListener('mousedown', handleDocClick, true)
  document.removeEventListener('pointerdown', handleDocClick, true)
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
          <input
            v-if="inlineEditThumb === 'left'"
            ref="editInputLeftRef"
            :value="editDraft"
            type="text"
            class="pf-date-chip pf-date-chip-input"
            placeholder="ДДММГГГГ"
            title="Только цифры: день, месяц, год (точки подставятся сами) или ДД.ММ.ГГГГ"
            inputmode="numeric"
            autocomplete="off"
            aria-label="Дата начала периода"
            @input="onEditDraftInput"
            @blur="commitDateEdit('left')"
            @keydown.enter.prevent="commitDateEdit('left')"
            @keydown.escape.prevent="cancelDateEdit"
          >
          <button
            v-else
            type="button"
            class="pf-date-chip"
            :class="{ active: calendarTarget === 'left' }"
            @click.stop="onDateChipClick('left')"
          >
            <Calendar class="pf-date-chip-icon" :size="15" stroke-width="2" aria-hidden="true" />
            <span class="pf-date-chip-text">{{ dateLeftDisplay }}</span>
          </button>
          <span class="pf-dates-divider" aria-hidden="true" />
          <input
            v-if="inlineEditThumb === 'right'"
            ref="editInputRightRef"
            :value="editDraft"
            type="text"
            class="pf-date-chip pf-date-chip-input"
            placeholder="ДДММГГГГ"
            title="Только цифры: день, месяц, год (точки подставятся сами) или ДД.ММ.ГГГГ"
            inputmode="numeric"
            autocomplete="off"
            aria-label="Дата конца периода"
            @input="onEditDraftInput"
            @blur="commitDateEdit('right')"
            @keydown.enter.prevent="commitDateEdit('right')"
            @keydown.escape.prevent="cancelDateEdit"
          >
          <button
            v-else
            type="button"
            class="pf-date-chip"
            :class="{ active: calendarTarget === 'right' }"
            @click.stop="onDateChipClick('right')"
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

    <input
      v-if="isMobileNativeRange"
      ref="nativeRangeInputRef"
      type="date"
      class="pf-hidden-native-date"
      :value="gridModelValue"
      :min="mobilePickerMin || undefined"
      :max="mobilePickerMax || undefined"
      tabindex="-1"
      aria-hidden="true"
      @change="onNativeRangeChange"
    >

    <Teleport to="body">
      <DateInput
        v-if="calendarTarget && !isMobileNativeRange"
        inline-panel
        class="pf-period-calendar-popover"
        :style="calendarStyle"
        :model-value="gridModelValue"
        :min="normalizeDateToString(trackMin)"
        :max="normalizeDateToString(trackMax)"
        :range-start="normalizeDateToString(selStart)"
        :range-end="normalizeDateToString(selEnd)"
        :select-bound-max="calendarTarget === 'left' ? normalizeDateToString(selEnd) : ''"
        :select-bound-min="calendarTarget === 'right' ? normalizeDateToString(selStart) : ''"
        @update:model-value="onDateGridPick"
        @layout-change="positionCalendar"
      />
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

/* Якорь для showPicker() на мобильных — не показываем отдельное поле на экране */
.pf-hidden-native-date {
  position: fixed;
  left: 0;
  top: 0;
  width: 1px;
  height: 1px;
  margin: 0;
  padding: 0;
  opacity: 0;
  pointer-events: none;
  border: 0;
  clip: rect(0, 0, 0, 0);
  overflow: hidden;
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

.pf-date-chip-input {
  flex: 1 1 0;
  min-width: 0;
  width: 100%;
  padding: 8px 10px;
  border: none;
  border-radius: 0;
  background: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  color: #111827;
  outline: none;
  box-sizing: border-box;
  cursor: text;
}

.pf-date-chip-input::placeholder {
  color: #9ca3af;
  font-weight: 400;
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
  /* Запас под ползунки (translateX(-50%), scale 1.15) и тень :active 8px — иначе обрезает overflow:hidden у предка */
  padding: 0 22px;
  box-sizing: border-box;
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
