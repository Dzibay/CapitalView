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
import { guideExcelFaq } from '../content/guideExcelFaq'

const excelTocItems = [
  { href: '#excel-why', label: 'Зачем вести учёт инвестиций в Excel' },
  { href: '#excel-table', label: 'Какой должна быть таблица' },
  { href: '#excel-limits', label: 'Лимиты таблиц и типичные ошибки' },
  { href: '#excel-migrate', label: 'Переход из Excel в CapitalView' },
  { href: '#excel-templates', label: 'Шаблоны и готовые колонки' },
  { href: '#excel-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Гайд · Excel и таблицы"
        title="Учёт инвестиций в Excel: таблицы, лимиты и переход в сервис"
        lead="Учёт инвестиций в Excel — привычный старт: одна таблица, свои формулы, полный контроль. Пока позиций немного, это работает. Когда появляются несколько счетов, валюты, дивиденды и десятки сделок, таблица для учёта инвестиций начинает «сыпаться»: цены устаревают, доли считаются вручную, сверка с брокером превращается в вечернюю рутину.\n\nНиже — как устроена нормальная таблица для учёта инвестиций в Excel, где таблицы упираются в потолок и как перенести данные в CapitalView, не потеряв историю. Если искали «учёт инвестиций excel скачать» или готовый шаблон — загляните также на страницу шаблонов."
      />

      <SeoPageToc aria-label="Разделы гайда" :items="excelTocItems" />

      <SeoPageSection section-id="excel-why" title="Зачем вести учёт инвестиций в Excel">
        <p>
          Таблица даёт свободу: вы сами решаете, как считать доходность, какие колонки нужны и что считать
          «истиной». Для многих это и есть ответ на вопрос
          <strong>как вести учёт инвестиций в Excel</strong> на старте — без подписок и новых интерфейсов.
        </p>
        <p>Excel (или Google Sheets) удобен, когда:</p>
        <ul>
          <li>портфель небольшой и сделки редкие;</li>
          <li>нужен свой сценарий или модель, которой нет в приложении;</li>
          <li>хочется сначала понять логику учёта, а потом выбрать сервис.</li>
        </ul>
        <SeoPageTip>
          Таблица хорошо учит дисциплине: дата, цена, количество, комиссия. Эти же поля потом переносятся в
          онлайн-учёт без смены мышления.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="excel-table" title="Какой должна быть таблица для учёта инвестиций">
        <p>
          Минимально полезная <strong>таблица для учёта инвестиций в Excel</strong> обычно содержит журнал операций
          и (опционально) снимок позиций. Без журнала сложно восстановить, почему изменилась стоимость портфеля.
        </p>
        <p>Базовые колонки журнала:</p>
        <ul>
          <li><strong>дата</strong> операции;</li>
          <li><strong>инструмент</strong> (тикер / название / ISIN);</li>
          <li><strong>тип</strong>: покупка, продажа, дивиденд, купон, комиссия, пополнение;</li>
          <li><strong>количество</strong> и <strong>цена</strong>;</li>
          <li><strong>комиссия</strong> и <strong>валюта</strong>;</li>
          <li>при необходимости — счёт или брокер.</li>
        </ul>
        <p>
          Отдельный лист «позиции» удобен для текущих остатков и долей, но его лучше считать из журнала или
          регулярно сверять с брокером — иначе два листа быстро разойдутся.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="excel-limits" title="Лимиты таблиц и типичные ошибки">
        <p>
          <strong>Таблицы для учёта инвестиций</strong> редко ломаются из‑за «плохого Excel» — чаще из‑за роста
          сложности учёта. Типичные точки боли:
        </p>
        <ul>
          <li>ручное обновление котировок и курсов валют;</li>
          <li>дивиденды и корпоративные действия, которые забыли внести;</li>
          <li>несколько брокеров без единого среза портфеля;</li>
          <li>формулы доходности, которые считают «не то», что ожидаете;</li>
          <li>копии файла «на всякий случай» и потеря актуальной версии.</li>
        </ul>
        <SeoPageTip>
          Если вы больше часа в месяц тратите на правку формул и сверку остатков, чем на решения по портфелю —
          это сигнал перенести фактический учёт в сервис.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="excel-migrate" title="Переход из Excel в CapitalView">
        <p>
          Переезд не обязан быть «большим взрывом». Практичный порядок для тех, кто уже вёл
          <strong>учёт инвестиций в Excel</strong>:
        </p>
        <SeoPageStepFlow layout="grid" aria-label="Шаги перехода из Excel">
          <SeoPageStepFlowItem :step="1" title="Зафиксируйте правила.">
            <p>
              Какие операции считаются обязательными, в какой валюте смотрите портфель, как учитываете комиссии.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Создайте портфель.">
            <p>
              Зарегистрируйтесь и заведите портфель в CapitalView —
              <router-link :to="{ path: '/login' }" class="seo-inline-link">вход и регистрация</router-link>.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Перенесите ядро.">
            <p>
              Текущие позиции и недавние сделки — достаточно, чтобы дашборд стал похож на брокерскую картину.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Догрузите историю.">
            <p>
              Старые операции — пакетами. Excel можно оставить архивом или листом для сценариев.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
        <p>
          Подробнее про логику объектов учёта в сервисе — в обзоре портфеля:
        </p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-portfolio' }"
          title="Учёт инвестиций в CapitalView — обзор сервиса"
        />
      </SeoPageSection>

      <SeoPageSection section-id="excel-templates" title="Шаблоны и готовые колонки">
        <p>
          Если искали «учёт инвестиций скачать таблицу» или шаблон под Excel — начните со страницы шаблонов:
          там разобрано, как составить таблицу учёта инвестиций и чем шаблон отличается от онлайн-учёта.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-templates' }"
            title="Шаблоны для учёта инвестиций — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-free' }"
            title="Пробный учёт инвестиций — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="excel-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="guideExcelFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Перейти от таблицы к учёту в CapitalView"
        text="Создайте аккаунт, перенесите ключевые сделки из Excel и держите портфель, активы и аналитику в одном сервисе — таблицу можно оставить архивом."
        primary-text="Зарегистрироваться"
        secondary-text="Шаблоны для учёта"
        secondary-to="/templates"
      />
    </article>
  </SiteSeoPage>
</template>
