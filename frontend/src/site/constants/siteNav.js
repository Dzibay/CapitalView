/**
 * Верхнее меню сайта — 3 пункта с выпадающим списком.
 * Заголовки и подписи ориентированы на кластер Wordstat «учёт инвестиций»:
 * портфель и доходность, акции/облигации/ЦБ, сравнение сервиса с Excel и шаблонами.
 * Раздел «Тарифы» в меню скрыт (блок на главной #pricing и страница /free доступны с главной и из футера).
 *
 * pathPrefixes — подсветка активного раздела по текущему пути.
 */
export const siteNavTopMenu = [
  {
    label: 'Учёт портфеля',
    to: '/features/portfolio',
    pathPrefixes: ['/features'],
    items: [
      { to: '/features/analytics', label: 'Аналитика и доходность' },
      { to: '/features/dividends', label: 'Дивиденды и купоны' },
      { to: '/features/transactions', label: 'Сделки и операции' },
    ],
  },
  {
    label: 'Акции и облигации',
    to: '/investments/securities',
    pathPrefixes: ['/investments'],
    items: [
      { to: '/investments/stocks', label: 'Учёт акций' },
      { to: '/investments/bonds', label: 'Учёт облигаций' },
    ],
  },
  {
    label: 'Сервис и гайды',
    to: '/guides/investment-tracking-excel',
    pathPrefixes: ['/guides', '/templates', '/blog'],
    items: [
      { to: '/templates', label: 'Шаблоны для учёта' },
      { to: '/blog', label: 'Блог и статьи' },
    ],
  },
]
