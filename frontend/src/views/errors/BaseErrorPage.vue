<template>
  <div class="error-landing">
    <div class="error-hero-bg" aria-hidden="true">
      <div class="gradient-mesh">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
        <div class="orb orb-4"></div>
      </div>
    </div>

    <PageLayout>
      <div class="error-container">
        <main class="error-glass-panel">
          <div class="error-header">
            <div class="icon-wrapper">
              <component :is="icon" class="error-icon" :style="{ color: accentColorSolid }" />
            </div>

            <div class="code-block">
              <div v-if="code != null" class="error-code">{{ code }}</div>
              <div class="error-phrase">{{ phrase }}</div>
            </div>
          </div>

          <div class="error-actions">
            <Button variant="primary" size="md" @click="goHome">Главная</Button>
            <Button variant="outline" size="md" @click="reload">Обновить</Button>
          </div>
        </main>
      </div>
    </PageLayout>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import PageLayout from '../../layouts/PageLayout.vue'
import { Button } from '../../components/base'

const props = defineProps({
  code: { type: [String, Number], default: null },
  phrase: { type: String, required: true },
  icon: { type: Object, required: true }
})

const router = useRouter()

const goHome = () => router.push('/')
const reload = () => window.location.reload()

const accentColorSolid = (() => {
  const c = Number(props.code)
  if (c === 503) return '#f59e0b'
  if (c === 500) return '#ef4444'
  if (c >= 400 && c < 500) return '#3b82f6'
  return '#3b82f6'
})()
</script>

<style scoped>
.error-landing {
  --color-text: #0f172a;
  overflow: hidden;
  height: 100vh;

  /* В том же вайбе, что и Home.vue */
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--color-text);
}

.error-container {
  min-height: calc(100vh - 60px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px 12px;
}

.error-glass-panel {
  position: relative;
  background: rgba(248, 250, 252, 0.72);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(241, 245, 249, 1);
  border-radius: 28px;
  padding: 26px 20px;
  width: 100%;
  max-width: 560px;
  text-align: left;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
  overflow: hidden;
}

.error-header {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.icon-wrapper {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59, 130, 246, 0.12);
  flex: 0 0 auto;
}

.error-icon {
  width: 26px;
  height: 26px;
}

.code-block {
  min-width: 0;
}

.error-code {
  font-size: clamp(44px, 8vw, 80px);
  font-weight: 900;
  letter-spacing: -0.04em;
  line-height: 0.95;
  color: var(--color-text);
}

.error-phrase {
  margin-top: 6px;
  font-size: 18px;
  line-height: 1.35;
  font-weight: 800;
  color: #64748b;
}

.error-actions {
  margin-top: 22px;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* Фон */
.error-hero-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
}

.gradient-mesh {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.18), transparent),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(139, 92, 246, 0.12), transparent),
    radial-gradient(ellipse 50% 30% at 0% 50%, rgba(236, 72, 153, 0.08), transparent),
    radial-gradient(ellipse 70% 50% at 100% 100%, rgba(59, 130, 246, 0.10), transparent);
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.35;
  animation: orbFloat 20s ease-in-out infinite;
}

.orb-1 {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.35) 0%, transparent 70%);
  top: -120px;
  right: 8%;
}
.orb-2 {
  width: 260px;
  height: 260px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.26) 0%, transparent 70%);
  bottom: 10%;
  left: -70px;
}
.orb-3 {
  width: 220px;
  height: 220px;
  background: radial-gradient(circle, rgba(236, 72, 153, 0.18) 0%, transparent 70%);
  top: 30%;
  right: -40px;
}
.orb-4 {
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.22) 0%, transparent 70%);
  bottom: -60px;
  left: 20%;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(10px, 10px) scale(1.02); }
  75% { transform: translate(-20px, 20px) scale(1.03); }
}

@media (max-width: 480px) {
  .error-actions { flex-direction: column; width: 100%; }
  :deep(.btn) { width: 100%; } /* Растягиваем ваши кнопки на мобильных */
}
</style>