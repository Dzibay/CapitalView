<script setup>
import { ref } from 'vue'

const props = defineProps({
  tabs: { type: Array, required: true }
})

const activeTab = ref(props.tabs[0]?.id ?? '')
</script>

<template>
  <section class="section snap-section">
    <div class="container">
      <h2 class="security-heading reveal">Безопасность без компромиссов</h2>

      <div class="security-tabs reveal">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="security-tab"
          :class="{ active: activeTab === tab.id }"
          type="button"
          @click="activeTab = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="security-content reveal">
        <template v-for="tab in tabs" :key="tab.id">
          <div v-if="activeTab === tab.id" class="security-panel">
            <div class="security-panel-icon">
              <component :is="tab.icon" :size="32" :stroke-width="1.5" />
            </div>
            <div class="security-panel-text">
              <h3 class="security-panel-heading">{{ tab.heading }}</h3>
              <p class="security-panel-body">{{ tab.body }}</p>
            </div>
          </div>
        </template>
      </div>
    </div>
  </section>
</template>

<style scoped>
.security-heading {
  font-family: var(--font-display);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: 300;
  line-height: 1.08;
  letter-spacing: -0.025em;
  color: var(--color-text);
  text-align: center;
  margin-bottom: 32px;
}

.security-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  margin-bottom: 40px;
  flex-wrap: wrap;
}

.security-tab {
  padding: 10px 22px;
  border-radius: 999px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  background: transparent;
  border: 1px solid var(--color-border);
  cursor: pointer;
  transition: all 0.2s;
}

.security-tab:hover {
  color: var(--color-text);
  border-color: var(--color-text-secondary);
}

.security-tab.active {
  background: var(--color-text);
  color: #fff;
  border-color: var(--color-text);
}

.security-content {
  max-width: 800px;
  margin: 0 auto;
  background: rgba(16, 185, 129, 0.04);
  border: 1px solid rgba(16, 185, 129, 0.1);
  border-radius: 20px;
  padding: clamp(28px, 4vw, 48px);
}

.security-panel {
  display: flex;
  align-items: flex-start;
  gap: 24px;
}

.security-panel-icon {
  flex-shrink: 0;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: rgba(16, 185, 129, 0.1);
  color: var(--color-success);
  display: flex;
  align-items: center;
  justify-content: center;
}

.security-panel-heading {
  font-family: var(--font-display);
  font-size: clamp(20px, 2.5vw, 26px);
  font-weight: 400;
  line-height: 1.25;
  color: var(--color-text);
  margin-bottom: 12px;
}

.security-panel-body {
  font-size: 15px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

@media (max-width: 600px) {
  .security-panel {
    flex-direction: column;
    gap: 16px;
  }

  .security-tab {
    font-size: 13px;
    padding: 8px 16px;
  }
}
</style>
