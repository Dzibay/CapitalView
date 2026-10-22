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
import { featureAnalyticsFaq } from '../content/featureAnalyticsFaq'

const analyticsTocItems = [
  { href: '#analytics-why', label: 'Зачем нужен учёт доходности' },
  { href: '#analytics-metrics', label: 'Доходность, рентабельность, окупаемость' },
  { href: '#analytics-how', label: 'Как смотреть аналитику в сервисе' },
  { href: '#analytics-quality', label: 'Качество данных и типичные ошибки' },
  { href: '#analytics-related', label: 'Связанные разделы учёта' },
  { href: '#analytics-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Справка · аналитика портфеля"
        title="Аналитика и учёт доходности инвестиций"
        lead="Цифры в брокерском приложении показывают баланс «здесь и сейчас», но редко отвечают, как менялась доходность инвестиций за год, что тянуло результат и окупились ли вложения. CapitalView помогает вести учёт доходности инвестиций и учёт доходов от инвестиций в одном контуре с портфелем и сделками.\n\nНиже — практический обзор: какие метрики смотреть, чем рентабельность отличается от простой прибыли, как подойти к окупаемости инвестиций и как не обмануть себя неполными данными. Если вы искали учёт и анализ инвестиций без бесконечных сводных таблиц — начните с оглавления."
      />

      <SeoPageToc aria-label="Разделы аналитики" :items="analyticsTocItems" />

      <SeoPageSection
        section-id="analytics-why"
        title="Зачем нужен учёт доходности инвестиций"
      >
        <p>
          <strong>Учёт доходности инвестиций</strong> отвечает на вопрос не «сколько стоит портфель», а «как он
          отработал». Без этого слоя легко перепутать рост рынка с удачной стратегией или не заметить, что комиссии и
          простой «съели» результат.
        </p>
        <p>
          В CapitalView аналитика опирается на те же активы и операции, что и остальной
          <strong>учёт и анализ инвестиций</strong>: вы не ведёте отдельную «теневую» таблицу метрик, а смотрите
          следствие уже внесённой истории.
        </p>
        <SeoPageTip>
          Сначала добейтесь правдоподобной стоимости портфеля и полноты сделок — иначе графики будут красивыми, но
          бесполезными для решений.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection
        section-id="analytics-metrics"
        title="Доходность, рентабельность и окупаемость"
      >
        <p>
          <strong>Доходность инвестиций</strong> — базовая метрика: как изменился результат относительно вложений за
          выбранный период. Её удобно смотреть в динамике и в разрезе портфеля или отдельных позиций.
        </p>
        <p>
          <strong>Рентабельность инвестиций</strong> и <strong>учёт рентабельности инвестиций</strong> помогают оценить
          эффективность: сопоставить отдачу с тем, сколько капитала было задействовано, а не только увидеть абсолютную
          прибыль в рублях.
        </p>
        <p>
          <strong>Окупаемость инвестиций</strong> и <strong>учёт окупаемости инвестиций</strong> — про горизонт:
          ориентировочно, за какой срок вложения «возвращают» себя при текущей динамике. Это не прогноз и не обещание,
          а способ сравнить сценарии и ожидания.
        </p>
        <ul>
          <li>смотрите доходность на сопоставимых периодах (месяц, квартал, год);</li>
          <li>отделяйте переоценку бумаг от фактических денежных поступлений;</li>
          <li>учитывайте комиссии и налоги там, где они уже отражены в операциях.</li>
        </ul>
      </SeoPageSection>

      <SeoPageVisual
        placeholder="Скриншот: аналитика — динамика доходности, вклад активов, сводные метрики"
        caption="Типовой вид раздела аналитики после накопления истории операций."
      />

      <SeoPageSection section-id="analytics-how" title="Как смотреть аналитику в сервисе">
        <p>Практичный порядок работы с разделом:</p>
        <SeoPageStepFlow layout="grid" aria-label="Как пользоваться аналитикой">
          <SeoPageStepFlowItem :step="1" title="Сверьте базу.">
            <p>
              Убедитесь, что портфель и сделки актуальны — без этого
              <strong>учёт доходов от инвестиций</strong> будет врать.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Выберите период.">
            <p>
              Сравните короткие и длинные окна: так видно, устойчива ли
              <strong>доходность инвестиций</strong> или это разовый скачок.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Разберите вклад.">
            <p>
              Найдите активы и классы, которые сильнее всего влияют на результат — плюс и минус.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Зафиксируйте вывод.">
            <p>
              Решите, что менять: структуру, частоту сделок или ожидания по
              <strong>окупаемости инвестиций</strong>.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
        <SeoPageTip>
          Аналитика полезна как регулярный ритуал раз в месяц или квартал — чаще имеет смысл смотреть дашборд и ленту
          операций, а не «перерисовывать» выводы каждый день.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection
        section-id="analytics-quality"
        title="Качество данных и типичные ошибки"
      >
        <p>
          Точность <strong>учёта рентабельности инвестиций</strong> почти всегда упирается в полноту истории. Частые
          причины расхождений:
        </p>
        <ul>
          <li>пропущенные комиссии и налоги;</li>
          <li>сделки без даты или с неверной валютой;</li>
          <li>дивиденды и купоны, которые есть у брокера, но не попали в сервис;</li>
          <li>корпоративные действия без корректировки количества бумаг.</li>
        </ul>
        <p>
          Если цифры «не бьются» с выпиской, сначала проверьте операции — подробнее об этом на странице сделок.
        </p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-transactions' }"
          title="Сделки и история операций — CapitalView"
        />
      </SeoPageSection>

      <SeoPageSection section-id="analytics-related" title="Связанные разделы учёта">
        <p>
          Аналитика сильнее всего работает в связке с остальным сервисом: обзор портфеля даёт контекст, дивиденды —
          денежный поток, сделки — первоисточник фактов.
        </p>
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

      <SeoPageSection section-id="analytics-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="featureAnalyticsFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Смотрите доходность в одном месте"
        text="Зарегистрируйтесь, перенесите сделки и откройте аналитику — учёт доходности инвестиций станет частью ежедневной картины портфеля, а не разовым расчётом в таблице."
        primary-text="Зарегистрироваться"
        secondary-text="Обзор учёта портфеля"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
