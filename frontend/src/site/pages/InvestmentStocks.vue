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
import { investmentStocksFaq } from '../content/investmentStocksFaq'

const stocksTocItems = [
  { href: '#stocks-essence', label: 'Суть инвестиций в акции' },
  { href: '#stocks-accounting', label: 'Что фиксировать в учёте' },
  { href: '#stocks-start', label: 'С чего начать учёт акций' },
  { href: '#stocks-mix', label: 'Акции и облигации вместе' },
  { href: '#stocks-dividends', label: 'Дивиденды и контроль позиций' },
  { href: '#stocks-choose', label: 'Какие инвестиции выбрать' },
  { href: '#stocks-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Инвестиции · акции"
        title="Учёт инвестиций в акции"
        lead="Покупки на бирже, усреднение, дивиденды и несколько счетов — без нормального учёта сложно понять, сколько реально заработано на акциях. CapitalView помогает вести учёт инвестиций в акции: позиции, сделки, комиссии и выплаты в одной модели портфеля.\n\nНиже — суть подхода, что обязательно фиксировать, как совмещать акции и облигации и куда смотреть дальше, если выстраиваете системный учёт, а не разовые заметки в таблице."
      />

      <SeoPageToc aria-label="Разделы страницы" :items="stocksTocItems" />

      <SeoPageSection section-id="stocks-essence" title="Суть инвестиций в акции и роль учёта">
        <p>
          <strong>Суть инвестиций в акции</strong> — доля в бизнесе эмитента: вы рассчитываете на рост цены и/или на
          дивиденды. На практике результат зависит не только от удачных тикеров, но и от того, насколько полно вы
          ведёте историю входов, выходов и издержек.
        </p>
        <p>
          <strong>Инвестиции в акции</strong> без учёта быстро превращаются в набор выписок: средняя цена «на глаз»,
          забытые комиссии, дивиденды «где-то на карте». <strong>Учёт инвестиций в акции</strong> в сервисе возвращает
          связность: позиция ↔ сделки ↔ денежные потоки ↔ оценка портфеля.
        </p>
        <SeoPageTip>
          Если вы только формируете подход, начните с одного портфеля и полного отражения сделок по 5–10 ключевым
          позициям — так быстрее поймёте, хватает ли вам детализации сервиса.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-accounting" title="Что фиксировать в учёте инвестиций в акции">
        <p>Минимальный набор для честного результата:</p>
        <ul>
          <li>дата, цена и количество при покупке и продаже;</li>
          <li>комиссия брокера и прочие издержки сделки;</li>
          <li>валюта операции и, при необходимости, курс для отчётов;</li>
          <li>дивидендные выплаты и корпоративные действия (сплиты, допэмиссии);</li>
          <li>переводы бумаг между счетами, если меняете брокера.</li>
        </ul>
        <p>
          Без этих полей <strong>учёт инвестиций в акции</strong> будет красиво выглядеть на дашборде, но расходиться
          с брокерской реальностью. Особенно часто «ломают» среднюю цену входа пропущенные докупки и комиссии.
        </p>
        <p>
          Общая модель портфеля и операций описана в
          <router-link :to="{ name: 'site-feature-portfolio' }" class="seo-inline-link">обзоре учёта инвестиций</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-start" title="С чего начать учёт инвестиций в акции">
        <SeoPageStepFlow layout="grid" aria-label="Порядок учёта акций">
          <SeoPageStepFlowItem :step="1" title="Портфель и валюта.">
            <p>
              Создайте портфель после
              <router-link :to="{ path: '/login' }" class="seo-inline-link">регистрации</router-link>
              и выберите валюту отображения — так проще сверять оценку с отчётами.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Позиции по акциям.">
            <p>
              Добавьте бумаги, которые уже есть на счетах. Начните с крупнейших долей — они сильнее влияют на сводку.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="История сделок.">
            <p>
              Внесите покупки и продажи (вручную или доступным импортом). Чем полнее история, тем точнее средняя
              и доходность по бумаге.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Сверка.">
            <p>
              Сравните количество и оценку с брокером. Расхождение почти всегда указывает на пропущенную операцию.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-mix" title="Акции и облигации в одном портфеле">
        <p>
          Запрос «<strong>акции облигации</strong>» и кластер <strong>инвестиции акции облигации</strong> часто
          означает смешанный портфель: рост через акции и более предсказуемый денежный поток через облигации. В
          CapitalView оба класса можно вести в одном учёте — доли и результат видны вместе.
        </p>
        <p>
          Нюансы по купонам и погашениям раскрыты отдельно; для <strong>инвестиций в ценные бумаги</strong> в целом
          удобна хаб-страница по ЦБ.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-bonds' }"
            title="Учёт инвестиций в облигации — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-securities' }"
            title="Учёт инвестиций в ценные бумаги — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-dividends" title="Дивиденды и контроль позиций">
        <p>
          Дивидендная часть <strong>инвестиций в акции</strong> легко «выпадает» из учёта, если смотреть только на
          цену. Фиксируйте фактические выплаты и сверяйте их с календарём ожиданий — иначе денежный доход не попадёт
          в результат портфеля.
        </p>
        <p>Сценарии выплат и купонов:</p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-dividends' }"
          title="Дивиденды и купоны — CapitalView"
        />
        <SeoPageTip>
          После закрытия реестра или поступления денег на счёт проверьте, что выплата отражена в истории — это частая
          точка расхождений при долгосрочном удержании акций.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-choose" title="Какие инвестиции выбрать и как помогает учёт">
        <p>
          Вопрос «<strong>какие инвестиции выбрать</strong>» не решается одной страницей: горизонт, риск и цели у всех
          разные. Учёт не подскажет «лучшую бумагу», но покажет факты: доли, перекосы, вклад дивидендов и реальный
          результат после комиссий.
        </p>
        <ul>
          <li>смотрите, не съели ли 2–3 позиции весь риск портфеля;</li>
          <li>сверяйте, окупают ли дивиденды просадки по отдельным бумагам;</li>
          <li>сравнивайте результат акций с облигационной частью, если портфель смешанный.</li>
        </ul>
        <p>
          Для системной картины используйте
          <router-link :to="{ name: 'site-feature-portfolio' }" class="seo-inline-link">обзор сервиса учёта портфеля</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="stocks-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="investmentStocksFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Вести учёт акций в CapitalView"
        text="Зарегистрируйтесь, добавьте позиции и сделки — дальше дашборд и история операций помогут держать учёт инвестиций в акции актуальным."
        primary-text="Зарегистрироваться"
        primary-to="/login"
        secondary-text="Обзор учёта портфеля"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
