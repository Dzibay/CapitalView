<script setup>
import { ref } from 'vue'
import { ArrowUpRight, CreditCard, Plus, Settings, Upload } from 'lucide-vue-next'
import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvWidget from '../cabinet/ui/CvWidget.vue'
import SupportChatPanel from '../components/support/SupportChatPanel.vue'
import { supportFaq } from '../content/supportFaq'
import { plural } from '../cabinet/format'

const openIndex = ref(0)
const toggle = (i) => { openIndex.value = openIndex.value === i ? null : i }

const LINKS = [
  { to: '/billing', icon: CreditCard, title: 'Подписка и оплата', text: 'Тарифы, продление, история платежей' },
  { to: '/assets', icon: Upload, title: 'Импорт портфеля', text: 'Подключение брокера и загрузка сделок' },
  { to: '/settings', icon: Settings, title: 'Настройки аккаунта', text: 'Имя, пароль и вход через Google' },
]
</script>

<template>
  <div class="sp">
    <CvPageHead
      eyebrow="Аккаунт"
      title="Поддержка"
      :meta="['Чат с командой сервиса', `${supportFaq.length} ${plural(supportFaq.length, 'ответ', 'ответа', 'ответов')} на частые вопросы`]"
    />

    <div class="cv-grid is-intro">
      <CvWidget id="chat" class="is-l" style="--i: 0" title="Чат с поддержкой" subtitle="Ответит администратор сервиса, история сохраняется здесь">
        <SupportChatPanel embedded />
      </CvWidget>

      <CvWidget class="is-s is-full-md" style="--i: 1" title="Полезное">
        <nav class="sp__links" aria-label="Разделы кабинета">
          <router-link v-for="l in LINKS" :key="l.to" :to="l.to" class="sp__link">
            <span class="sp__link-ic"><component :is="l.icon" :size="16" /></span>
            <span class="sp__link-text">
              <b>{{ l.title }}</b>
              <span>{{ l.text }}</span>
            </span>
            <ArrowUpRight :size="15" class="sp__link-go" />
          </router-link>
        </nav>
      </CvWidget>

      <CvWidget class="is-xl" style="--i: 2" title="Частые вопросы">
        <div class="faq" role="list">
          <div
            v-for="(item, i) in supportFaq"
            :key="i"
            class="faq__row"
            :class="{ 'is-open': openIndex === i }"
            role="listitem"
          >
            <button
              :id="`faq-q-${i}`"
              type="button"
              class="faq__q"
              :aria-expanded="openIndex === i"
              :aria-controls="`faq-a-${i}`"
              @click="toggle(i)"
            >
              <span class="faq__num cv-num">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="faq__text">{{ item.question }}</span>
              <span class="faq__ic" aria-hidden="true"><Plus :size="16" /></span>
            </button>
            <div :id="`faq-a-${i}`" class="faq__a" role="region" :aria-labelledby="`faq-q-${i}`">
              <div class="faq__a-inner">
                <p>{{ item.answer }}</p>
              </div>
            </div>
          </div>
        </div>
      </CvWidget>
    </div>
  </div>
</template>

<style scoped>
.sp__links { display: flex; flex-direction: column; gap: 4px; margin: 0 -10px; }
.sp__link {
  display: flex; align-items: center; gap: 12px; padding: 10px; border-radius: var(--cv-r-sm);
  color: inherit; text-decoration: none; transition: background .2s var(--cv-ease);
}
.sp__link:hover { background: var(--cv-hover); }
.sp__link:focus-visible { outline: 2px solid var(--cv-accent); outline-offset: -2px; }
.sp__link-ic {
  display: grid; place-items: center; flex: none; width: 34px; height: 34px; border-radius: 10px;
  color: var(--cv-accent-ink); background: var(--cv-accent-soft);
}
.sp__link-text { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; }
.sp__link-text b { font-size: 13px; font-weight: 600; color: var(--cv-ink); }
.sp__link-text span { font-size: 12px; line-height: 1.4; color: var(--cv-mut); }
.sp__link-go { flex: none; color: var(--cv-dim); transition: color .2s, transform .2s var(--cv-ease); }
.sp__link:hover .sp__link-go { color: var(--cv-ink); transform: translate(2px, -2px); }

.faq { display: flex; flex-direction: column; }
.faq__row { border-top: 1px solid var(--cv-line); }
.faq__row:first-child { border-top: 0; }
.faq__q {
  display: flex; align-items: center; gap: 16px; width: 100%; padding: 16px 0; border: 0;
  font: inherit; text-align: left; color: var(--cv-ink-2); background: none; cursor: pointer;
  transition: color .2s;
}
.faq__q:hover, .faq__row.is-open .faq__q { color: var(--cv-ink); }
.faq__q:focus-visible { outline: 2px solid var(--cv-accent); outline-offset: 2px; border-radius: 6px; }
.faq__num { flex: none; width: 22px; font-size: 12px; color: var(--cv-dim); }
.faq__text { flex: 1; font-size: 14px; font-weight: 550; line-height: 1.45; }
.faq__ic {
  display: grid; place-items: center; flex: none; width: 28px; height: 28px; border-radius: 50%;
  color: var(--cv-mut); box-shadow: inset 0 0 0 1px var(--cv-line-2);
  transition: transform .3s var(--cv-ease), color .2s, background .2s;
}
.faq__row.is-open .faq__ic { transform: rotate(45deg); color: var(--cv-accent-ink); background: var(--cv-accent-soft); box-shadow: none; }
.faq__a { display: grid; grid-template-rows: 0fr; transition: grid-template-rows .35s var(--cv-ease); }
.faq__row.is-open .faq__a { grid-template-rows: 1fr; }
.faq__a-inner { overflow: hidden; }
.faq__a p { margin: 0; padding: 0 44px 18px 38px; font-size: 13.5px; line-height: 1.65; color: var(--cv-mut); }
@media (min-width: 769px) and (max-width: 1200px) {
  .sp__links { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
}
@media (max-width: 600px) {
  .faq__q { gap: 12px; }
  .faq__num { display: none; }
  .faq__a p { padding: 0 0 16px; }
}
</style>
