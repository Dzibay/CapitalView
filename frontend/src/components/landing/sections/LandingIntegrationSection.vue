<script setup>
import { ArrowRight, ArrowUpRight } from 'lucide-vue-next'

defineProps({
  bullets: { type: Array, required: true },
  comingSoonBrokers: { type: Array, required: true }
})
</script>

<template>
  <section id="integrations" class="section snap-section">
    <div class="container">
      <div class="integration-highlight reveal">
        <div class="integration-col-text">
          <h2 class="integration-heading">
            Подключите брокера<br>за 2 минуты
          </h2>
          <ul class="integration-bullets">
            <li v-for="(bullet, i) in bullets" :key="i">
              <ArrowRight :size="16" :stroke-width="2" />
              <span>{{ bullet }}</span>
            </li>
          </ul>
          <p class="integration-body">
            Получите полный контроль над инвестициями. Все сделки, дивиденды и купоны
            синхронизируются автоматически через официальный API.
          </p>
          <router-link to="/login" class="integration-cta">
            Подключить Т-Инвестиции
            <ArrowUpRight :size="18" :stroke-width="2" />
          </router-link>
        </div>

        <div class="integration-col-visual">
          <div class="broker-card">
            <div class="broker-card-header">
              <div class="broker-logo">Т</div>
              <div>
                <div class="broker-name">Т-Инвестиции</div>
                <div class="broker-status">
                  <span class="status-dot" />
                  Активно
                </div>
              </div>
            </div>
            <div class="broker-stats">
              <div class="broker-stat">
                <span class="broker-stat-label">Портфелей</span>
                <span class="broker-stat-value">3</span>
              </div>
              <div class="broker-stat">
                <span class="broker-stat-label">Активов</span>
                <span class="broker-stat-value">24</span>
              </div>
              <div class="broker-stat">
                <span class="broker-stat-label">Синхр.</span>
                <span class="broker-stat-value">Авто</span>
              </div>
            </div>
          </div>

          <div class="coming-soon">
            <span class="coming-soon-label">Скоро</span>
            <div class="coming-soon-list">
              <div
                v-for="broker in comingSoonBrokers"
                :key="broker.name"
                class="coming-soon-item"
              >
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
      </div>
    </div>
  </section>
</template>

<style scoped>
.integration-highlight {
  display: grid;
  grid-template-columns: 1fr;
  gap: 48px;
  background: rgba(139, 92, 246, 0.04);
  border: 1px solid rgba(139, 92, 246, 0.08);
  border-radius: 24px;
  padding: clamp(32px, 5vw, 56px);
}

.integration-heading {
  font-family: var(--font-display);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.025em;
  color: var(--color-text);
  margin-bottom: 28px;
}

.integration-bullets {
  list-style: none;
  padding: 0;
  margin: 0 0 24px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.integration-bullets li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text);
}

.integration-bullets li svg {
  color: var(--color-accent-purple);
  flex-shrink: 0;
}

.integration-body {
  font-size: 15px;
  line-height: 1.65;
  color: var(--color-text-secondary);
  max-width: 400px;
  margin-bottom: 32px;
}

.integration-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 14px 28px;
  border-radius: 999px;
  font-size: 15px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
  background: var(--color-accent-purple);
  transition: background 0.2s, transform 0.15s;
}

.integration-cta:hover {
  background: #7c3aed;
  transform: translateY(-1px);
}

.integration-col-visual {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.broker-card {
  background: #fff;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 16px;
  padding: 24px;
}

.broker-card-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 24px;
}

.broker-logo {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  background: #fef08a;
  color: var(--color-text);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 700;
  flex-shrink: 0;
}

.broker-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 2px;
}

.broker-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--color-success);
}

.status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--color-success);
}

.broker-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light);
}

.broker-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.broker-stat-label {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.broker-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text);
}

.coming-soon {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.coming-soon-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.coming-soon-list {
  display: flex;
  gap: 20px;
}

.coming-soon-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.coming-soon-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  border: 2px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.coming-soon-item span {
  font-size: 13px;
  color: var(--color-text-secondary);
}

@media (min-width: 900px) {
  .integration-highlight {
    grid-template-columns: 1fr 1fr;
    align-items: start;
  }
}
</style>
