/**
 * Верхнее меню сайта — 3 пункта с выпадающим списком.
 * Заголовки и подписи ориентированы на кластер Wordstat «учёт инвестиций»:
 * портфель и доходность, акции/облигации/ЦБ, сравнение сервиса с Excel и шаблонами.
 * Раздел «Тарифы» в меню скрыт (маршруты /pricing и /free доступны с главной и из футера).
 *
 * pathPrefixes — подсветка активного раздела по текущему пути.
 */
export const siteNavTopMenu = [
  {
    label: 'Учёт портфеля',
    pathPrefixes: ['/features'],
    items: [
      { to: '/features/portfolio', label: 'Инвестиционный портфель' },
      { to: '/features/analytics', label: 'Аналитика и доходность' },
      { to: '/features/dividends', label: 'Дивиденды и купоны' },
      { to: '/features/transactions', label: 'Сделки и операции' },
    ],
  },
  {
    label: 'Акции и облигации',
    pathPrefixes: ['/investments'],
    items: [
      { to: '/investments/stocks', label: 'Учёт акций' },
      { to: '/investments/bonds', label: 'Учёт облигаций' },
      { to: '/investments/securities', label: 'Ценные бумаги' },
    ],
  },
  {
    label: 'Сервис и гайды',
    pathPrefixes: ['/compare', '/guides', '/templates', '/blog'],
    items: [
      { to: '/compare/investment-tracking-apps', label: 'Сравнение сервисов учёта' },
      { to: '/guides/investment-tracking-excel', label: 'Учёт в Excel и таблицах' },
      { to: '/templates', label: 'Шаблоны для учёта' },
      { to: '/blog', label: 'Блог и статьи' },
    ],
  },
]
