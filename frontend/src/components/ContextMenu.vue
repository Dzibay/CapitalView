<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useContextMenu } from '../composables/useContextMenu'

const emit = defineEmits([
  'clearPortfolio',
  'deletePortfolio',
  'addTransaction',
  'addPrice',
  'moveAsset',
  'removeAsset',
  'editTransaction',
  'deleteTransaction'
])

const { menu, closeMenu } = useContextMenu()
const menuRef = ref(null)

const onClickOutside = () => closeMenu()

// Корректируем позицию после рендера, когда известны реальные размеры
const adjustPosition = async () => {
  if (!menu.value.open || !menuRef.value) return
  
  await nextTick()
  
  const rect = menuRef.value.getBoundingClientRect()
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  
  let x = menu.value.x
  let y = menu.value.y
  
  // Корректируем по горизонтали
  if (x + rect.width > viewportWidth) {
    x = viewportWidth - rect.width - 8
  }
  if (x < 8) {
    x = 8
  }
  
  // Корректируем по вертикали
  if (y + rect.height > viewportHeight) {
    y = viewportHeight - rect.height - 8
  }
  if (y < 8) {
    y = 8
  }
  
  // Обновляем позицию только если она изменилась
  if (x !== menu.value.x || y !== menu.value.y) {
    menu.value.x = x
    menu.value.y = y
  }
}

watch(() => menu.value.open, (isOpen) => {
  if (isOpen) {
    nextTick(() => {
      adjustPosition()
    })
  }
})

onMounted(() => {
  document.addEventListener('click', onClickOutside)
  window.addEventListener('resize', adjustPosition)
  window.addEventListener('scroll', adjustPosition, true)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  window.removeEventListener('resize', adjustPosition)
  window.removeEventListener('scroll', adjustPosition, true)
})
</script>

<template>
  <Teleport to="body">
    <div
      v-if="menu.open"
      ref="menuRef"
      class="context-menu"
      :style="{ top: menu.y + 'px', left: menu.x + 'px' }"
    >
      <!-- Портфель -->
      <template v-if="menu.type === 'portfolio'">
        <div class="menu-header">
          <span class="menu-icon">💼</span>
          <span class="menu-title">Портфель</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('clearPortfolio', menu.payload)">
          <span class="item-icon">🧹</span>
          <span class="item-text">Очистить</span>
        </button>
        <button class="item danger" @click="closeMenu(); $emit('deletePortfolio', menu.payload)">
          <span class="item-icon">🗑️</span>
          <span class="item-text">Удалить</span>
        </button>
      </template>

      <!-- Актив -->
      <template v-if="menu.type === 'asset'">
        <div class="menu-header">
          <span class="menu-icon">📈</span>
          <span class="menu-title">Актив</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('addTransaction', menu.payload)">
          <span class="item-icon">💰</span>
          <span class="item-text">Добавить транзакцию</span>
        </button>
        <button class="item" @click="closeMenu(); $emit('addPrice', menu.payload)">
          <span class="item-icon">📈</span>
          <span class="item-text">Изменить цену</span>
        </button>
        <button class="item" @click="closeMenu(); $emit('moveAsset', menu.payload)">
          <span class="item-icon">📦</span>
          <span class="item-text">Переместить</span>
        </button>
        <div class="divider"></div>
        <button class="item danger" @click="closeMenu(); $emit('removeAsset', menu.payload.portfolio_asset_id)">
          <span class="item-icon">🗑️</span>
          <span class="item-text">Удалить</span>
        </button>
      </template>

      <!-- Транзакция -->
      <template v-if="menu.type === 'transaction'">
        <div class="menu-header">
          <span class="menu-icon">💸</span>
          <span class="menu-title">Транзакция</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('editTransaction', menu.payload)">
          <span class="item-icon">✏️</span>
          <span class="item-text">Редактировать</span>
        </button>
        <button class="item danger" @click="closeMenu(); $emit('deleteTransaction', menu.payload)">
          <span class="item-icon">🗑️</span>
          <span class="item-text">Удалить</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style>
.context-menu {
  position: fixed;
  background: linear-gradient(180deg, #ffffff 0%, #fafbfc 100%);
  border-radius: 14px;
  min-width: 220px;
  border: 1px solid rgba(229,231,235,0.8);
  box-shadow: 0 20px 60px rgba(0,0,0,0.15), 0 0 0 1px rgba(0,0,0,0.05);
  z-index: 9999;
  padding: 8px;
  animation: contextMenuFadeIn 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  max-width: calc(100vw - 16px);
  backdrop-filter: blur(10px);
  overflow: hidden;
}

.context-menu::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(59,130,246,0.3), transparent);
}

@keyframes contextMenuFadeIn {
  from {
    opacity: 0;
    transform: scale(0.92) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px 8px;
  margin: -4px -4px 4px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid rgba(226,232,240,0.6);
}

.menu-icon {
  font-size: 18px;
  line-height: 1;
}

.menu-title {
  font-size: 13px;
  font-weight: 700;
  color: #374151;
  letter-spacing: -0.01em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-menu .item {
  width: 100%;
  padding: 10px 14px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.15s cubic-bezier(0.4, 0, 0.2, 1);
  color: #374151;
  font-weight: 500;
  position: relative;
  margin: 2px 0;
}

.context-menu .item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 0;
  background: linear-gradient(180deg, #3b82f6, #2563eb);
  border-radius: 0 2px 2px 0;
  transition: height 0.2s ease;
}

.context-menu .item:hover {
  background: linear-gradient(90deg, #f0f9ff 0%, #e0f2fe 100%);
  color: #2563eb;
  transform: translateX(2px);
  padding-left: 16px;
}

.context-menu .item:hover::before {
  height: 60%;
}

.context-menu .item:active {
  transform: translateX(1px);
}

.item-icon {
  font-size: 16px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  flex-shrink: 0;
}

.item-text {
  flex: 1;
  letter-spacing: -0.01em;
}

.context-menu .item.danger {
  color: #dc2626;
}

.context-menu .item.danger:hover {
  background: linear-gradient(90deg, #fef2f2 0%, #fee2e2 100%);
  color: #dc2626;
}

.context-menu .item.danger::before {
  background: linear-gradient(180deg, #ef4444, #dc2626);
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 6px 4px;
  border: none;
}
</style>
