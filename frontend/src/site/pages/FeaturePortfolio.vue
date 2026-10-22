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
import { portfolioOverviewFaq } from '../content/portfolioOverviewFaq'

const portfolioTocItems = [
  { href: '#overview-model', label: 'Объекты учёта: портфель, активы, операции' },
  { href: '#overview-start', label: 'С чего начать учёт личных инвестиций' },
  { href: '#overview-dashboard', label: 'Дашборд и учёт портфеля инвестиций' },
  { href: '#overview-assets', label: 'Активы и сделки' },
  { href: '#overview-analytics', label: 'Аналитика и доходность' },
  { href: '#overview-dividends', label: 'Дивиденды и выплаты' },
  { href: '#overview-routine', label: 'Как вести учёт инвестиций регулярно' },
  { href: '#overview-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Справка · учёт портфеля"
        title="Учёт инвестиций в CapitalView: обзор сервиса"
        lead="Несколько счетов, разные валюты, купоны и дивиденды — без нормального учёта инвестиций легко не заметить, куда ушла доходность и что сейчас реально в портфеле. CapitalView собирает картину в одном месте: это сервис учёта инвестиций, где виден баланс, сделки и динамика без бесконечных таблиц.\n\nДальше — простой обзор «как пользоваться» для учёта портфеля инвестиций и учёта личных инвестиций онлайн: с чего начать, что смотреть на дашборде, где жить сделкам и аналитике, и как не забросить ведение учёта инвестиций, чтобы система учёта инвестиций не расходилась с брокерскими выписками. Если вы как раз искали, как вести учёт инвестиций системно, пройдитесь по оглавлению ниже — от базовой логики до рутины и коротких ответов на типовые вопросы."
      />

      <SeoPageToc aria-label="Разделы обзора" :items="portfolioTocItems" />

      <SeoPageSection
        section-id="overview-model"
        title="Объекты учёта: портфель, активы, операции"
      >
        <p>
          <strong>Учёт инвестиций</strong> в CapitalView строится вокруг портфеля: это ваша «корневая» сущность для
          <strong>учёта портфеля инвестиций</strong> — баланс, структура, история операций и показатели доходности.
          Внутри портфеля находятся активы (акции, облигации, другие инструменты) и денежные потоки: покупки, продажи,
          комиссии, пополнения, выплаты.
        </p>
        <p>
          Такой подход близок к идее <strong>системы учёта инвестиций</strong>: данные не размазаны по таблицам и
          выпискам, а собираются в одном интерфейсе — удобно для <strong>учёта личных инвестиций</strong> и для
          контроля нескольких брокерских счетов в одной логике.
        </p>
        <SeoPageTip>
          Если вы переходите с таблицы Excel, имеет смысл сначала завести портфель и перенести ключевые сделки —
          так быстрее «поймаете» ту же логику, что и в ручном <strong>ведении учёта инвестиций</strong>, но без
          постоянной подстройки формул.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="overview-start" title="С чего начать учёт личных инвестиций">
        <p>Типовой порядок для нового пользователя:</p>
        <SeoPageStepFlow layout="grid" aria-label="Порядок действий для нового пользователя">
          <SeoPageStepFlowItem :step="1" title="Регистрация и вход.">
            <p>
              Создайте аккаунт и откройте личный кабинет —
              <router-link :to="{ path: '/login' }" class="seo-inline-link">вход и регистрация</router-link>.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Портфель.">
            <p>
              Задайте валюту отображения и базовые настройки, чтобы дальнейший
              <strong>учёт инвестиций онлайн</strong> был сопоставим с вашими брокерскими отчётами.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Активы и операции.">
            <p>
              Добавьте позиции и историю сделок (вручную или через доступные в сервисе сценарии импорта —
              ориентируйтесь на подсказки в интерфейсе).
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Проверка дашборда.">
            <p>
              Убедитесь, что стоимость портфеля, вложения и доходность выглядят правдоподобно; при расхождениях обычно
              не хватает операции или комиссии.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
        <p>
          Параллельно полезно заглянуть в материалы по Excel и шаблонам — особенно если часть портфеля вы ещё ведёте
          вне сервиса.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-guide-excel' }"
            title="Учёт инвестиций в Excel — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-templates' }"
            title="Шаблоны для учёта инвестиций — CapitalView"
          />
        </div>
      </SeoPageSection>

      <SeoPageSection section-id="overview-dashboard" title="Дашборд и учёт портфеля инвестиций">
        <p>
          После входа основной экран — дашборд. Это «витрина» <strong>сервиса учёта инвестиций</strong>: здесь обычно
          собраны агрегированные цифры (стоимость, динамика, крупные движения) и быстрый доступ к разделам приложения.
        </p>
        <p>На дашборде имеет смысл отслеживать:</p>
        <ul>
          <li>текущую оценку портфеля в выбранной валюте;</li>
          <li>вклад отдельных активов или классов в результат;</li>
          <li>наличие нетипичных просадок или скачков — повод проверить сделки и курсы.</li>
        </ul>
        <SeoPageTip>
          Дашборд хорош как ежедневная точка контроля, но не заменяет детальный разбор: для глубины переходите в
          аналитику и карточки активов.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageVisual
        placeholder="Скриншот: дашборд — сводка портфеля, виджеты, переходы в активы и аналитику"
        caption="Типовой вид главного экрана после настройки учёта."
      />

      <SeoPageSection section-id="overview-assets" title="Активы и сделки">
        <p>
          Раздел активов — центр <strong>учёта портфеля инвестиций</strong> на уровне инструментов: какие бумаги в
          портфеле, по каким ценам вошли, какова текущая доля. Раздел сделок фиксирует историю операций; качество
          <strong>ведения учёта инвестиций</strong> почти всегда упирается в полноту этих записей.
        </p>
        <p>Практические правила:</p>
        <ul>
          <li>отражайте комиссии брокера и налоги там, где это предусмотрено интерфейсом;</li>
          <li>не смешивайте в одной записи несколько событий — проще искать ошибки;</li>
          <li>при корпоративных действиях (сплиты, выплаты) проверяйте, что они попали в историю.</li>
        </ul>
        <p>Подробнее про логику операций на лендинге:</p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-transactions' }"
          title="Сделки и история операций — CapitalView"
        />
      </SeoPageSection>

      <SeoPageSection section-id="overview-analytics" title="Аналитика и доходность">
        <p>
          Аналитика отвечает на вопрос «как ведёт себя портфель во времени и по сравнению с ожиданиями». Для
          <strong>учёта инвестиций онлайн</strong> это важный слой: без графиков и метрик система превращается в простой
          реестр сделок.
        </p>
        <p>На отдельной странице мы раскрываем маркетинговый контекст метрик и доходности:</p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-analytics' }"
          title="Аналитика и доходность портфеля — CapitalView"
        />
        <p>
          В приложении используйте раздел аналитики, чтобы смотреть динамику, структуру и вспомогательные отчёты —
          конкретный набор экранов может развиваться релизами, но назначение раздела остаётся тем же.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="overview-dividends" title="Дивиденды и выплаты">
        <p>
          Для дивидендной стратегии и контроля купонов важен отдельный контур: календарь, прогнозы и фактические
          поступления. CapitalView ориентирован на то, чтобы <strong>учёт личных инвестиций</strong> включал и этот
          пласт, а не только оценку бумаг.
        </p>
        <p>Обзор сценариев — на странице:</p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-dividends' }"
          title="Дивиденды и купоны — CapitalView"
        />
      </SeoPageSection>

      <SeoPageVisual
        placeholder="Скриншот: список активов или лента сделок с фильтрами"
        caption="Детальный учёт удобнее проверять там, где видны и позиции, и операции."
      />

      <SeoPageSection section-id="overview-routine" title="Как вести учёт инвестиций регулярно">
        <p>
          <strong>Как вести учёт инвестиций</strong>, если портфель живёт месяцами и годами? Полезно закрепить простую
          рутину — тогда <strong>система учёта инвестиций</strong> не ломается после каждого отпуска.
        </p>
        <ul>
          <li><strong>Еженедельно:</strong> сверка ключевых позиций с брокером, дозагрузка сделок.</li>
          <li><strong>После сделок:</strong> вносите операции сразу или пакетом раз в несколько дней — главное, не копить «хвосты» на месяцы.</li>
          <li><strong>После отчётов эмитентов:</strong> проверяйте дивиденды и корпоративные действия.</li>
          <li><strong>Раз в квартал:</strong> смотрите структуру портфеля и доходность в аналитике, сверяйте цели.</li>
        </ul>
        <SeoPageTip>
          Учёт инвестиций в сервисе даёт выигрыш, когда данные актуальны: редкие «большие» обновления почти всегда
          приводят к трудноразбираемым расхождениям.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="overview-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="portfolioOverviewFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Перейти к учёту в CapitalView"
        text="Зарегистрируйтесь, создайте портфель и перенесите сделки — дальше дашборд, активы и аналитика помогут держать учёт инвестиций в одном месте."
        primary-text="Зарегистрироваться"
        secondary-text="Шаблоны для учёта"
        secondary-to="/templates"
      />
    </article>
  </SiteSeoPage>
</template>
