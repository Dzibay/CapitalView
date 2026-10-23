<script setup>
/**
 * Рамка виджета дашборда: заголовок, действия, подсветка за курсором,
 * а в режиме редактирования — ручка перетаскивания, размеры и скрытие.
 */
import { GripVertical, EyeOff } from 'lucide-vue-next'

const props = defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  /** оставлен для совместимости: в заголовке иконки больше не рисуются */
  icon: { type: [Object, Function], default: null },
  editing: { type: Boolean, default: false },
  size: { type: String, default: 'm' },
  sizes: { type: Array, default: () => ['s', 'm', 'l', 'xl'] },
  glow: { type: Boolean, default: false },
  flush: { type: Boolean, default: false },
})
const emit = defineEmits(['resize', 'hide'])

const SIZE_LABEL = { s: '⅓', m: '½', l: '⅔', xl: '1' }
const SIZE_NAME = { s: 'треть строки', m: 'половина строки', l: 'две трети строки', xl: 'вся строка' }

function onMove(e) {
  const r = e.currentTarget.getBoundingClientRect()
  e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
  e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
}
</script>

<template>
  <section
    class="cv-w cv-card"
    :class="{ 'cv-card--glow': glow, 'is-editing': editing, 'is-flush': flush }"
    @pointermove="onMove"
  >
    <header v-if="title || $slots.actions || editing" class="cv-w__head">
      <button
        v-if="editing"
        type="button"
        class="cv-w__grip cv-drag-handle"
        aria-label="Перетащить виджет"
      >
        <GripVertical :size="16" />
      </button>
      <div class="cv-w__titles">
        <h3 class="cv-w__title cv-eyebrow">{{ title }}</h3>
        <p v-if="subtitle" class="cv-w__sub">{{ subtitle }}</p>
      </div>
      <div class="cv-w__actions">
        <template v-if="editing">
          <div v-if="props.sizes.length > 1" class="cv-w__sizes" role="group" aria-label="Ширина виджета">
            <button
              v-for="s in props.sizes"
              :key="s"
              type="button"
              :class="{ 'is-on': s === size }"
              :title="`Ширина: ${SIZE_NAME[s]}`"
              :aria-label="`Ширина: ${SIZE_NAME[s]}`"
              :aria-pressed="s === size"
              @click="emit('resize', s)"
            >{{ SIZE_LABEL[s] }}</button>
          </div>
          <button type="button" class="cv-btn cv-btn--ghost cv-btn--icon cv-btn--sm" title="Скрыть виджет" aria-label="Скрыть виджет" @click="emit('hide')">
            <EyeOff :size="15" />
          </button>
        </template>
        <slot v-else name="actions" />
      </div>
    </header>
    <div class="cv-w__body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.cv-w {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
  padding: 22px 24px 24px;
  transition: box-shadow .3s var(--cv-ease), transform .3s var(--cv-ease);
}
.cv-w.is-flush { padding: 0; }
.cv-w.is-flush .cv-w__head { padding: 22px 24px 0; }

/* сдержанный свет рамки за курсором */
.cv-w::after {
  content: '';
  position: absolute; inset: -1px; border-radius: inherit; pointer-events: none; z-index: 2;
  padding: 1px;
  background: radial-gradient(200px circle at var(--mx, -999px) var(--my, -999px), rgba(180, 188, 255, .2), transparent 70%);
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity .35s;
}
.cv-w:hover::after { opacity: 1; }

.cv-w.is-editing {
  box-shadow: 0 0 0 1px var(--cv-accent-line), 0 0 0 4px rgba(100, 116, 255, .05);
  animation: cv-wobble .5s var(--cv-ease);
}
@keyframes cv-wobble {
  0% { transform: scale(1); }
  40% { transform: scale(.985); }
  100% { transform: scale(1); }
}

.cv-w__head {
  display: flex;
  flex-wrap: wrap; /* на узких экранах переключатели уходят под заголовок */
  align-items: flex-start;
  gap: 8px 10px;
  margin-bottom: 16px;
  min-height: 30px;
}
.cv-w__titles { flex: 1 1 auto; min-width: 0; padding-top: 8px; }
.cv-w__title { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-w__sub { margin-top: 3px; font-size: 12px; color: var(--cv-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-w__actions { display: flex; align-items: center; gap: 6px; flex: none; max-width: 100%; margin-left: auto; }

.cv-w__grip {
  display: grid; place-items: center; width: 26px; height: 30px; margin-left: -8px;
  border: 0; border-radius: 8px; background: transparent; color: var(--cv-mut); cursor: grab;
}
.cv-w__grip:hover { background: var(--cv-hover); color: var(--cv-ink); }
.cv-w__grip:active { cursor: grabbing; }

.cv-w__sizes {
  display: inline-flex; padding: 2px; gap: 2px; border-radius: 9px;
  background: rgba(255, 255, 255, .04); box-shadow: inset 0 0 0 1px var(--cv-line);
}
.cv-w__sizes button {
  min-width: 26px; height: 24px; padding: 0 6px; border: 0; border-radius: 7px;
  background: transparent; color: var(--cv-mut); font-size: 12px; font-weight: 600; cursor: pointer;
}
.cv-w__sizes button:hover { color: var(--cv-ink); }
.cv-w__sizes button.is-on { background: var(--cv-accent-soft); color: var(--cv-accent-ink); }

.cv-w__body { position: relative; flex: 1; min-height: 0; display: flex; flex-direction: column; }
</style>
