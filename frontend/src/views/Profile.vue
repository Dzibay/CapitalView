<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const router = useRouter();
const user = ref(null);

const logout = () => {
  authService.logout();
  router.push('/login');
};

onMounted(async () => {
  try {
    const u = await authService.checkToken();
    console.log("Профиль")
    console.log(u)
    if (!u) {
      router.push('/login');
    } else {
      user.value = u;
    }
  } catch {
    authService.logout();
    router.push('/login');
  }
});
</script>

<template>
  <div>
    <h2>Profile</h2>
    <p v-if="user">Привет, {{ user.email }}!</p>
    <button @click="logout">Выйти</button>
  </div>
</template>
