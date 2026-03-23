/**
 * SVG paths в координатах viewBox 0 0 100 100 (preserveAspectRatio none).
 * Как на референсе: 3 дуги слева, 3 справа (зеркально). Сначала почти горизонтальный заход
 * к центру, затем плавный изгиб вниз — сходятся у верхнего края дашборда по центру.
 * Индексы 0–2: слева; 3–5: справа.
 */
export const HERO_ASSET_PATHS = [
  // Левый верх → фокус у дашборда
  'M -6 15 C 48 17 46 42 49 122',
  'M -6 34 C 24 35 44 50 50 123',
  'M -16 55 C 21 52 41 56 51 122',
  // Правый верх (зеркально)
  'M 109 18 C 72 17 54 42 51 122',
  'M 100 34 C 76 35 56 50 50 123',
  'M 112 50 C 79 52 59 56 49 122'
]

/** После интро кубики уже «вошли» в дугу к центру; дорисовка к фокусу — по скроллу */
export const HERO_MOTION_INTRO_PROGRESS = 0.1

/**
 * Иконки на анимированных кубиках героя (WebP в public).
 * Индекс совпадает с HERO_ASSET_PATHS: 0–2 слева, 3–5 справа.
 * Положите файлы в frontend/public/landing/hero-blocks/
 */
export const HERO_BLOCK_WEBP_SRCS = [
  '/landing/hero-blocks/0.webp',
  '/landing/hero-blocks/1.webp',
  '/landing/hero-blocks/2.webp',
  '/landing/hero-blocks/3.webp',
  '/landing/hero-blocks/4.webp',
  '/landing/hero-blocks/5.webp'
]

/**
 * Поворот кубиков (градусы, индекс как у путей).
 * Интерполяция start → end за первые HERO_BLOCK_ROTATION_DURATION доли общего таймлайна (0–1).
 * Чтобы крутить почти весь полёт — поставьте duration ближе к 1.
 */
export const HERO_BLOCK_ROTATION_START_DEG = [-150, 100, -80, 120, -70, 90]
export const HERO_BLOCK_ROTATION_END_DEG = [-15, -11, -9, 10, 5, 6]
export const HERO_BLOCK_ROTATION_DURATION = 0.34
