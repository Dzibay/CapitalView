<script setup></script>

<template>
  <footer class="footer snap-section" role="contentinfo">
    <div class="container footer-inner">
      <div class="footer-brand">
        <router-link to="/" class="logo" aria-label="CapitalView — учёт инвестиций">Capital<span>View</span></router-link>
        <p>Онлайн-сервис для учёта инвестиций, аналитики портфеля и отслеживания дивидендов</p>
      </div>
      <div class="footer-links">
        <div class="footer-col">
          <h4>Продукт</h4>
          <router-link :to="{ path: '/', hash: '#features' }">Возможности</router-link>
          <router-link :to="{ path: '/', hash: '#pricing' }">Бесплатно</router-link>
          <router-link :to="{ path: '/', hash: '#integrations' }">Интеграции</router-link>
        </div>
        <div class="footer-col">
          <h4>Поддержка</h4>
          <router-link :to="{ path: '/', hash: '#faq' }">FAQ на главной</router-link>
          <router-link to="/support">Написать в поддержку</router-link>
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
