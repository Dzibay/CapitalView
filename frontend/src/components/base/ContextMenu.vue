<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { Briefcase, TrendingUp, Receipt, DollarSign, PlusCircle, BarChart3, MoveRight, Trash2, Edit, RotateCcw, RefreshCw } from 'lucide-vue-next'
import { useContextMenu } from '../../composables/useContextMenu'
import { isDepositLikePortfolioAsset } from '../../utils/depositAssetType'

const emit = defineEmits([
  'clearPortfolio',
  'refreshPortfolio',
  'deletePortfolio',
  'addTransaction',
  'addPrice',
  'moveAsset',
  'removeAsset',
  'editTransaction',
  'deleteTransaction',
  'deleteOperation'
])

const { menu, closeMenu } = useContextMenu()
const menuRef = ref(null)

const onClickOutside = (event) => {
  // Не закрываем меню, если клик был на элементе, который открывает меню
  if (menu.value.triggerElement && menu.value.triggerElement.contains(event.target)) {
    return
  }
  // Не закрываем меню, если клик был внутри самого меню
  if (menuRef.value && menuRef.value.contains(event.target)) {
    return
  }
  closeMenu()
}

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
          <Briefcase :size="18" class="menu-icon" />
          <span class="menu-title">Портфель</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('clearPortfolio', menu.payload.id)">
          <RotateCcw :size="16" class="item-icon" />
          <span class="item-text">Очистить</span>
        </button>
        <button class="item" @click="closeMenu(); $emit('refreshPortfolio', menu.payload.id)">
          <RefreshCw :size="16" class="item-icon" />
          <span class="item-text">Обновить</span>
        </button>
        <button 
          v-if="menu.payload.parent_portfolio_id" 
          class="item danger" 
          @click="closeMenu(); $emit('deletePortfolio', menu.payload.id)"
        >
          <Trash2 :size="16" class="item-icon" />
          <span class="item-text">Удалить</span>
        </button>
      </template>

      <!-- Актив -->
      <template v-if="menu.type === 'asset'">
        <div class="menu-header">
          <TrendingUp :size="18" class="menu-icon" />
          <span class="menu-title">Актив</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('addTransaction', menu.payload)">
          <PlusCircle :size="16" class="item-icon" />
          <span class="item-text">Добавить транзакцию</span>
        </button>
        <!-- Скрываем «Изменить цену» для системных активов и для вкладов -->
        <button 
          v-if="menu.payload?.asset?.is_custom !== false && menu.payload?.is_custom !== false && !isDepositLikePortfolioAsset(menu.payload?.asset ?? menu.payload)"
          class="item" 
          @click="closeMenu(); $emit('addPrice', menu.payload)"
        >
          <BarChart3 :size="16" class="item-icon" />
          <span class="item-text">Изменить цену</span>
        </button>
        <button class="item" @click="closeMenu(); $emit('moveAsset', menu.payload)">
          <MoveRight :size="16" class="item-icon" />
          <span class="item-text">Переместить</span>
        </button>
        <div class="divider"></div>
        <button class="item danger" @click="closeMenu(); $emit('removeAsset', menu.payload.portfolio_asset_id)">
          <Trash2 :size="16" class="item-icon" />
          <span class="item-text">Удалить</span>
        </button>
      </template>

      <!-- Транзакция -->
      <template v-if="menu.type === 'transaction'">
        <div class="menu-header">
          <Receipt :size="18" class="menu-icon" />
          <span class="menu-title">Транзакция</span>
        </div>
        <div class="divider"></div>
        <button class="item" @click="closeMenu(); $emit('editTransaction', menu.payload)">
          <Edit :size="16" class="item-icon" />
          <span class="item-text">Редактировать</span>
        </button>
        <button class="item danger" @click="closeMenu(); $emit('deleteTransaction', menu.payload)">
          <Trash2 :size="16" class="item-icon" />
          <span class="item-text">Удалить</span>
        </button>
      </template>

      <!-- Операция -->
      <template v-if="menu.type === 'operation'">
        <div class="menu-header">
          <DollarSign :size="18" class="menu-icon" />
          <span class="menu-title">Операция</span>
        </div>
        <div class="divider"></div>
        <button class="item danger" @click="closeMenu(); $emit('deleteOperation', menu.payload)">
          <Trash2 :size="16" class="item-icon" />
          <span class="item-text">Удалить</span>
        </button>
      </template>
    </div>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  background: white;
  border-radius: 12px;
  min-width: 200px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 0 0 1px rgba(0, 0, 0, 0.05);
  z-index: 9999;
  padding: 6px;
  animation: contextMenuFadeIn 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
  max-width: calc(100vw - 16px);
  overflow: hidden;
}

@keyframes contextMenuFadeIn {
  from {
    opacity: 0;
    transform: scale(0.95) translateY(-4px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.menu-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  margin: -2px -2px 4px;
  background: #f9fafb;
  border-bottom: 1px solid #f3f4f6;
}

.menu-icon {
  color: #3b82f6;
  flex-shrink: 0;
}

.menu-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  letter-spacing: -0.01em;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.context-menu .item {
  width: 100%;
  padding: 9px 12px;
  background: none;
  border: none;
  text-align: left;
  font-size: 13px;
  cursor: pointer;
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: all 0.15s ease;
  color: #374151;
  font-weight: 500;
  margin: 1px 0;
}

.context-menu .item:hover {
  background: #f3f4f6;
  color: #111827;
}

.context-menu .item:active {
  background: #e5e7eb;
  transform: scale(0.98);
}

.item-icon {
  color: #6b7280;
  flex-shrink: 0;
}

.context-menu .item:hover .item-icon {
  color: #374151;
}

.item-text {
  flex: 1;
  letter-spacing: -0.01em;
}

.context-menu .item.danger {
  color: #dc2626;
}

.context-menu .item.danger .item-icon {
  color: #dc2626;
}

.context-menu .item.danger:hover {
  background: #fef2f2;
  color: #dc2626;
}

.context-menu .item.danger:hover .item-icon {
  color: #dc2626;
}

.divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #e5e7eb, transparent);
  margin: 4px 0;
  border: none;
}
</style>
