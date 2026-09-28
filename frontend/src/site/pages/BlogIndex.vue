<script setup>
import FaqAccordion from '../../components/faq/FaqAccordion.vue'
import SiteSeoPage from '../components/SiteSeoPage.vue'
import SeoPageHero from '../components/seo/SeoPageHero.vue'
import SeoPageSection from '../components/seo/SeoPageSection.vue'
import SeoPageToc from '../components/seo/SeoPageToc.vue'
import SeoPageTip from '../components/seo/SeoPageTip.vue'
import SeoArticleLinkCard from '../components/seo/SeoArticleLinkCard.vue'
import SeoPageCtaCard from '../components/seo/SeoPageCtaCard.vue'

const blogTocItems = [
  { href: '#blog-start', label: 'С чего начать новичкам' },
  { href: '#blog-articles', label: 'Материалы и статьи' },
  { href: '#blog-faq', label: 'Короткие ответы' },
]

const blogFaq = [
  {
    question: 'Это полноценный блог со статьями?',
    answer:
      'Пока здесь собраны обзорные материалы CapitalView по учёту портфеля, акциям, облигациям, Excel и аналитике. Отдельные длинные посты появятся позже — эти страницы уже можно читать как стартовый набор «инвестиции для начинающих».',
  },
  {
    question: 'С чего начать, если я только открыл брокерский счёт?',
    answer:
      'Сначала разберитесь, как устроен учёт портфеля и сделок, затем — особенности акций и облигаций. Параллельно решите: ведёте таблицу Excel или сразу онлайн-учёт в сервисе.',
  },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Блог · материалы"
        title="Инвестиции для начинающих: материалы CapitalView"
        lead="Если вы ищете «инвестиции для начинающих», «с чего начать» и базовые ответы про портфель — здесь собраны короткие обзорные статьи CapitalView. Это не финансовый совет и не обещание доходности: фокус на учёте инвестиций, структуре портфеля и понятных следующих шагах.\n\nНиже — вводный маршрут для новичков и карточки материалов. Пока отдельных постов блога ещё нет, эти SEO-страницы работают как статьи по ключевым темам."
      />

      <SeoPageToc aria-label="Разделы блога" :items="blogTocItems" />

      <SeoPageSection section-id="blog-start" title="С чего начать новичкам">
        <p>
          Типичный путь «инвестиции с чего начать» на практике выглядит так: понять, что вы учитываете (деньги,
          бумаги, сделки), завести простой учёт и уже потом углубляться в классы активов и метрики доходности.
        </p>
        <ul>
          <li>
            <strong>Основы учёта</strong> — портфель, активы, операции: без этого сложно понять, «как работают
            инвестиции» именно в вашем случае.
          </li>
          <li>
            <strong>Акции и облигации</strong> — разные потоки дохода и разная логика записей в учёте.
          </li>
          <li>
            <strong>Таблица или сервис</strong> — Excel на старте нормален; когда данных больше, удобнее онлайн-учёт.
          </li>
        </ul>
        <SeoPageTip>
          «Как зарабатывать на инвестициях» начинается не с сложной стратегии, а с дисциплины: знать, что у вас в
          портфеле, сколько вложено и какие были выплаты.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="blog-articles" title="Материалы и статьи">
        <p>
          Подборка обзоров CapitalView — читайте как статьи, пока отдельная лента блога не наполнена:
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-portfolio' }"
            title="Учёт инвестиций в CapitalView — обзор сервиса"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-stocks' }"
            title="Учёт инвестиций в акции — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-bonds' }"
            title="Учёт инвестиций в облигации — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-guide-excel' }"
            title="Учёт инвестиций в Excel — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-analytics' }"
            title="Аналитика и доходность портфеля — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-templates' }"
            title="Шаблоны для учёта инвестиций — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="blog-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="blogFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Начать учёт инвестиций"
        text="Прочитайте обзор портфеля или сразу зарегистрируйтесь: пробный период даёт полный доступ к сервису."
        primary-text="Зарегистрироваться"
        secondary-text="Обзор учёта"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
