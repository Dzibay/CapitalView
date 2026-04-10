<script setup></script>

<template>
  <header class="header" role="banner">
    <div class="container header-inner">
      <router-link to="/" class="logo" aria-label="CapitalView — на главную">Capital<span>View</span></router-link>

      <nav class="nav" aria-label="Основная навигация">
        <router-link :to="{ path: '/', hash: '#features' }">Возможности</router-link>
        <router-link :to="{ path: '/', hash: '#how-it-works' }">Как это работает</router-link>
        <router-link :to="{ path: '/', hash: '#pricing' }">Тарифы</router-link>
        <router-link :to="{ path: '/', hash: '#faq' }">FAQ</router-link>
        <router-link to="/support">Поддержка</router-link>
      </nav>

      <div class="header-actions">
        <div class="desktop-actions">
          <router-link to="/login" class="btn-ghost">Войти</router-link>
          <router-link to="/login" class="btn-primary-sm">Регистрация</router-link>
        </div>
      </div>
    </div>
  </header>
</template>
