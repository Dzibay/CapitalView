<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/authService.js'

// Компоненты макета
import AppSidebar from '../components/AppSidebar.vue'
import AppHeader from '../components/AppHeader.vue'

const user = ref(null)
const router = useRouter()
const isSidebarVisible = ref(true)

onMounted(async () => {
  try {
    const u = await authService.checkToken()
    if (!u) {
      router.push('/login')
    } else {
      user.value = u['user']
    }
  } catch {
    authService.logout()
    router.push('/login')
  }
})

function toggleSidebar() {
  isSidebarVisible.value = !isSidebarVisible.value
}
</script>

<template>
  <div class="dashboard-layout">
    <AppSidebar :class="{ 'sidebar-hidden': !isSidebarVisible }" />
    <main class="main-content" :class="{ 'full-width': !isSidebarVisible }">
      <AppHeader v-if="user" :user="user" @toggle-sidebar="toggleSidebar" />
      <div class="page-content">
        <router-view />
      </div>
    </main>
  </div>
</template>

<style scoped>
.sidebar-hidden {
  transform: translateX(-100%);
}

.main-content {
  flex-grow: 1;
  margin-left: var(--sidebarWidth);
  transition: margin-left 0.3s ease-in-out;
  min-height: 100vh;
}

.main-content.full-width {
  margin-left: 0;
}

.page-content {
  margin-top: var(--headerHeight);
  padding: var(--spacing);
}
</style>
