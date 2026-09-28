<script setup>
import FaqAccordion from '../../components/faq/FaqAccordion.vue'
import SiteSeoPage from '../components/SiteSeoPage.vue'
import SeoPageHero from '../components/seo/SeoPageHero.vue'
import SeoPageSection from '../components/seo/SeoPageSection.vue'
import SeoPageToc from '../components/seo/SeoPageToc.vue'
import SeoPageTip from '../components/seo/SeoPageTip.vue'
import SeoArticleLinkCard from '../components/seo/SeoArticleLinkCard.vue'
import SeoPageCtaCard from '../components/seo/SeoPageCtaCard.vue'
import { compareAppsFaq } from '../content/compareAppsFaq'

const compareTocItems = [
  { href: '#cmp-criteria', label: 'Критерии сравнения' },
  { href: '#cmp-excel', label: 'Excel и таблицы' },
  { href: '#cmp-apps', label: 'Приложения и сервисы' },
  { href: '#cmp-cv', label: 'Где CapitalView' },
  { href: '#cmp-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Сравнение · обзор"
        title="Excel, приложения и CapitalView: как выбрать учёт инвестиций"
        lead="Краткое сравнение подходов к учёту портфеля: таблица Excel, брокерские и сторонние приложения, сервис CapitalView. Не рейтинг рынка — набор критериев, чтобы понять, что вам нужно сейчас."
      />

      <SeoPageToc aria-label="Разделы сравнения" :items="compareTocItems" />

      <SeoPageSection section-id="cmp-criteria" title="Критерии сравнения">
        <p>Имеет смысл смотреть не на «красоту экрана», а на:</p>
        <ul>
          <li><strong>полноту учёта</strong> — сделки, комиссии, выплаты, несколько счетов;</li>
          <li><strong>сводную картину</strong> — один портфель vs только «свой» брокер;</li>
          <li><strong>трудозатраты</strong> — ручные формулы против готовых экранов;</li>
          <li><strong>стоимость</strong> — бесплатный файл, trial, подписка.</li>
        </ul>
      </SeoPageSection>

      <SeoPageSection section-id="cmp-excel" title="Excel и таблицы">
        <p>
          Плюсы: бесплатно, гибко, привычно. Минусы: котировки, дивиденды и сверки — на вас; при росте портфеля
          растёт риск ошибок. Подробнее —
          <router-link :to="{ name: 'site-guide-excel' }" class="seo-inline-link">гайд по Excel</router-link>
          и
          <router-link :to="{ name: 'site-templates' }" class="seo-inline-link">шаблоны</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="cmp-apps" title="Приложения и сервисы">
        <p>
          Брокерское приложение отлично показывает свой счёт, но редко даёт единый учёт «всех денег и бумаг» в вашей
          логике. Сторонние сервисы закрывают сводку и аналитику — смотрите на импорт, модель операций и прозрачность
          тарифов (trial vs «бесплатно навсегда»).
        </p>
        <SeoPageTip>
          CapitalView не позиционируется как вечно бесплатный: новым пользователям — пробный полный доступ, далее
          подписка. Условия — на
          <router-link :to="{ path: '/', hash: '#pricing' }" class="seo-inline-link">/#pricing</router-link>.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="cmp-cv" title="Где CapitalView">
        <p>
          CapitalView — сервис учёта инвестиций: портфель, активы, сделки, аналитика и дивидендный контур в одном
          интерфейсе. Удобен, если нужен сводный учёт и меньше ручной рутины, чем в таблице.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-portfolio' }"
            title="Учёт инвестиций в CapitalView — обзор сервиса"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-free' }"
            title="Пробный учёт инвестиций — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="cmp-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="compareAppsFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Попробовать CapitalView"
        text="Зарегистрируйтесь и оцените учёт портфеля в пробном периоде — или начните с обзора сервиса."
        primary-text="Зарегистрироваться"
        secondary-text="Обзор учёта"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
