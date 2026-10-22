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
import { templatesFaq } from '../content/templatesFaq'

const templatesTocItems = [
  { href: '#tpl-why', label: 'Зачем нужен шаблон учёта' },
  { href: '#tpl-structure', label: 'Структура таблицы' },
  { href: '#tpl-build', label: 'Как составить таблицу' },
  { href: '#tpl-online', label: 'От шаблона к онлайн-учёту' },
  { href: '#tpl-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Материалы · шаблоны"
        title="Шаблоны и таблицы для учёта инвестиций"
        lead="Шаблон для учёта инвестиций — это не «магический файл», а понятная структура: какие колонки завести, как фиксировать сделки и как не потерять сверку с брокером. Ниже — практичная логика таблицы Excel для учёта инвестиций и путь от файла к онлайн-учёту в CapitalView.\n\nСтраница отвечает на запросы вроде «шаблоны для учета инвестиций», «таблица эксель для учета инвестиций» и «учет инвестиций скачать таблицу»: сначала ясная модель, затем — регистрация и ведение портфеля в сервисе."
      />

      <SeoPageToc aria-label="Разделы о шаблонах" :items="templatesTocItems" />

      <SeoPageSection section-id="tpl-why" title="Зачем нужен шаблон учёта инвестиций">
        <p>
          Без шаблона таблица быстро превращается в хаос: сегодня одна колонка «сумма», завтра — другая валюта,
          послезавтра — забытая комиссия. Готовая структура экономит время и снижает ошибки в
          <strong>ведении учёта инвестиций</strong>.
        </p>
        <p>Шаблон помогает:</p>
        <ul>
          <li>одинаково записывать покупки, продажи и выплаты;</li>
          <li>сверять остатки с брокерской выпиской;</li>
          <li>подготовить данные к переносу в сервис без переименования всего подряд.</li>
        </ul>
        <SeoPageTip>
          Даже если цель — учёт онлайн, короткий этап с таблицей полезен: вы осознанно выбираете, что считать
          операцией и что — справочной информацией.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="tpl-structure" title="Структура таблицы для учёта инвестиций">
        <p>
          Универсальный <strong>файл-шаблон для учёта инвестиций</strong> почти всегда строится вокруг журнала
          операций. Рекомендуемый минимум колонок:
        </p>
        <ul>
          <li>дата и тип операции;</li>
          <li>инструмент (тикер / название);</li>
          <li>количество, цена, сумма;</li>
          <li>комиссия, налог (если учитываете), валюта;</li>
          <li>счёт или брокер — если их несколько.</li>
        </ul>
        <p>
          Второй лист — «позиции» или «сводка»: текущие остатки и доли. Его либо считают из журнала, либо
          обновляют вручную после сверки — но не ведут в отрыве от операций.
        </p>
        <p>
          Подробнее про лимиты таблиц и миграцию — в гайде по Excel:
        </p>
        <SeoArticleLinkCard
          :to="{ name: 'site-guide-excel' }"
          title="Учёт инвестиций в Excel — CapitalView"
        />
      </SeoPageSection>

      <SeoPageSection section-id="tpl-build" title="Как составить таблицу учёта инвестиций">
        <SeoPageStepFlow layout="grid" aria-label="Как собрать шаблон">
          <SeoPageStepFlowItem :step="1" title="Выберите инструмент.">
            <p>Excel или Google Sheets — главное, чтобы файл был доступен с устройств, где вы реально обновляете учёт.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Заведите журнал.">
            <p>Одну строку — одно событие. Не смешивайте покупку и дивиденд в одной записи.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Внесите текущее состояние.">
            <p>Остатки и недавние сделки — чтобы таблица сразу отражала реальность, а не «идеальный» пустой шаблон.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Закрепите правило обновления.">
            <p>Например: после каждой сделки или раз в неделю — иначе шаблон быстро устареет.</p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
      </SeoPageSection>

      <SeoPageSection section-id="tpl-online" title="От шаблона к онлайн-учёту в CapitalView">
        <p>
          Шаблон хорош как старт. Когда нужно видеть дашборд, структуру портфеля и аналитику без ручных формул —
          логичный следующий шаг — <strong>учёт инвестиций онлайн</strong> в CapitalView.
        </p>
        <p>
          Создайте аккаунт, заведите портфель и перенесите операции из таблицы. Новым пользователям доступен
          пробный период с полным доступом — детали на
          <router-link :to="{ path: '/', hash: '#pricing' }" class="seo-inline-link">странице тарифов</router-link>
          и на странице про пробный доступ.
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

      <SeoPageSection section-id="tpl-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="templatesFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Вести учёт инвестиций онлайн"
        text="Соберите структуру в таблице — и перенесите сделки в CapitalView: дашборд, активы и аналитика без постоянной правки формул."
        primary-text="Зарегистрироваться"
        secondary-text="Гайд по Excel"
        secondary-to="/guides/investment-tracking-excel"
      />
    </article>
  </SiteSeoPage>
</template>
