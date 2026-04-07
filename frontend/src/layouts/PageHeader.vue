<template>
  <div class="page-header">
    <div class="page-header-content">
      <!-- Первый уровень: заголовок + переключатель (actions) -->
      <div class="page-header-row1">
        <div class="page-header-title">
          <h1>{{ title }}</h1>
          <h2 v-if="subtitle">{{ subtitle }}</h2>
        </div>
        <div v-if="$slots.actions" class="page-header-actions">
          <slot name="actions" />
        </div>
      </div>
      <!-- Второй уровень при сужении: только меню кнопок -->
      <div v-if="$slots.menu" class="page-header-menu">
        <slot name="menu" />
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    required: true
  },
  subtitle: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
.page-header {
  margin-bottom: var(--spacing);
}

/* Широкий экран: [ заголовок + переключатель | меню кнопок ] в одну строку */
.page-header-content {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: nowrap;
}

/* Первый уровень: заголовок и actions (переключатель) */
.page-header-row1 {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  min-width: 0;
  width: 100%;
  max-width: 100%;
}

.page-header-title {
  flex: 1 1 auto;
  min-width: 0;
}

.page-header h1 {
  font-size: var(--text-heading-1-size);
  font-weight: var(--text-heading-1-weight);
  color: var(--text-heading-1-color);
  margin: 0;
  line-height: var(--text-heading-1-line);
}

.page-header h2 {
  font-size: var(--text-heading-2-size);
  font-weight: var(--text-heading-2-weight);
  color: var(--text-heading-2-color);
  margin: 0;
  margin-top: 0.25rem;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
  flex: 0 0 auto;
  margin-left: auto;
  width: fit-content;
  max-width: 100%;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  /* Одна строка: подзаголовок слева на всё свободное место, actions справа по содержимому */
  .page-header-row1 {
    flex-wrap: nowrap;
    align-items: center;
    gap: 0.75rem;
  }

  .page-header-title {
    flex: 1 1 auto;
    min-width: 0;
    width: auto;
  }

  .page-header-actions {
    flex: 0 0 auto;
    width: fit-content;
    max-width: 100%;
    margin-left: auto;
    justify-content: flex-end;
  }

  /* Крупный заголовок убираем, если есть подзаголовок — на мобильном виден только h2 */
  .page-header-title:has(h2) h1 {
    display: none;
  }

  .page-header-title:has(h2) h2 {
    margin-top: 0;
  }
}

/* Меню кнопок: одна строка, не переносим кнопки внутри */
.page-header-menu {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: nowrap;
  min-width: 0;
  flex-shrink: 0;
}

/* Меню кнопок переходит вниз до наезда на «Показать проданные активы» */
@media (max-width: 1240px) {
  .page-header-content {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }

  .page-header-menu {
    width: 100%;
    max-width: 100%;
  }
}

/* Очень узкий экран: кнопкам разрешаем перенос, чтобы не уезжали за край */
@media (max-width: 480px) {
  .page-header-menu {
    flex-wrap: wrap;
  }
}
</style>
