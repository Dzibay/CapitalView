<script setup>
import FaqAccordion from '../../components/faq/FaqAccordion.vue'
import SiteSeoPage from '../components/SiteSeoPage.vue'
import SeoPageHero from '../components/seo/SeoPageHero.vue'
import SeoPageSection from '../components/seo/SeoPageSection.vue'
import SeoPageToc from '../components/seo/SeoPageToc.vue'
import SeoPageTip from '../components/seo/SeoPageTip.vue'
import SeoPageStepFlow from '../components/seo/SeoPageStepFlow.vue'
import SeoPageStepFlowItem from '../components/seo/SeoPageStepFlowItem.vue'
import SeoArticleLinkCard from '../components/seo/SeoArticleLinkCard.vue'
import SeoPageCtaCard from '../components/seo/SeoPageCtaCard.vue'
import { freePageFaq } from '../content/freePageFaq'

const freeTocItems = [
  { href: '#free-what', label: 'Что значит «учёт инвестиций бесплатно»' },
  { href: '#free-trial', label: 'Пробный полный доступ' },
  { href: '#free-vs-download', label: 'Пробный период vs «скачать бесплатно»' },
  { href: '#free-start', label: 'Как начать' },
  { href: '#free-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Тарифы · пробный доступ"
        title="Бесплатный учёт инвестиций: пробный период CapitalView"
        lead="Искали «учёт инвестиций бесплатно» или «бесплатное приложение инвестиции»? CapitalView даёт новым пользователям пробный период с полным доступом ко всем функциям — это не «бесплатно навсегда», а честный способ попробовать сервис учёта инвестиций онлайн без урезанной демо-версии.\n\nПосле окончания trial нужна подписка (оплата через YooKassa). Ниже — чем пробный доступ отличается от скачивания таблицы, что входит в период и как стартовать."
      />

      <SeoPageToc aria-label="Разделы о пробном доступе" :items="freeTocItems" />

      <SeoPageSection section-id="free-what" title="Что значит «учёт инвестиций бесплатно» у нас">
        <p>
          В поиске «учёт инвестиций бесплатно» часто ждут либо вечный бесплатный тариф, либо файл «скачать и
          забыть». CapitalView устроен иначе:
        </p>
        <ul>
          <li>
            <strong>пробный период</strong> — полный функционал сервиса для новых пользователей;
          </li>
          <li>
            далее — <strong>платная подписка</strong>, если хотите продолжить вести портфель в приложении;
          </li>
          <li>
            длительность trial и актуальные условия смотрите в блоке
            <router-link :to="{ path: '/', hash: '#pricing' }" class="seo-inline-link">тарифов на главной</router-link>.
          </li>
        </ul>
        <SeoPageTip>
          Мы не обещаем «сервис учёта инвестиций бесплатно навсегда»: зато в пробном периоде вы видите продукт
          целиком — дашборд, сделки, аналитику и дивидендный контур.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="free-trial" title="Пробный полный доступ">
        <p>В пробный период обычно входит то же, чем пользуются подписчики:</p>
        <ul>
          <li>учёт портфеля, активов и операций;</li>
          <li>аналитика и обзор доходности;</li>
          <li>дивиденды и выплаты в рамках возможностей сервиса;</li>
          <li>доступные сценарии импорта (например, из поддерживаемых брокеров).</li>
        </ul>
        <p>
          Это ответ на запрос «бесплатное приложение инвестиции» в практическом смысле: вы пробуете полноценный
          веб-сервис, а не урезанный режим «только три актива».
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="free-vs-download" title="Пробный период vs «скачать бесплатно»">
        <p>
          Запросы вроде «учёт инвестиций скачать» или «бесплатно учёт инвестиции скачать» часто ведут к Excel-файлу.
          Сравнение честное:
        </p>
        <ul>
          <li>
            <strong>Скачать таблицу</strong> — бесплатно и навсегда, но учёт, формулы и сверки остаются на вас.
          </li>
          <li>
            <strong>Пробный CapitalView</strong> — бесплатно на ограниченный срок, зато сразу интерфейс, сводка
            портфеля и готовые сценарии учёта.
          </li>
        </ul>
        <p>
          Если нужен именно файл — начните с
          <router-link :to="{ name: 'site-templates' }" class="seo-inline-link">шаблонов</router-link>
          и
          <router-link :to="{ name: 'site-guide-excel' }" class="seo-inline-link">гайда по Excel</router-link>.
          Если хотите сервис — регистрируйтесь и используйте пробный период.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-templates' }"
            title="Шаблоны для учёта инвестиций — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-guide-excel' }"
            title="Учёт инвестиций в Excel — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="free-start" title="Как начать">
        <SeoPageStepFlow layout="grid" aria-label="Старт пробного периода">
          <SeoPageStepFlowItem :step="1" title="Регистрация.">
            <p>
              Создайте аккаунт на странице
              <router-link :to="{ path: '/login' }" class="seo-inline-link">входа</router-link>.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Портфель и сделки.">
            <p>Заведите портфель, добавьте активы и операции — вручную или через доступный импорт.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Проверка дашборда.">
            <p>Сверьте стоимость и позиции с брокером, пока идёт пробный период.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Тарифы.">
            <p>
              Когда решите продолжить — условия подписки на
              <router-link :to="{ path: '/', hash: '#pricing' }" class="seo-inline-link">/#pricing</router-link>.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
      </SeoPageSection>

      <SeoPageSection section-id="free-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="freePageFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Начать пробный период"
        text="Зарегистрируйтесь и получите полный доступ к учёту инвестиций на время trial. После — подписка, если сервис вам подходит."
        primary-text="Войти / зарегистрироваться"
        primary-to="/login"
        secondary-text="Смотреть тарифы"
        :secondary-to="{ path: '/', hash: '#pricing' }"
      />
    </article>
  </SiteSeoPage>
</template>
