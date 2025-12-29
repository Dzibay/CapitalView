<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useContextMenu } from '../composables/useContextMenu'

const emit = defineEmits([
  'clearPortfolio',
  'deletePortfolio',
  'addTransaction',
  'addPrice',
  'removeAsset'
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
        <button class="item" @click="$emit('clearPortfolio', menu.payload)">
          🧹 Очистить
        </button>
        <button class="item danger" @click="$emit('deletePortfolio', menu.payload)">
          🗑️ Удалить
        </button>
      </template>

      <!-- Актив -->
      <template v-if="menu.type === 'asset'">
        <button class="item" @click="$emit('addTransaction', menu.payload)">
          💰 Добавить транзакцию
        </button>
        <button class="item" @click="$emit('addPrice', menu.payload)">
          📈 Изменить цену
        </button>
        <div class="divider"></div>
        <button class="item danger" @click="$emit('removeAsset', menu.payload.portfolio_asset_id)">
          🗑️ Удалить
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style>
.context-menu {
  position: fixed;
  background: white;
  border-radius: 8px;
  min-width: 200px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 10px 30px rgba(0,0,0,0.15);
  z-index: 9999;
  padding: 4px;
  animation: contextMenuFadeIn 0.15s ease-out;
  max-width: calc(100vw - 16px);
  max-height: calc(100vh - 16px);
  overflow-y: auto;
}

@keyframes contextMenuFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.context-menu .item {
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;
}

.context-menu .item:hover {
  background: #f1f5f9;
}

.context-menu .item.danger {
  color: #ef4444;
}

.context-menu .item.danger:hover {
  background: #fef2f2;
}

.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 4px 0;
}
</style>
