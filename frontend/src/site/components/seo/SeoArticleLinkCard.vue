<script setup>
import { computed } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

const props = defineProps({
  /** Маршрут vue-router (если не задан href) */
  to: {
    type: [String, Object],
    default: null,
  },
  /** Внешняя или абсолютная ссылка; если задана — рендерится <a>, а не RouterLink */
  href: {
    type: String,
    default: '',
  },
  /**
   * Подпись над заголовком (как в превью ссылки).
   * Если не передана — показывается имя сайта (домен): для ссылок внутри приложения — capital-view.ru, для внешних — hostname из URL.
   */
  source: {
    type: String,
    default: undefined,
  },
  /** Заголовок целевой страницы */
  title: {
    type: String,
    required: true,
  },
  /** Иконка в карточке (файл из /public) */
  iconSrc: {
    type: String,
    default: '/favicon-96x96.png',
  },
})

const router = useRouter()

/** Публичный домен сайта (как в index.html canonical) */
const PUBLIC_SITE_HOSTNAME = 'capital-view.ru'

function hostnameFromHref(href) {
  if (!href) return PUBLIC_SITE_HOSTNAME
  if (/^https?:\/\//i.test(href)) {
    try {
      return new URL(href).hostname.replace(/^www\./i, '') || PUBLIC_SITE_HOSTNAME
    } catch {
      return PUBLIC_SITE_HOSTNAME
    }
  }
  return PUBLIC_SITE_HOSTNAME
}

function siteLabelFromTo(to) {
  if (!to) return PUBLIC_SITE_HOSTNAME
  try {
    router.resolve(to)
    return PUBLIC_SITE_HOSTNAME
  } catch {
    return PUBLIC_SITE_HOSTNAME
  }
}

const isExternal = computed(() => Boolean(props.href))
const linkComponent = computed(() => (isExternal.value ? 'a' : RouterLink))
const linkBind = computed(() =>
  isExternal.value ? { href: props.href } : { to: props.to }
)

const displaySource = computed(() => {
  if (props.source != null && props.source !== '') return props.source
  if (props.href) return hostnameFromHref(props.href)
  return siteLabelFromTo(props.to)
})
</script>

<template>
  <component
    :is="linkComponent"
    class="seo-article-card"
    v-bind="linkBind"
  >
    <span class="seo-article-card__icon-wrap" aria-hidden="true">
      <img
        class="seo-article-card__logo"
        :src="iconSrc"
        alt=""
        width="28"
        height="28"
        decoding="async"
        loading="lazy"
      />
    </span>
    <span class="seo-article-card__body">
      <span class="seo-article-card__source">{{ displaySource }}</span>
      <span class="seo-article-card__title">{{ title }}</span>
    </span>
  </component>
</template>

<style scoped>
.seo-article-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 11px 14px;
  width: 100%;
  box-sizing: border-box;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  text-decoration: none;
  color: inherit;
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease,
    box-shadow 0.15s ease;
}

.seo-article-card:hover {
  border-color: rgba(37, 99, 235, 0.35);
  background: rgba(248, 250, 252, 0.98);
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.06);
}

.seo-article-card:focus-visible {
  outline: 2px solid #2563eb;
  outline-offset: 2px;
}

.seo-article-card__icon-wrap {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}

.seo-article-card__logo {
  display: block;
  width: 28px;
  height: 28px;
  object-fit: contain;
}

.seo-article-card__body {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.seo-article-card__source {
  display: block;
  font-size: 12px;
  font-weight: 400;
  color: #757575;
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  direction: ltr;
  unicode-bidi: isolate;
}

.seo-article-card__title {
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  line-height: 1.35;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
