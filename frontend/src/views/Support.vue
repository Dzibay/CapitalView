<script setup>
import PageLayout from '../layouts/PageLayout.vue'
import PageHeader from '../layouts/PageHeader.vue'
import Widget from '../components/widgets/base/Widget.vue'
import WidgetContainer from '../components/widgets/base/WidgetContainer.vue'
import FaqAccordion from '../components/faq/FaqAccordion.vue'
import SupportChatPanel from '../components/support/SupportChatPanel.vue'
import { supportFaq } from '../content/supportFaq'
import { CircleHelp, MessageCircle } from 'lucide-vue-next'

import '../site/styles/landing-page.css'
</script>

<template>
  <PageLayout>
    <PageHeader
      title="Поддержка"
      subtitle="Ответы на частые вопросы и переписка с командой сервиса"
    />

    <div class="support-grid">
      <WidgetContainer id="chat" :gridColumn="12" minHeight="auto">
        <Widget title="Чат с поддержкой" :icon="MessageCircle">
          <SupportChatPanel embedded />
        </Widget>
      </WidgetContainer>
      
      <WidgetContainer :gridColumn="12" minHeight="auto">
        <Widget title="Частые вопросы" :icon="CircleHelp">
          <div class="cv-landing support-faq-wrap">
            <FaqAccordion :items="supportFaq" />
          </div>
        </Widget>
      </WidgetContainer>
    </div>
  </PageLayout>
</template>

<style scoped>
.support-grid {
  display: grid;
  gap: var(--spacing);
  grid-template-columns: repeat(12, 1fr);
  width: 100%;
  min-width: 0;
}

.support-faq-wrap {
  width: 100%;
  min-width: 0;
  margin: 0 -0.25rem;
}

@media (max-width: 768px) {
  .support-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .support-grid :deep(.widget-container) {
    grid-column: 1 / -1 !important;
  }
}
</style>
