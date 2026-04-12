<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { siteNavTopMenu } from '../../constants/siteNav'
import SiteNavDropdown from '../SiteNavDropdown.vue'

const route = useRoute()
const mobileMenuOpen = ref(false)

function isGroupActive(group) {
  const p = route.path
  return group.pathPrefixes.some((prefix) => p === prefix || p.startsWith(`${prefix}/`))
}

function toggleMobileMenu() {
  mobileMenuOpen.value = !mobileMenuOpen.value
}

function closeMobileMenu() {
  mobileMenuOpen.value = false
}

watch(
  () => route.path,
  () => {
    mobileMenuOpen.value = false
  }
)

function onGlobalKeydown(ev) {
  if (ev.key === 'Escape' && mobileMenuOpen.value) {
    ev.preventDefault()
    closeMobileMenu()
  }
}

watch(mobileMenuOpen, (open) => {
  if (typeof document === 'undefined') return
  document.body.style.overflow = open ? 'hidden' : ''
  if (open) {
    window.addEventListener('keydown', onGlobalKeydown)
  } else {
    window.removeEventListener('keydown', onGlobalKeydown)
  }
})

onUnmounted(() => {
  if (typeof document !== 'undefined') {
    document.body.style.overflow = ''
  }
  window.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <header class="header" role="banner">
    <div class="container header-inner">
      <router-link to="/" class="logo" aria-label="CapitalView — на главную">Capital<span>View</span></router-link>

      <nav class="nav nav--desktop" aria-label="Основная навигация">
        <SiteNavDropdown
          v-for="group in siteNavTopMenu"
          :key="group.label"
          :label="group.label"
          :active="isGroupActive(group)"
        >
          <router-link
            v-for="link in group.items"
            :key="link.to"
            :to="link.to"
            role="menuitem"
          >
            {{ link.label }}
          </router-link>
        </SiteNavDropdown>
      </nav>

      <div class="header-mobile">
        <button
          type="button"
          class="header-mobile__toggle"
          :aria-expanded="mobileMenuOpen"
          aria-controls="header-mobile-nav"
          :aria-label="mobileMenuOpen ? 'Закрыть меню' : 'Открыть меню'"
          @click="toggleMobileMenu"
        >
          <span class="header-mobile__burger" :class="{ 'header-mobile__burger--open': mobileMenuOpen }">
            <span class="header-mobile__burger-line" aria-hidden="true" />
            <span class="header-mobile__burger-line" aria-hidden="true" />
            <span class="header-mobile__burger-line" aria-hidden="true" />
          </span>
        </button>

        <Teleport to="body">
          <Transition name="mobile-nav">
            <div
              v-if="mobileMenuOpen"
              id="header-mobile-nav"
              class="header-mobile__backdrop"
              role="dialog"
              aria-modal="true"
              aria-label="Навигация по сайту"
              @click="closeMobileMenu"
            >
              <div class="header-mobile__sheet" @click.stop>
                <router-link
                  to="/"
                  class="header-mobile__brand"
                  aria-label="CapitalView — на главную"
                  @click="closeMobileMenu"
                >
                  Capital<span>View</span>
                </router-link>
                <nav class="header-mobile__nav" aria-label="Мобильная навигация">
                  <details
                    v-for="group in siteNavTopMenu"
                    :key="group.label"
                    class="header-mobile__sub"
                  >
                    <summary class="header-mobile__sub-summary">{{ group.label }}</summary>
                    <div class="header-mobile__sub-panel">
                      <router-link
                        v-for="link in group.items"
                        :key="link.to"
                        :to="link.to"
                        class="header-mobile__link"
                        @click="closeMobileMenu"
                      >
                        {{ link.label }}
                      </router-link>
                    </div>
                  </details>
                </nav>
              </div>
            </div>
          </Transition>
        </Teleport>
      </div>

      <div class="header-actions">
        <nav class="desktop-actions" aria-label="Вход и регистрация">
          <router-link to="/login" class="btn-ghost">Войти</router-link>
          <router-link to="/login" class="btn-primary-sm">Регистрация</router-link>
        </nav>
      </div>
    </div>
  </header>
</template>
