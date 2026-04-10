<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { PRIVACY_POLICY, TERMS_OF_USE } from '../content/legal'
import { ArrowLeft } from 'lucide-vue-next'

const route = useRoute()

const documents = {
  privacy: PRIVACY_POLICY,
  terms: TERMS_OF_USE
}

const document = computed(() => {
  const type = route.path === '/privacy' ? 'privacy' : 'terms'
  return documents[type] ?? PRIVACY_POLICY
})
</script>

<template>
  <div class="legal-page">
    <header class="legal-header">
      <div class="container">
        <router-link to="/" class="back-link">
          <ArrowLeft :size="18" />
          На главную
        </router-link>
        <router-link to="/" class="logo">Capital<span>View</span></router-link>
      </div>
    </header>

    <main class="legal-main">
      <div class="container legal-content">
        <h1 class="legal-title">{{ document.title }}</h1>
        <p class="legal-date">Последнее обновление: {{ document.lastUpdated }}</p>

        <div
          v-for="(section, i) in document.sections"
          :key="i"
          class="legal-section"
        >
          <h2 class="legal-heading">{{ section.heading }}</h2>
          <div class="legal-text" v-html="section.content.replace(/\n/g, '<br>')" />
        </div>
      </div>
    </main>

    <footer class="legal-footer">
      <div class="container">
        <div class="footer-links">
          <a href="/privacy" target="_blank" rel="noopener noreferrer">Политика конфиденциальности</a>
          <span class="divider" />
          <a href="/terms" target="_blank" rel="noopener noreferrer">Условия использования</a>
          <span class="divider" />
          <router-link :to="{ path: '/login', query: { redirect: '/support' } }">Поддержка</router-link>
        </div>
        <p class="copyright">© {{ new Date().getFullYear() }} CapitalView. Все права защищены.</p>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.legal-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #0f172a;
  background: #fff;
}

.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 24px;
}

.legal-header {
  padding: 24px 0;
  border-bottom: 1px solid #e2e8f0;
}

.legal-header .container {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.back-link {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #64748b;
  text-decoration: none;
  transition: color 0.2s;
}

.back-link:hover {
  color: #3b82f6;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
  text-decoration: none;
  letter-spacing: -0.02em;
}

.logo span {
  color: #3b82f6;
}

.legal-main {
  flex: 1;
  padding: 48px 0 64px;
}

.legal-title {
  font-size: 36px;
  font-weight: 700;
  letter-spacing: -0.03em;
  margin: 0 0 8px;
  color: #0f172a;
}

.legal-date {
  font-size: 14px;
  color: #64748b;
  margin: 0 0 40px;
}

.legal-section {
  margin-bottom: 32px;
}

.legal-heading {
  font-size: 20px;
  font-weight: 600;
  margin: 0 0 12px;
  color: #0f172a;
}

.legal-text {
  font-size: 16px;
  line-height: 1.7;
  color: #475569;
}

.legal-text :deep(br) {
  display: block;
  content: '';
  margin-top: 0.5em;
}

.legal-footer {
  padding: 32px 0;
  border-top: 1px solid #e2e8f0;
  background: #f8fafc;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.footer-links a {
  font-size: 13px;
  color: #64748b;
  text-decoration: none;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: #3b82f6;
}

.divider {
  width: 1px;
  height: 12px;
  background: #cbd5e1;
}

.copyright {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
}
</style>
