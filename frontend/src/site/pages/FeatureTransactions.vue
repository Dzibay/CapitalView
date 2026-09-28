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
import SeoPageVisual from '../components/seo/SeoPageVisual.vue'
import SeoPageCtaCard from '../components/seo/SeoPageCtaCard.vue'
import { featureTransactionsFaq } from '../content/featureTransactionsFaq'

const transactionsTocItems = [
  { href: '#tx-role', label: 'Зачем журнал сделок и операций' },
  { href: '#tx-broker', label: 'Брокерский счёт и учёт на бирже' },
  { href: '#tx-fees', label: 'Комиссии: что обязательно отражать' },
  { href: '#tx-howto', label: 'Как вести операции без хвостов' },
  { href: '#tx-related', label: 'Связь с активами и аналитикой' },
  { href: '#tx-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Справка · сделки и операции"
        title="Сделки и операции: учёт на бирже, комиссии и брокерский счёт"
        lead="Портфель честен ровно настолько, насколько полна история операций. Сделки по инвестициям, комиссии, пополнения и выплаты — первоисточник для баланса и доходности. CapitalView собирает этот журнал рядом с активами, чтобы учёт инвестиций на бирже не расходился с брокерским счётом.\n\nДальше — как устроен контур операций, почему комиссии по инвестициям нельзя «оставлять на потом», и какой порядок сверки помогает держать данные живыми. Если вы переходите с выписок или Excel, оглавление ниже задаёт маршрут от базовой логики до рутины."
      />

      <SeoPageToc aria-label="Разделы о сделках" :items="transactionsTocItems" />

      <SeoPageSection
        section-id="tx-role"
        title="Зачем журнал сделок и операций"
      >
        <p>
          Раздел сделок — это лента фактов: покупка, продажа, комиссия, дивиденд, купон, перевод денег. Именно она
          питает оценку позиций и аналитику. Без аккуратных записей «красивый» дашборд быстро начинает врать.
        </p>
        <p>
          <strong>Сделки по инвестициям</strong> лучше фиксировать атомарно: одно событие — одна запись. Так проще
          искать ошибки, сверяться с брокером и понимать, откуда взялась каждая бумага в портфеле.
        </p>
        <SeoPageTip>
          Если сомневаетесь, вносить ли мелкую комиссию — вносите. Накопленный эффект
          <strong>комиссий по инвестициям</strong> часто заметнее, чем кажется на одной сделке.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection
        section-id="tx-broker"
        title="Брокерский счёт и учёт инвестиций на бирже"
      >
        <p>
          <strong>Инвестиции и брокерский счёт</strong> — связка, от которой отталкивается сверка. Выписка брокера
          остаётся внешним эталоном; CapitalView — рабочая модель, где вы видите те же движения в удобном интерфейсе.
        </p>
        <p>
          <strong>Учёт инвестиций на бирже</strong> в сервисе строится так: позиции растут и уменьшаются из операций,
          денежные остатки отражают пополнения, выводы и выплаты. Чем ближе журнал к отчёту брокера, тем меньше
          «ручных» сюрпризов при ребалансировке.
        </p>
        <ul>
          <li>сверяйте количество бумаг после крупных сделок и корпоративных действий;</li>
          <li>не игнорируйте частичные исполнения и дробные лоты;</li>
          <li>при нескольких счетах держите понятное правило: один портфель или разделение по брокерам.</li>
        </ul>
        <p>
          Общая логика портфеля, активов и дашборда описана в обзоре сервиса:
        </p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-portfolio' }"
          title="Учёт инвестиций в CapitalView: обзор сервиса"
        />
      </SeoPageSection>

      <SeoPageVisual
        placeholder="Скриншот: лента сделок с фильтрами по типу операции и дате"
        caption="Журнал операций удобно проверять рядом с выпиской брокера."
      />

      <SeoPageSection section-id="tx-fees" title="Комиссии: что обязательно отражать">
        <p>
          <strong>Комиссии по инвестициям</strong> и шире — <strong>комиссии биржи и брокера</strong> — часть цены
          владения. Если их нет в истории, доходность завышена, а сравнение стратегий становится нечестным.
        </p>
        <p>Минимальный набор, который стоит отражать:</p>
        <ul>
          <li>комиссия за сделку (покупка / продажа);</li>
          <li>биржевые и депозитарные сборы, если они выделены в отчёте;</li>
          <li>налоги и удержания там, где интерфейс позволяет зафиксировать факт.</li>
        </ul>
        <SeoPageTip>
          Ведите комиссии в той же валюте и дате, что в отчёте брокера — иначе при
          <strong>учёте инвестиций на бирже</strong> появятся «копейки», которые сложно разобрать через месяц.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="tx-howto" title="Как вести операции без хвостов">
        <p>Рабочий порядок, который обычно выдерживают:</p>
        <SeoPageStepFlow layout="grid" aria-label="Порядок ведения операций">
          <SeoPageStepFlowItem :step="1" title="Сразу после сделки.">
            <p>
              Внесите покупку или продажу (или дождитесь импорта, если пользуетесь доступным сценарием).
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Комиссии и налоги.">
            <p>
              Добавьте сопутствующие суммы — без них искажаются и баланс, и аналитика.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Сверка с брокерским счётом.">
            <p>
              Раз в неделю сверьте ключевые позиции и денежный остаток с отчётом брокера.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Выплаты и КД.">
            <p>
              После дивидендов, купонов и сплитов проверьте, что события попали в журнал.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
        <p>
          Если часть истории всё ещё в таблице — можно опереться на шаблоны и постепенно перенести операции в сервис.
        </p>
        <SeoArticleLinkCard
          :to="{ path: '/templates' }"
          title="Шаблоны для учёта инвестиций — CapitalView"
        />
      </SeoPageSection>

      <SeoPageSection section-id="tx-related" title="Связь с активами и аналитикой">
        <p>
          Журнал операций — фундамент: активы показывают «что в портфеле», аналитика — «какой результат», дивиденды —
          «какой денежный поток». Имеет смысл держать все три слоя согласованными.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-analytics' }"
            title="Аналитика и доходность портфеля — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-dividends' }"
            title="Дивиденды и купоны — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="tx-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="featureTransactionsFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Соберите историю операций в CapitalView"
        text="Зарегистрируйтесь и начните вносить сделки — учёт на бирже, комиссии и брокерский счёт перестанут жить в разрозненных выписках."
        primary-text="Зарегистрироваться"
        secondary-text="Шаблоны для учёта"
        secondary-to="/templates"
      />
    </article>
  </SiteSeoPage>
</template>
