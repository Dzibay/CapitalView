<script setup>
import { onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { defaultAuthenticatedPath } from '../utils/defaultAppPath'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  const token = route.query.token
  const error = route.query.error

  if (error) {
    authStore.logout()
    router.replace({ path: '/login', query: { error } })
    return
  }

  if (token) {
    localStorage.setItem('access_token', token)
    authStore.checkToken().then(() => {
      const redirect = (route.query.redirect && String(route.query.redirect).startsWith('/'))
        ? route.query.redirect
        : defaultAuthenticatedPath(authStore.user)
      router.replace(redirect)
    }).catch(() => {
      router.replace('/login')
    })
  } else {
    router.replace('/login')
  }
})
</script>

<template>
  <div class="callback-page">
    <p>Вход выполняется...</p>
  </div>
</template>

<style scoped>
.callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  font-family: inherit;
  color: #6b7280;
}
</style>
