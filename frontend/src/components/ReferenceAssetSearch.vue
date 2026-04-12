<script setup>
import { ref, watch, onUnmounted, computed } from 'vue'
import { Search, Loader2 } from 'lucide-vue-next'
import { searchReferenceAssets } from '../services/referenceService'

const props = defineProps({
  /** Текст в поле (v-model) */
  modelValue: {
    type: String,
    default: '',
  },
  /** `modal` — форма добавления актива; `header` — шапка */
  variant: {
    type: String,
    default: 'modal',
    validator: (v) => ['modal', 'header'].includes(v),
  },
  placeholder: {
    type: String,
    default: '',
  },
  limit: {
    type: Number,
    default: 25,
  },
  minChars: {
    type: Number,
    default: 2,
  },
  debounceMs: {
    type: Number,
    default: 280,
  },
  /**
   * Не искать и не показывать список (например, актив уже выбран в модалке).
   */
  locked: {
    type: Boolean,
    default: false,
  },
  /** Тип поля ввода */
  inputType: {
    type: String,
    default: 'text',
  },
  /** Задержка закрытия панели после blur (только variant=header) */
  blurCloseDelayMs: {
    type: Number,
    default: 200,
  },
  /** Сообщение при пустом результате */
  emptyMessage: {
    type: String,
    default: '',
  },
  /** Доп. класс на input */
  inputClass: {
    type: String,
    default: '',
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  required: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'select', 'user-input', 'focus', 'blur'])

const results = ref([])
const loading = ref(false)
const panelOpen = ref(false)

let debounceTimer = null
let requestSeq = 0

const placeholderText = computed(() => {
  if (props.placeholder) return props.placeholder
  return props.variant === 'header'
    ? 'Поиск актива (от 2 символов)…'
    : 'Поиск по названию или тикеру (от 2 символов)...'
})

const emptyText = computed(() => {
  if (props.emptyMessage) return props.emptyMessage
  return props.variant === 'header'
    ? 'Актив не найден'
    : 'Актив не найден. Выберите «Кастомный» для создания нового.'
})

const showDropdown = computed(() => {
  const q = props.modelValue.trim()
  if (q.length < props.minChars) return false
  if (props.locked) return false
  if (props.variant === 'header') return panelOpen.value
  return true
})

const rootClass = computed(() => [
  'ref-asset-search',
  props.variant === 'header' ? 'ref-asset-search--header' : 'ref-asset-search--modal',
])

const inputClasses = computed(() => {
  const base =
    props.variant === 'header'
      ? 'ref-asset-search__input ref-asset-search__input--header'
      : 'ref-asset-search__input ref-asset-search__input--modal form-input'
  return [base, props.inputClass].filter(Boolean).join(' ')
})

function onInput(e) {
  const v = e.target.value
  emit('update:modelValue', v)
  emit('user-input', v)
}

function openPanel() {
  if (props.variant === 'header') panelOpen.value = true
  emit('focus')
}

function closePanelSoon() {
  if (props.variant !== 'header') return
  setTimeout(() => {
    panelOpen.value = false
  }, props.blurCloseDelayMs)
}

function onBlur(e) {
  closePanelSoon()
  emit('blur', e)
}

function pick(asset) {
  emit('select', asset)
  if (props.variant === 'header') {
    emit('update:modelValue', '')
    results.value = []
    loading.value = false
    panelOpen.value = false
  }
}

watch(
  () => props.modelValue,
  () => {
    if (props.locked) {
      results.value = []
      loading.value = false
      return
    }
    clearTimeout(debounceTimer)
    const q = props.modelValue.trim()
    if (q.length < props.minChars) {
      results.value = []
      loading.value = false
      return
    }
    loading.value = true
    debounceTimer = setTimeout(async () => {
      const seq = ++requestSeq
      try {
        const items = await searchReferenceAssets(q, props.limit)
        if (seq === requestSeq) results.value = items
      } catch (e) {
        console.error(e)
        if (seq === requestSeq) results.value = []
      } finally {
        if (seq === requestSeq) loading.value = false
      }
    }, props.debounceMs)
  }
)

onUnmounted(() => {
  clearTimeout(debounceTimer)
})

defineExpose({
  clearResults() {
    results.value = []
    loading.value = false
  },
})
</script>

<template>
  <div :class="rootClass">
    <div class="ref-asset-search__wrap">
      <Search :size="16" class="ref-asset-search__icon" />
      <input
        :type="inputType"
        :value="modelValue"
        :class="inputClasses"
        :placeholder="placeholderText"
        :disabled="disabled"
        :required="required"
        autocomplete="off"
        @input="onInput"
        @focus="openPanel"
        @blur="onBlur"
      />
      <ul v-if="showDropdown" class="ref-asset-search__dropdown" role="listbox">
        <li v-if="loading" class="ref-asset-search__msg">
          <Loader2 :size="variant === 'header' ? 18 : 20" class="ref-asset-search__spinner" />
          <span>Поиск…</span>
        </li>
        <template v-else>
          <li
            v-for="a in results"
            :key="a.id"
            class="ref-asset-search__item"
            role="option"
            @mousedown.prevent="pick(a)"
          >
            <div class="ref-asset-search__row">
              <span class="ref-asset-search__name">{{ a.name }}</span>
              <span class="ref-asset-search__ticker">{{ a.ticker || '—' }}</span>
            </div>
          </li>
          <li v-if="results.length === 0" class="ref-asset-search__msg">
            <Search :size="variant === 'header' ? 18 : 20" class="ref-asset-search__empty-icon" />
            <span>{{ emptyText }}</span>
          </li>
        </template>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.ref-asset-search {
  position: relative;
  width: 100%;
}

.ref-asset-search__wrap {
  position: relative;
  width: 100%;
}

.ref-asset-search__icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: #9ca3af;
  z-index: 1;
}

.ref-asset-search__input {
  width: 100%;
  box-sizing: border-box;
  font-family: inherit;
}

.ref-asset-search__input--modal {
  padding: 11px 14px 11px 36px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
  color: #111827;
  transition: all 0.2s ease;
}

.ref-asset-search__input--modal:hover {
  border-color: #d1d5db;
  background: #fafafa;
}

.ref-asset-search__input--modal:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
  background: #fff;
}

.ref-asset-search__input--modal:disabled {
  background: #f9fafb;
  color: #9ca3af;
  cursor: not-allowed;
}

.ref-asset-search__input--header {
  height: 40px;
  padding: 0 14px 0 38px;
  border: 1.5px solid #e5e7eb;
  border-radius: 10px;
  font-size: 14px;
  background: #fff;
  color: #111827;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.ref-asset-search__input--header::placeholder {
  color: #9ca3af;
}

.ref-asset-search__input--header:hover {
  border-color: #d1d5db;
}

.ref-asset-search__input--header:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.12);
}

.ref-asset-search__dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  width: 100%;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.12), 0 4px 10px rgba(0, 0, 0, 0.08);
  max-height: min(280px, 50vh);
  overflow-y: auto;
  z-index: 1010;
}

.ref-asset-search--header .ref-asset-search__dropdown {
  width: max(100%, 260px);
  max-width: min(400px, calc(100vw - 24px));
  right: auto;
}

.ref-asset-search--modal .ref-asset-search__dropdown {
  animation: ref-asset-search-slide 0.2s ease;
}

@keyframes ref-asset-search-slide {
  from {
    opacity: 0;
    transform: translateY(-4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.ref-asset-search__item {
  padding: 12px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  border-left: 3px solid transparent;
}

.ref-asset-search--header .ref-asset-search__item {
  padding: 10px 14px;
}

.ref-asset-search__item:hover {
  background: #f3f4f6;
  border-left-color: #3b82f6;
  padding-left: 11px;
}

.ref-asset-search__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  width: 100%;
}

.ref-asset-search__name {
  font-weight: 500;
  color: #111827;
  font-size: 13px;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ref-asset-search__ticker {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
  flex-shrink: 0;
}

.ref-asset-search__msg {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 14px;
  color: #9ca3af;
  font-size: 12px;
  cursor: default;
  text-align: center;
  flex-direction: column;
}

.ref-asset-search--header .ref-asset-search__msg {
  flex-direction: row;
  padding: 14px;
}

.ref-asset-search__spinner {
  color: #3b82f6;
  animation: ref-asset-search-spin 1s linear infinite;
}

.ref-asset-search__empty-icon {
  color: #d1d5db;
  opacity: 0.6;
}

@keyframes ref-asset-search-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
