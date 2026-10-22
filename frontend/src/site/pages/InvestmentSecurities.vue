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
import { investmentSecuritiesFaq } from '../content/investmentSecuritiesFaq'

const securitiesTocItems = [
  { href: '#securities-what', label: 'Что такое учёт ценных бумаг' },
  { href: '#securities-why', label: 'Зачем вести учёт инвестиций в ЦБ' },
  { href: '#securities-classes', label: 'Акции и облигации в одном портфеле' },
  { href: '#securities-start', label: 'С чего начать смешанный портфель' },
  { href: '#securities-routine', label: 'Регулярный контроль позиций' },
  { href: '#securities-faq', label: 'Короткие ответы' },
]
</script>

<template>
  <SiteSeoPage>
    <article class="seo-page seo-help-page">
      <SeoPageHero
        eyebrow="Инвестиции · ценные бумаги"
        title="Учёт инвестиций в ценные бумаги"
        lead="Акции, облигации, несколько брокеров и валют — без единого контура легко потерять структуру портфеля и реальный результат. Эта страница — хаб по учёту инвестиций в ценные бумаги в CapitalView: как собрать позиции в одном месте, чем отличаются классы бумаг и куда углубиться дальше.\n\nЕсли вы ищете систему для финансовых инвестиций в ценные бумаги, а не разовую таблицу «на глаз», ниже — логика учёта, карточки разделов по акциям и облигациям и короткие ответы на типовые вопросы."
      />

      <SeoPageToc aria-label="Разделы страницы" :items="securitiesTocItems" />

      <SeoPageSection
        section-id="securities-what"
        title="Что такое учёт инвестиций в ценные бумаги"
      >
        <p>
          <strong>Учёт инвестиций в ценные бумаги</strong> — это не только список тикеров. Это связка позиций,
          сделок, комиссий и выплат, из которой видно: сколько вложено, какова текущая оценка и откуда берётся
          результат. В CapitalView такой учёт строится вокруг портфеля: бумаги и денежные операции живут в одной модели.
        </p>
        <p>
          Под <strong>инвестициями в ценные бумаги</strong> обычно имеют в виду акции, облигации и близкие биржевые
          инструменты. На практике «<strong>инвестиции бумаги</strong>» и разговорное «<strong>ценные инвестиции</strong>»
          часто означают одно и то же — портфель ЦБ, который хочется видеть целиком, а не по выпискам брокеров.
        </p>
        <SeoPageTip>
          Если часть портфеля ещё в Excel, сначала перенесите крупные позиции и ключевые сделки — так быстрее сверите
          логику сервиса с привычным <strong>учётом финансовых инвестиций и ценных бумаг</strong> в таблице.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection
        section-id="securities-why"
        title="Зачем вести учёт инвестиций в ЦБ отдельно от брокера"
      >
        <p>
          Брокерский кабинет показывает счёт у конкретного брокера. <strong>Финансовые инвестиции в ценные бумаги</strong>
          часто размазаны по нескольким счетам, ИИС и «ручным» позициям. Сводный учёт помогает:
        </p>
        <ul>
          <li>видеть доли акций и облигаций в одной валюте отображения;</li>
          <li>не терять комиссии и корпоративные действия при переносе между счетами;</li>
          <li>сверять доходность и структуру без ручной склейки выписок;</li>
          <li>держать историю сделок, если меняете брокера или стратегию.</li>
        </ul>
        <p>
          Подробный обзор модели портфеля, дашборда и рутины — на странице
          <router-link :to="{ name: 'site-feature-portfolio' }" class="seo-inline-link">учёта портфеля в CapitalView</router-link>.
        </p>
      </SeoPageSection>

      <SeoPageSection
        section-id="securities-classes"
        title="Акции и облигации: куда углубиться"
      >
        <p>
          Смешанный портфель удобно вести вместе, но нюансы классов бумаг разные. Выберите раздел по интересам —
          там раскрыты сценарии учёта, типичные ошибки и FAQ.
        </p>
        <div class="seo-article-cards">
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-stocks' }"
            title="Учёт инвестиций в акции — CapitalView"
          />
          <SeoArticleLinkCard
            :to="{ name: 'site-investment-bonds' }"
            title="Учёт инвестиций в облигации — CapitalView"
          />
        </div>
        <p>
          Акции сильнее зависят от цены и дивидендов; облигации — от купонов, погашения и графика выплат. В одном
          портфеле оба класса можно держать рядом, а детальный разбор — открывать по ссылкам выше.
        </p>
      </SeoPageSection>

      <SeoPageSection section-id="securities-start" title="С чего начать смешанный портфель">
        <p>Типовой порядок для <strong>учёта инвестиций в ценные бумаги</strong> с нуля:</p>
        <SeoPageStepFlow layout="grid" aria-label="Порядок настройки учёта ценных бумаг">
          <SeoPageStepFlowItem :step="1" title="Вход и портфель.">
            <p>
              Зарегистрируйтесь и создайте портфель —
              <router-link :to="{ path: '/login' }" class="seo-inline-link">вход и регистрация</router-link>.
              Задайте валюту отображения, чтобы сверять оценку с отчётами.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="2" title="Позиции ЦБ.">
            <p>
              Добавьте акции и облигации, которые уже есть на счетах. Не обязательно вносить всё за один вечер —
              начните с крупных долей.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="3" title="Сделки и комиссии.">
            <p>
              Отразите покупки, продажи и комиссии. Качество учёта почти всегда упирается в полноту истории операций.
            </p>
          </SeoPageStepFlowItem>
          <SeoPageStepFlowItem :step="4" title="Выплаты.">
            <p>
              Проверьте дивиденды и купоны: без них картина по <strong>инвестициям в ценные бумаги</strong> будет
              неполной, даже если цены позиций верные.
            </p>
          </SeoPageStepFlowItem>
        </SeoPageStepFlow>
        <SeoPageTip>
          После первого переноса сверьте итоговую оценку и крупные позиции с брокером. Расхождения чаще всего — в
          пропущенной сделке, комиссии или недавней выплате.
        </SeoPageTip>
      </SeoPageSection>

      <SeoPageSection section-id="securities-routine" title="Регулярный контроль позиций">
        <p>
          Чтобы <strong>учёт инвестиций в ценные бумаги</strong> не расходился с реальностью, закрепите простую рутину:
        </p>
        <ul>
          <li><strong>После сделок:</strong> вносите операции сразу или пакетом раз в несколько дней.</li>
          <li><strong>Еженедельно:</strong> сверяйте ключевые позиции и доли классов бумаг.</li>
          <li><strong>После отчётов и выплат:</strong> проверяйте дивиденды, купоны и корпоративные действия.</li>
          <li><strong>Раз в квартал:</strong> смотрите структуру портфеля и пересматривайте цели.</li>
        </ul>
        <p>
          Обзор сервиса и дашборда поможет понять, где смотреть сводку каждый день:
        </p>
        <SeoArticleLinkCard
          :to="{ name: 'site-feature-portfolio' }"
          title="Учёт инвестиций в CapitalView: обзор сервиса"
        />
      </SeoPageSection>

      <SeoPageSection section-id="securities-faq" title="Короткие ответы">
        <div class="seo-faq-accordion">
          <FaqAccordion :items="investmentSecuritiesFaq" />
        </div>
      </SeoPageSection>

      <SeoPageCtaCard
        title="Вести учёт ценных бумаг в CapitalView"
        text="Создайте портфель, перенесите позиции по акциям и облигациям и держите структуру и выплаты в одном месте."
        primary-text="Зарегистрироваться"
        primary-to="/login"
        secondary-text="Обзор учёта портфеля"
        secondary-to="/features/portfolio"
      />
    </article>
  </SiteSeoPage>
</template>
