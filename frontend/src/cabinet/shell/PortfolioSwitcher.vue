<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ChevronsUpDown, Check, FolderTree } from 'lucide-vue-next'
import { flattenPortfolioTree } from '../portfolioTree'
import { moneyCompact, plural } from '../format'

const props = defineProps({
  portfolios: { type: Array, default: () => [] },
  modelValue: { type: [Number, String], default: null },
})
const emit = defineEmits(['update:modelValue'])

const open = ref(false)
const root = ref(null)

const rows = computed(() => flattenPortfolioTree(props.portfolios))
const current = computed(() => props.portfolios.find((p) => p.id === props.modelValue) || props.portfolios[0])
const maxValue = computed(() => Math.max(1, ...props.portfolios.map((p) => Number(p.total_value) || 0)))

function pick(id) {
  emit('update:modelValue', id)
  open.value = false
}

function onDocDown(e) {
  if (open.value && root.value && !root.value.contains(e.target)) open.value = false
}
function onKey(e) {
  if (e.key === 'Escape') open.value = false
}
onMounted(() => {
  document.addEventListener('pointerdown', onDocDown)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', onDocDown)
  document.removeEventListener('keydown', onKey)
})

const assetsCount = (p) => (p.assets || []).filter((a) => Number(a.quantity) !== 0).length
</script>

<template>
  <div ref="root" class="cv-ps">
    <button
      type="button"
      class="cv-ps__btn"
      :class="{ 'is-open': open }"
      aria-haspopup="listbox"
      :aria-expanded="open"
      @click="open = !open"
    >
      <span class="cv-ps__mark"><FolderTree :size="14" :stroke-width="2" /></span>
      <span class="cv-ps__text">
        <span class="cv-ps__label">Портфель</span>
        <span class="cv-ps__name">{{ current?.name || '—' }}</span>
      </span>
      <ChevronsUpDown :size="15" class="cv-ps__chev" />
    </button>

    <Transition name="cv-pop">
      <div v-if="open" class="cv-ps__menu cv-pop" role="listbox" aria-label="Выбор портфеля">
        <div class="cv-ps__head">Портфели</div>
        <button
          v-for="{ portfolio: p, depth } in rows"
          :key="p.id"
          type="button"
          role="option"
          class="cv-ps__row"
          :class="{ 'is-on': p.id === modelValue }"
          :aria-selected="p.id === modelValue"
          :style="{ '--depth': depth }"
          @click="pick(p.id)"
        >
          <span class="cv-ps__tree" aria-hidden="true" />
          <span class="cv-ps__info">
            <span class="cv-ps__rname">{{ p.name }}</span>
            <span class="cv-ps__meta">
              {{ assetsCount(p) }} {{ plural(assetsCount(p), 'актив', 'актива', 'активов') }}
            </span>
            <span class="cv-ps__share"><i :style="{ transform: `scaleX(${(Number(p.total_value) || 0) / maxValue})` }" /></span>
          </span>
          <span class="cv-ps__val cv-num">{{ moneyCompact(p.total_value) }}</span>
          <Check v-if="p.id === modelValue" :size="15" class="cv-ps__check" />
          <span v-else class="cv-ps__check" />
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.cv-ps { position: relative; }
.cv-ps__btn {
  display: flex; align-items: center; gap: 10px; height: 40px; padding: 0 10px 0 6px; max-width: 280px;
  border: 0; border-radius: 12px; cursor: pointer; text-align: left;
  background: rgba(255, 255, 255, .035); box-shadow: inset 0 0 0 1px var(--cv-line);
  transition: background .2s, box-shadow .2s;
}
.cv-ps__btn:hover, .cv-ps__btn.is-open { background: rgba(255, 255, 255, .06); box-shadow: inset 0 0 0 1px var(--cv-line-2); }
.cv-ps__mark {
  display: grid; place-items: center; width: 28px; height: 28px; border-radius: 9px; flex: none;
  color: #fff; background: linear-gradient(135deg, #6d84ff, #8b5cf6);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, .25), 0 4px 14px -4px rgba(91, 116, 255, .8);
}
.cv-ps__text { display: flex; flex-direction: column; min-width: 0; line-height: 1.15; }
.cv-ps__label { font-size: 10.5px; color: var(--cv-dim); font-weight: 500; }
.cv-ps__name { font-size: 13px; font-weight: 600; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-ps__chev { color: var(--cv-mut); flex: none; }

.cv-ps__menu {
  position: absolute; top: calc(100% + 8px); right: 0; z-index: 50; width: 340px;
  transform-origin: top right;
}
.cv-ps__head { padding: 8px 10px 6px; font-size: 11px; font-weight: 600; letter-spacing: .06em; text-transform: uppercase; color: var(--cv-dim); }
.cv-ps__row {
  position: relative; display: flex; align-items: center; gap: 10px; width: 100%;
  padding: 8px 10px 8px calc(10px + var(--depth) * 18px);
  border: 0; border-radius: 11px; background: transparent; cursor: pointer; text-align: left;
  transition: background .15s;
}
.cv-ps__row:hover { background: var(--cv-hover); }
.cv-ps__row.is-on { background: var(--cv-accent-soft); }
.cv-ps__tree {
  position: absolute; left: calc(var(--depth) * 18px - 2px); top: 0; bottom: 50%; width: 9px;
  border-left: 1px solid var(--cv-line-3); border-bottom: 1px solid var(--cv-line-3); border-bottom-left-radius: 6px;
  opacity: calc(var(--depth));
}
.cv-ps__info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cv-ps__rname { font-size: 13px; font-weight: 550; color: var(--cv-ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cv-ps__meta { font-size: 11.5px; color: var(--cv-dim); }
.cv-ps__share { height: 3px; margin-top: 3px; border-radius: 3px; background: rgba(255, 255, 255, .06); overflow: hidden; }
.cv-ps__share i { display: block; height: 100%; background: var(--cv-accent); border-radius: inherit; transform-origin: left; opacity: .8; }
.cv-ps__val { font-size: 12.5px; font-weight: 600; color: var(--cv-ink-2); white-space: nowrap; }
.cv-ps__check { width: 15px; flex: none; color: var(--cv-accent-ink); }

@media (max-width: 768px) {
  .cv-ps__btn { height: 36px; max-width: 170px; padding: 0 8px 0 4px; gap: 8px; }
  .cv-ps__mark { width: 26px; height: 26px; }
  .cv-ps__label { display: none; }
  .cv-ps__menu { position: fixed; top: 60px; left: 10px; right: 10px; width: auto; }
}
</style>
