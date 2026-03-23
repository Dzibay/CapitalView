<script setup></script>

<template>
  <footer class="footer snap-section">
    <div class="container footer-inner">
      <div class="footer-brand">
        <router-link to="/" class="logo">Capital<span>View</span></router-link>
        <p>Учёт и аналитика инвестиционного портфеля</p>
      </div>
      <div class="footer-links">
        <div class="footer-col">
          <h4>Продукт</h4>
          <a href="#features">Возможности</a>
          <a href="#pricing">Бесплатно</a>
          <a href="#integrations">Интеграции</a>
        </div>
        <div class="footer-col">
          <h4>Поддержка</h4>
          <a href="#faq">FAQ</a>
          <router-link :to="{ path: '/login', query: { redirect: '/settings#support' } }">
            Написать нам
          </router-link>
        </div>
        <div class="footer-col">
          <h4>Правовая информация</h4>
          <a href="/privacy" target="_blank" rel="noopener noreferrer">Политика конфиденциальности</a>
          <a href="/terms" target="_blank" rel="noopener noreferrer">Условия использования</a>
        </div>
      </div>
    </div>
    <div class="container footer-bottom">
      <p>© 2026 CapitalView. Все права защищены.</p>
    </div>
  </footer>
</template>
