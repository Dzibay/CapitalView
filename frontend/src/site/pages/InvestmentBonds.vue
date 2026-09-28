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
import { investmentBondsFaq } from '../content/investmentBondsFaq'

const bondsTocItems = [
  { href: '#bonds-why', label: 'Зачем учитывать облигации отдельно' },
  { href: '#bonds-what', label: 'Что фиксировать: цена, купоны, погашение' },
  { href: '#bonds-yield', label: 'Доходность облигаций в учёте' },
  { href: '#bonds-start', label: 'С чего начать учёт облигаций' },
  { href: '#bonds-coupons', label: 'Купоны и календарь выплат' },
  { href: '#bonds-buy', label: 'Покупка облигаций и портфель' },
  { href: '#bonds-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Инвестиции · облигации"
        title="Учёт инвестиций в облигации"
        lead="Купоны, НКД, погашения и оферты — у облигаций денежный поток важнее «красивого графика цены». CapitalView помогает вести учёт инвестиций в облигации: позиции, сделки, купонные выплаты и итоговую доходность в одной модели портфеля.\n\nНиже — что обязательно отражать в учёте, как не потерять купоны, чем смотреть доходность облигаций и куда перейти за календарём выплат."
      />

      <SeoPageToc aria-label="Разделы страницы" :items="bondsTocItems" />

      <SeoPageSection section-id="bonds-why" title="Зачем учитывать облигации отдельно от «просто цены»">
        <p>
          <strong>Инвестиции в облигации</strong> часто выбирают ради предсказуемых выплат и возврата номинала. Если
          в учёте видна только рыночная цена, легко недооценить или переоценить результат: купон «на карту» не попал в
          историю, погашение не отражено, комиссия съела часть дохода.
        </p>
        <p>
          <strong>Учёт инвестиций в облигации</strong> связывает покупку бумаги с графиком выплат и финальным
          погашением (или продажей). Так портфель остаётся сопоставимым с брокерской выпиской и понятным через годы.
        </p>
        <SeoPageTip>
          Облигации хорошо сочетаются с акциями в одном портфеле — но чек-лист контроля разный. Для акций важнее
          средняя и дивиденды, для облигаций — купоны и даты погашения.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection
        section-id="bonds-what"
        title="Что фиксировать: цена, купоны, погашение"
      >
        <p>Базовый набор для честного учёта:</p>
        <ul>
          <li>дата, цена и количество при покупке или продаже;</li>
          <li>комиссия и прочие издержки сделки;</li>
          <li>купонные выплаты по факту поступления;</li>
          <li>погашение номинала, оферта или досрочный выкуп;</li>
          <li>при необходимости — НКД в момент сделки, если вы его учитываете явно.</li>
        </ul>
        <p>
          Без купонов и погашения даже аккуратная цена входа не даст полной картины. Именно поэтому
          <strong>учёт</strong> облигаций шире, чем реестр тикеров: это ещё и журнал денежных событий по бумаге.
        </p>
        <p>
          Общая логика портфеля и операций —
          <router-link :to="{ name: 'site-feature-portfolio' }" class="seo-inline-link">обзор учёта инвестиций</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="bonds-yield" title="Доходность облигаций в учёте">
        <p>
          <strong>Доходность облигаций</strong> на практике складывается из купонного потока, разницы между ценой
          покупки и погашением (или продажей) и издержек. В сервисе удобно смотреть вклад бумаги в портфель и не
          терять «тихие» выплаты, которые не двигают котировку каждый день.
        </p>
        <p>
          Кластер запросов вроде «доходность инвестиций облигаций» обычно означает одно: инвестору нужна не только
          YTM «с витрины», а фактический результат по своим сделкам. Для этого история должна быть полной — иначе
          метрики будут красивыми, но чужими.
        </p>
        <SeoPageTip>
          Сверяйте крупные купонные поступления с брокером в день выплаты или на следующий рабочий день — так проще
          поймать пропуск в учёте, пока событие свежее.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="bonds-start" title="С чего начать учёт инвестиций в облигации">
        <SeoPageStepFlow layout="grid" aria-label="Порядок учёта облигаций">
          <SeoPageStepFlowItem :step="1" title="Портфель.">
            <p>
              Войдите и создайте портфель —
              <router-link :to="{ path: '/login' }" class="seo-inline-link">регистрация и вход</router-link>.
              Задайте валюту отображения для сверки с отчётами.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Позиции.">
            <p>
              Добавьте облигации, которые уже есть на счетах. Отметьте для себя ближайшие купоны и дату погашения.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Сделки.">
            <p>
              Внесите покупки и продажи с комиссиями. Если докупали одну и ту же бумагу несколько раз — отразите
              каждую операцию отдельно.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Выплаты.">
            <p>
              Подтяните уже полученные <strong>купоны</strong> и проверьте, что номинал при погашении тоже попал в
              историю.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
      </SeoPageSection>

      <SeoPageSection section-id="bonds-coupons" title="Купоны и календарь выплат">
        <p>
          Купонный контур — сердце <strong>учёта инвестиций в облигации</strong>. Пропущенная выплата искажает и
          доходность, и сравнение с акциями в смешанном портфеле. В CapitalView сценарии дивидендов и купонов
          собраны в отдельном разделе продукта.
        </p>
        <p>Подробнее про выплаты:</p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-dividends' }"
          title="Дивиденды и купоны — CapitalView"
        />
        <p>
          Если параллельно держите акции, полезны также страницы по
          <router-link :to="{ name: 'site-investment-stocks' }" class="seo-inline-link">учёту акций</router-link>
          и
          <router-link :to="{ name: 'site-investment-securities' }" class="seo-inline-link">ценным бумагам в целом</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="bonds-buy" title="Покупка облигаций и место в портфеле">
        <p>
          Запросы вроде «купить облигации инвестиции» обычно про выбор бумаги и брокера. Учёт не заменяет инвестиционное
          решение, но помогает после покупки: зафиксировать вход, не потерять купоны и видеть долю облигаций рядом с
          акциями.
        </p>
        <ul>
          <li>после сделки сразу внесите операцию — не копите «хвосты»;</li>
          <li>отметьте ближайшую купонную дату в своей рутине контроля;</li>
          <li>раз в квартал смотрите, не разъехались ли доли классов бумаг относительно цели.</li>
        </ul>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-portfolio' }"
            title="Учёт инвестиций в CapitalView: обзор сервиса"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-dividends' }"
            title="Дивиденды и купоны — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="bonds-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="investmentBondsFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Вести учёт облигаций в CapitalView"
        text="Создайте портфель, добавьте позиции и купоны — так доходность облигаций и денежный поток остаются под контролем."
        primary-text="Зарегистрироваться"
        primary-to="/login"
        secondary-text="Обзор учёта портфеля"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
