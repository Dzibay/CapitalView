<script setup>
import { ArrowRight } from 'lucide-vue-next'

defineProps({
  integrationFeatures: {
    type: Array,
    required: true
  },
  comingSoonBrokers: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section id="integrations" class="section section-alt snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Подключается за 2 минуты</h2>
      <p class="section-subheading reveal">
        Один раз авторизуйтесь через брокера — и все сделки, дивиденды и купоны будут синхронизироваться
        автоматически. Мы используем только read-only доступ: выводить средства или совершать сделки через
        CapitalView невозможно.
      </p>

      <div class="integration-card reveal">
        <div class="integration-header">
          <div class="integration-logo">Т</div>
          <div>
            <h3 class="integration-name">Т-Инвестиции</h3>
            <div class="integration-status">
              <span class="status-dot" />
              Активно
            </div>
          </div>
        </div>
        <p class="integration-desc">
          Подключите брокерский счёт и получите полный контроль над инвестициями. Все сделки, дивиденды и
          купоны синхронизируются автоматически.
        </p>
        <div class="integration-features">
          <div v-for="(feat, i) in integrationFeatures" :key="i" class="integration-feature">
            <component :is="feat.icon" :size="20" :stroke-width="1.5" />
            <div>
              <strong>{{ feat.title }}</strong>
              <p>{{ feat.desc }}</p>
            </div>
          </div>
        </div>
        <router-link to="/login" class="btn-primary">
          Подключить Т-Инвестиции
          <ArrowRight :size="18" />
        </router-link>
      </div>

      <div class="coming-soon reveal">
        <p class="coming-soon-label">Скоро</p>
        <div class="coming-soon-list">
          <div v-for="broker in comingSoonBrokers" :key="broker.name" class="coming-soon-item">
            <div
              class="coming-soon-avatar"
              :style="{ borderColor: broker.color, color: broker.color }"
            >
              {{ broker.initials }}
            </div>
            <span>{{ broker.name }}</span>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>
