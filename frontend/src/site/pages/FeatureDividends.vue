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
import { featureDividendsFaq } from '../content/featureDividendsFaq'

const dividendsTocItems = [
  { href: '#div-income', label: 'Доход от инвестиций: дивиденды и купоны' },
  { href: '#div-calendar', label: 'Календарь и ожидания выплат' },
  { href: '#div-bonds', label: 'Облигации и купонный поток' },
  { href: '#div-routine', label: 'Как вести учёт выплат регулярно' },
  { href: '#div-related', label: 'Связь с портфелем и аналитикой' },
  { href: '#div-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Справка · дивиденды и купоны"
        title="Дивиденды и купоны: доход от инвестиций"
        lead="Переоценка бумаг на экране брокера — ещё не полный результат. Для многих стратегий важен фактический доход от инвестиций: дивиденды по акциям и купоны по облигациям. CapitalView помогает видеть выплаты рядом с портфелем, а не искать их только в выписках.\n\nНа странице — как устроен учёт дивидендов и купонов, зачем отделять получение дохода с инвестиций от роста котировок, и как аккуратно вести учёт инвестиций в облигации, если купонный поток — часть вашей модели. Оглавление ниже ведёт от общей логики к рутине и коротким ответам."
      />

      <SeoPageToc aria-label="Разделы о дивидендах" :items="dividendsTocItems" />

      <SeoPageSection
        section-id="div-income"
        title="Доход от инвестиций: дивиденды и купоны"
      >
        <p>
          <strong>Дивиденды и купоны</strong> — разные механизмы, но одна роль в учёте: зафиксировать денежный поток.
          Дивиденды приходят по акциям (не гарантированы и зависят от решений эмитента), купоны — по облигациям по
          заранее известному графику.
        </p>
        <p>
          Без отдельного контура <strong>доход от инвестиций</strong> легко «растворяется» в общем изменении стоимости
          портфеля. Тогда сложно ответить, сколько вы реально получили живыми деньгами и насколько стратегия опирается
          на выплаты, а не только на рост цены.
        </p>
        <SeoPageTip>
          Если цель — <strong>получение дохода с инвестиций</strong>, смотрите не только прогнозную доходность бумаги,
          но и историю фактических зачислений и пропусков выплат.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="div-calendar" title="Календарь и ожидания выплат">
        <p>
          Удобный календарь выплат помогает планировать ликвидность: когда ждать денег, какие позиции дают поток,
          совпадают ли ожидания с фактом у брокера. Это особенно полезно, когда
          <strong>доходы, сбережения и инвестиции</strong> живут в одном семейном бюджете и даты важны.
        </p>
        <p>На практике полезно разделять:</p>
        <ul>
          <li>ожидаемые выплаты (по календарю / справочнику);</li>
          <li>фактически зачисленные суммы в истории операций;</li>
          <li>расхождения — повод проверить отсечку, налог или задержку брокера.</li>
        </ul>
        <SeoPageStepFlow layout="grid" aria-label="Работа с выплатами">
          <SeoPageStepFlowItem :step="1" title="Позиции.">
            <p>Убедитесь, что дивидендные акции и облигации отражены в портфеле с верным количеством.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Ожидания.">
            <p>Сверьте ближайшие даты выплат в календаре сервиса и у брокера.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Факт.">
            <p>После зачисления проверьте операцию в истории — так закрывается цикл учёта.</p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Итог.">
            <p>Раз в квартал смотрите суммарный поток: сколько дали дивиденды и купоны.</p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
      </SeoPageSection>

      <SeoPageVisual
        placeholder="Скриншот: календарь дивидендов и купонов, список ближайших выплат"
        caption="Календарь помогает связать ожидания по доходу с реальными датами."
      />

      <SeoPageSection section-id="div-bonds" title="Облигации и купонный поток">
        <p>
          <strong>Инвестиции в облигации</strong> часто выбирают именно ради предсказуемого купона. Тогда
          <strong>учёт инвестиций в облигации</strong> должен включать не только цену и НКД в моменте, но и график
          выплат, погашения и комиссии при покупке/продаже.
        </p>
        <p>
          В CapitalView облигации живут в общей модели портфеля: позиции, сделки и купоны не разъезжаются по разным
          файлам. Это упрощает сверку с брокерским счётом и снижает риск «забытых» купонов в годовой картине дохода.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-bonds' }"
            title="Учёт инвестиций в облигации — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-transactions' }"
            title="Сделки и история операций — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="div-routine" title="Как вести учёт выплат регулярно">
        <p>
          Чтобы <strong>получение дохода с инвестиций</strong> не превращалось в хаос раз в год, закрепите короткую
          рутину:
        </p>
        <ul>
          <li><strong>После отсечки / даты купона:</strong> проверьте факт зачисления у брокера.</li>
          <li><strong>После зачисления:</strong> убедитесь, что операция есть в CapitalView.</li>
          <li><strong>Ежемесячно:</strong> сверьте суммарный денежный поток с ожиданиями.</li>
          <li><strong>При ребалансировке:</strong> учитывайте, как смена бумаг меняет будущие выплаты.</li>
        </ul>
        <SeoPageTip>
          Не смешивайте в одной записи дивиденд и продажу бумаги — потом сложнее искать ошибки и считать чистый
          <strong>доход от инвестиций</strong>.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="div-related" title="Связь с портфелем и аналитикой">
        <p>
          Выплаты — часть общей системы учёта. Обзор портфеля даёт структуру позиций, аналитика показывает, как поток
          влияет на результат, сделки фиксируют каждую операцию.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-portfolio' }"
            title="Учёт инвестиций в CapitalView: обзор сервиса"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-feature-analytics' }"
            title="Аналитика и доходность портфеля — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="div-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="featureDividendsFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Держите дивиденды и купоны под контролем"
        text="Зарегистрируйтесь, добавьте позиции и начните учитывать выплаты — доход от инвестиций станет видимым слоем портфеля, а не сюрпризом в выписке."
        primary-text="Зарегистрироваться"
        secondary-text="Обзор учёта портфеля"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
