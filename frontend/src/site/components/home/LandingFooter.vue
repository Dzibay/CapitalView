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
          <router-link :to="{ name: 'site-free' }">Бесплатно</router-link>
          <router-link :to="{ path: '/', hash: '#pricing' }">Тарифы</router-link>
          <router-link :to="{ path: '/', hash: '#integrations' }">Интеграции</router-link>
        </div>
        <div class="footer-col">
          <h4>Сайт</h4>
          <router-link to="/features/portfolio">Учёт портфеля</router-link>
          <router-link to="/compare/investment-tracking-apps">Сравнение сервисов</router-link>
          <router-link to="/guides/investment-tracking-excel">Учёт в Excel</router-link>
          <router-link to="/blog">Блог</router-link>
        </div>
        <div class="footer-col">
          <h4>Поддержка</h4>
          <router-link :to="{ path: '/', hash: '#faq' }">FAQ на главной</router-link>
          <router-link :to="{ path: '/login', query: { redirect: '/support' } }">Написать в поддержку</router-link>
        </div>
      </div>
    </div>
    <div class="container footer-bottom">
      <div class="footer-bottom__meta">
        <p class="footer-copyright">© 2026 CapitalView. Все права защищены.</p>
        <nav class="footer-legal" aria-label="Правовая информация">
          <router-link to="/privacy">Политика конфиденциальности</router-link>
          <span class="footer-legal__sep" aria-hidden="true">·</span>
          <router-link to="/terms">Условия использования</router-link>
        </nav>
      </div>
    </div>
  </footer>
</template>
