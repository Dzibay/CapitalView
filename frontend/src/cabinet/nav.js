import {
  LayoutDashboard,
  BarChart3,
  Briefcase,
  Coins,
  ArrowLeftRight,
  Settings,
  Shield,
  MessageSquare,
  Headphones,
  CreditCard,
} from 'lucide-vue-next'

/** Доступ закрыт: пользователь без активной подписки. */
export function isLocked(user) {
  return Boolean(user && !user.is_admin && user.subscription && user.subscription.has_access === false)
}

/** Разделы кабинета — общий источник для сайдбара, нижней навигации и ⌘K. */
export function buildNavSections(user) {
  if (user?.is_admin) {
    return [
      {
        title: 'Админ',
        items: [
          { name: 'Статистика', short: 'Админ', link: '/admin', icon: Shield, exact: true },
          { name: 'Сообщения', short: 'Письма', link: '/admin/messages', icon: MessageSquare },
          { name: 'Биллинг', link: '/admin/billing', icon: CreditCard },
        ],
      },
      { title: 'Аккаунт', items: [{ name: 'Настройки', link: '/settings', icon: Settings }] },
    ]
  }
  const locked = isLocked(user)
  return [
    {
      title: 'Обзор',
      items: [
        { name: 'Дашборд', link: '/dashboard', icon: LayoutDashboard, locked, keywords: 'главная обзор' },
        { name: 'Аналитика', link: '/analitics', icon: BarChart3, locked, keywords: 'доходность графики' },
      ],
    },
    {
      title: 'Финансы',
      items: [
        { name: 'Активы', link: '/assets', icon: Briefcase, locked, keywords: 'бумаги позиции портфель' },
        { name: 'Дивиденды', link: '/dividends', icon: Coins, locked, keywords: 'купоны выплаты календарь' },
        { name: 'Операции', link: '/transactions', icon: ArrowLeftRight, locked, keywords: 'сделки транзакции покупки' },
      ],
    },
    {
      title: 'Аккаунт',
      items: [
        { name: 'Подписка', link: '/billing', icon: CreditCard, keywords: 'тариф оплата' },
        { name: 'Поддержка', link: '/support', icon: Headphones, keywords: 'помощь вопрос' },
        { name: 'Настройки', link: '/settings', icon: Settings, keywords: 'профиль брокер импорт' },
      ],
    },
  ]
}

export function isNavActive(item, path) {
  if (item.exact) return path === item.link
  return path === item.link || path.startsWith(`${item.link}/`)
}

/** Подпись страницы для шапки: из meta.title без хвоста « — CapitalView». */
export function pageTitle(route) {
  const t = route?.meta?.title || ''
  return t.replace(/\s+—\s+CapitalView$/, '')
}
