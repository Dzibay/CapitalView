<script setup>
import { ref, useId } from 'vue'

defineProps({
  /** Текст на кнопке верхнего уровня */
  label: {
    type: String,
    required: true,
  },
  /** Ссылка верхнего уровня (основная страница раздела) */
  to: {
    type: String,
    required: true,
  },
  /** Подсветка, если текущий маршрут внутри раздела */
  active: {
    type: Boolean,
    default: false,
  },
})

const menuId = useId()

const open = ref(false)

function openMenu() {
  open.value = true
}

function closeMenu() {
  open.value = false
}

/** Не закрывать при Tab с триггера на пункты меню внутри того же контейнера */
function onFocusOut(ev) {
  const root = ev.currentTarget
  const next = ev.relatedTarget
  if (next instanceof Node && root.contains(next)) return
  open.value = false
}
</script>

<template>
  <div
    class="site-nav-dropdown"
    :class="{
      'site-nav-dropdown--active': active,
      'site-nav-dropdown--open': open,
    }"
    @mouseenter="openMenu"
    @mouseleave="closeMenu"
    @focusin="openMenu"
    @focusout="onFocusOut"
  >
    <router-link
      :to="to"
      class="site-nav-dropdown__trigger"
      :aria-label="`Перейти в раздел: ${label}`"
    >
      {{ label }}
    </router-link>
    <div
      :id="menuId"
      class="site-nav-dropdown__panel"
      role="menu"
      :aria-label="label"
      :aria-hidden="!open"
      :inert="!open"
    >
      <slot />
    </div>
  </div>
</template>

<style scoped>
.site-nav-dropdown {
  position: relative;
}

.site-nav-dropdown__trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  text-decoration: none;
  font: inherit;
  font-family: var(--font-body, 'Plus Jakarta Sans', system-ui, sans-serif);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.01em;
  color: var(--color-text-secondary, #64748b);
  padding: 8px 12px;
  margin: 0;
  border: none;
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
  white-space: nowrap;
  transition:
    color 0.2s ease,
    background 0.2s ease,
    box-shadow 0.2s ease;
}

.site-nav-dropdown__trigger::after {
  content: '';
  flex-shrink: 0;
  width: 0.32em;
  height: 0.32em;
  margin-top: -0.12em;
  border-right: 1.5px solid currentColor;
  border-bottom: 1.5px solid currentColor;
  opacity: 0.42;
  transform: rotate(45deg);
  transition:
    transform 0.22s cubic-bezier(0.32, 0.72, 0, 1),
    opacity 0.2s ease;
}

.site-nav-dropdown__trigger:hover {
  color: var(--color-text, #0f172a);
  background: rgba(15, 23, 42, 0.04);
}

.site-nav-dropdown__trigger:focus-visible {
  outline: 2px solid var(--color-primary, #3b82f6);
  outline-offset: 2px;
}

.site-nav-dropdown--open .site-nav-dropdown__trigger {
  color: var(--color-primary, #3b82f6);
  background: rgba(59, 130, 246, 0.08);
}

.site-nav-dropdown--open .site-nav-dropdown__trigger::after {
  opacity: 0.55;
  transform: rotate(-135deg);
  margin-top: 0.08em;
}

.site-nav-dropdown--active:not(.site-nav-dropdown--open) .site-nav-dropdown__trigger {
  color: var(--color-primary, #3b82f6);
}

.site-nav-dropdown__panel {
  position: absolute;
  left: 0;
  top: calc(100% + 8px);
  min-width: 260px;
  max-width: min(92vw, 340px);
  padding: 8px;
  background: #ffffff;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(15, 23, 42, 0.1);
  z-index: 110;
  pointer-events: none;
  opacity: 0;
  visibility: hidden;
  transform: translateY(-4px);
  transform-origin: top left;
  transition:
    opacity 0.2s ease,
    transform 0.2s cubic-bezier(0.32, 0.72, 0, 1),
    visibility 0.2s;
}

/* «Мост» для курсора между кнопкой и панелью */
.site-nav-dropdown__panel::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -10px;
  height: 10px;
}

.site-nav-dropdown--open .site-nav-dropdown__panel {
  pointer-events: auto;
  opacity: 1;
  visibility: visible;
  transform: translateY(0);
}

.site-nav-dropdown__panel :deep(a) {
  display: block;
  font-family: var(--font-body, 'Plus Jakarta Sans', system-ui, sans-serif);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--color-text-secondary, #64748b);
  text-decoration: none;
  padding: 10px 12px;
  margin: 2px 0;
  border-radius: 10px;
  transition:
    color 0.18s ease,
    background 0.18s ease;
}

.site-nav-dropdown__panel :deep(a:hover) {
  color: var(--color-text, #0f172a);
  background: rgba(15, 23, 42, 0.045);
}

.site-nav-dropdown__panel :deep(a.router-link-active) {
  color: var(--color-primary, #3b82f6);
  font-weight: 600;
  background: var(--color-primary-light, rgba(59, 130, 246, 0.1));
}

@media (prefers-reduced-motion: reduce) {
  .site-nav-dropdown__panel,
  .site-nav-dropdown__trigger::after {
    transition-duration: 0.01ms;
  }

  .site-nav-dropdown__panel {
    transform: none;
  }

  .site-nav-dropdown--open .site-nav-dropdown__panel {
    transform: none;
  }
}
</style>
