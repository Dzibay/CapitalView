<script setup>
const year = new Date().getFullYear()
</script>

<template>
  <footer class="cv-foot">
    <div class="cv-foot__row">
      <span class="cv-foot__brand">© {{ year }} CapitalView</span>
      <nav class="cv-foot__links" aria-label="Документы">
        <a href="/privacy" target="_blank" rel="noopener noreferrer">Конфиденциальность</a>
        <a href="/terms" target="_blank" rel="noopener noreferrer">Условия</a>
        <router-link to="/support">Поддержка</router-link>
      </nav>
    </div>
    <p class="cv-foot__disclaimer">
      Информация в сервисе носит исключительно информационный характер и не является индивидуальной инвестиционной
      рекомендацией. Финансовые инструменты и операции могут не соответствовать вашему инвестиционному профилю и целям.
      Решения о сделках вы принимаете самостоятельно.
    </p>
  </footer>
</template>

<style scoped>
.cv-foot {
  margin-top: auto;
  padding: 28px var(--cv-pad) 28px;
  color: var(--cv-dim);
  font-size: 12px;
}
.cv-foot__row { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.cv-foot__brand { color: var(--cv-mut); font-weight: 500; }
.cv-foot__links { display: flex; gap: 18px; }
.cv-foot__links a { color: var(--cv-mut); text-decoration: none; transition: color .2s; }
.cv-foot__links a:hover { color: var(--cv-ink); }
.cv-foot__disclaimer { margin: 12px 0 0; font-size: 12px; color: var(--cv-dim); max-width: 920px; line-height: 1.55; }

@media (max-width: 768px) {
  .cv-foot { padding: 20px 14px 24px; }
}
</style>
