<script setup>
import { ArrowRight, Check } from 'lucide-vue-next'
</script>

<template>
  <div class="hero-scene-root">
    <section class="hero-scene" aria-labelledby="hero-scene-title">
      <div class="hero-scene-content container">
        <div class="hero-center">
          <div class="hero-badge">
            <Check :size="14" :stroke-width="2.5" />
            Сервис временно бесплатный
          </div>
          <h1 id="hero-scene-title" class="hero-scene-title">
            Ваши инвестиции.<br />Одна картина.
          </h1>
          <p class="hero-scene-lead">
            Объединяйте брокерские счета, следите за доходностью и дивидендами — в одном спокойном
            интерфейсе, без таблиц и ручных пересчётов.
          </p>
          <div class="hero-scene-cta">
            <router-link to="/login" class="btn-hero-primary">
              Начать бесплатно
              <ArrowRight :size="18" />
            </router-link>
            <a href="#how-it-works" class="btn-hero-ghost">Как это работает</a>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero-scene-root {
  position: relative;
  min-height: 100%;
  box-sizing: border-box;
}

.hero-scene {
  position: relative;
  z-index: 4;
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 88px 0 clamp(48px, 12vh, 120px);
  box-sizing: border-box;
}

.hero-scene-content {
  position: relative;
  z-index: 5;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  flex: 1;
  justify-content: center;
  padding-bottom: clamp(32px, 6vh, 56px);
}

.hero-center {
  text-align: center;
  max-width: 720px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 999px;
  margin-bottom: 18px;
  letter-spacing: 0.02em;
}

.hero-scene-title {
  margin: 0 0 16px;
  font-size: clamp(34px, 5.5vw + 12px, 56px);
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 1.08;
  color: #0f172a;
}

.hero-scene-lead {
  margin: 0 0 28px;
  font-size: clamp(16px, 1.2vw + 14px, 19px);
  line-height: 1.55;
  color: #64748b;
  font-weight: 450;
}

.hero-scene-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.btn-hero-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 32px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.22);
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-hero-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.28);
}

.btn-hero-ghost {
  display: inline-flex;
  align-items: center;
  padding: 16px 28px;
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
  text-decoration: none;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  transition: border-color 0.2s, background 0.2s;
}

.btn-hero-ghost:hover {
  border-color: #cbd5e1;
  background: #fff;
}

@media (max-width: 767px) {
  .hero-scene {
    padding: 76px 0 20px;
    min-height: 100vh;
    min-height: 100dvh;
  }
}
</style>
