// composables/useContextMenu.js
import { ref, nextTick } from 'vue'

const menu = ref({
  open: false,
  type: null,
  x: 0,
  y: 0,
  payload: null,
  position: 'bottom-right', // bottom-right, bottom-left, top-right, top-left
  triggerElement: null // Элемент, который открыл меню
})

// Примерные размеры меню (будут обновлены после рендера)
const MENU_WIDTH = 200
const MENU_ITEM_HEIGHT = 36
const MENU_PADDING = 8
const MENU_OFFSET = 4

export function useContextMenu() {
  const openMenu = (event, type, payload = null) => {
    event.stopPropagation()
    
    // Если меню уже открыто с тем же типом и payload, закрываем его
    if (menu.value.open && menu.value.type === type) {
      // Сравниваем payload по ID для проверки, что это тот же элемент
      const currentId = menu.value.payload?.id || menu.value.payload?.portfolio_asset_id || menu.value.payload?.transaction_id || menu.value.payload?.operation_id
      const newId = payload?.id || payload?.portfolio_asset_id || payload?.transaction_id || payload?.operation_id
      
      if (currentId === newId || (!currentId && !newId)) {
        menu.value.open = false
        return
      }
    }
    
    const rect = event.currentTarget.getBoundingClientRect()
    const viewportWidth = window.innerWidth
    const viewportHeight = window.innerHeight
    
    // Определяем количество элементов меню (оценка высоты для позиционирования)
    let itemCount = 2
    if (type === 'portfolio') {
      // Всегда: clear + refresh, опционально: delete (если есть parent_portfolio_id)
      itemCount = payload?.parent_portfolio_id ? 3 : 2
    } else if (type === 'asset') {
      itemCount = 4 // включая разделитель
    } else if (type === 'transaction') {
      itemCount = 2
    }
    const estimatedHeight = itemCount * MENU_ITEM_HEIGHT + MENU_PADDING * 2
    
    let x = rect.right + MENU_OFFSET
    let y = rect.bottom + MENU_OFFSET
    let position = 'bottom-right'
    
    // Проверяем, помещается ли меню справа
    if (x + MENU_WIDTH > viewportWidth) {
      // Показываем слева от кнопки
      x = rect.left - MENU_WIDTH - MENU_OFFSET
      position = position.replace('right', 'left')
    }
    
    // Если и слева не помещается, прижимаем к краю
    if (x < 0) {
      x = MENU_OFFSET
    }
    
    // Проверяем, помещается ли меню снизу
    if (y + estimatedHeight > viewportHeight) {
      // Показываем сверху от кнопки
      y = rect.top - estimatedHeight - MENU_OFFSET
      position = position.replace('bottom', 'top')
    }
    
    // Если и сверху не помещается, прижимаем к краю
    if (y < 0) {
      y = MENU_OFFSET
    }

    menu.value = {
      open: true,
      type,
      x,
      y,
      payload,
      position,
      triggerElement: event.currentTarget
    }
  }

  const closeMenu = () => {
    menu.value.open = false
    menu.value.triggerElement = null
  }

  return {
    menu,
    openMenu,
    closeMenu
  }
}
