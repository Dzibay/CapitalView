<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <div class="footer-top">
        <div class="footer-brand">
          <span class="logo">Capital<span class="logo-accent">View</span></span>
          <span class="version">v1.0</span>
        </div>
        <div class="footer-links">
          <a href="#">Политика конфиденциальности</a>
          <span class="divider" />
          <a href="#">Условия использования</a>
          <span class="divider" />
          <a href="#">Поддержка</a>
        </div>
      </div>
      <div class="footer-bottom">
        <p class="disclaimer">
          Информация, представленная в данном сервисе, носит исключительно информационный характер
          и не является индивидуальной инвестиционной рекомендацией. Финансовые инструменты и операции,
          упомянутые в сервисе, могут не соответствовать вашему инвестиционному профилю и целям.
          Принятие решений о совершении сделок осуществляется вами самостоятельно.
        </p>
        <p class="copyright">&copy; {{ currentYear }} CapitalView. Все права защищены.</p>
      </div>
    </div>
  </footer>
</template>

<script setup>
const currentYear = new Date().getFullYear()
</script>

<style scoped>
.app-footer {
  margin-top: auto;
  border-top: 1px solid #eef0f2;
  background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%);
}

.footer-inner {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px 24px 24px;
}

.footer-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.footer-brand {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.logo {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.3px;
}

.logo-accent {
  color: #5478EA;
}

.version {
  font-size: 11px;
  color: #94a3b8;
  font-weight: 500;
  background: #eef0f2;
  padding: 1px 6px;
  border-radius: 4px;
}

.footer-links {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.footer-links a {
  color: #64748b;
  text-decoration: none;
  font-size: 13px;
  font-weight: 400;
  transition: color 0.15s;
}

.footer-links a:hover {
  color: #5478EA;
}

.divider {
  width: 1px;
  height: 12px;
  background: #d1d5db;
}

.footer-bottom {
  padding-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.disclaimer {
  font-size: 11px;
  line-height: 1.6;
  color: #94a3b8;
  max-width: 800px;
  margin: 0;
}

.copyright {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  margin: 0;
}

@media (max-width: 640px) {
  .footer-top {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
