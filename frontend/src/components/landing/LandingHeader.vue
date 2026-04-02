<script setup></script>

<template>
  <header class="header" role="banner">
    <div class="container header-inner">
      <router-link to="/" class="logo" aria-label="CapitalView — на главную">Capital<span>View</span></router-link>

      <nav class="nav" aria-label="Основная навигация">
        <a href="#features">Возможности</a>
        <a href="#how-it-works">Как это работает</a>
        <a href="#pricing">Тарифы</a>
        <a href="#faq">FAQ</a>
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
