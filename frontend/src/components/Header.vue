<script setup>
import { ref, onMounted } from 'vue'
import { authService } from '../services/authService.js';
import { useRouter } from 'vue-router';

const user = ref(null);
const router = useRouter();

onMounted(async () => {
  try {
    const u = await authService.checkToken();
    if (u) {
      user.value = u
    }
    else {user.value = null}
  }
  catch {
    console.log("Нет токена")
  }
})

const logout = () => {
  authService.logout();
  router.push('/login');
};

</script>


<template>
  <header class="header">
    <div class="logo">
        <router-link to="/">CapitalView</router-link>
    </div>
    
    <div v-if="!user" class="menu">
      <router-link to="/login">Вход</router-link>
      <router-link to="/register">Регистрация</router-link>
    </div>
    <div v-else class="menu">
      <router-link to="/profile">Профиль</router-link>
      <router-link to="/assets">Мои активы</router-link>
      <button @click="logout">Выйти</button>
    </div>
  </header>
</template>



<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background-color: #f5f5f5;
}

.logo {
  font-weight: bold;
  font-size: 1.5rem;
}

.menu a {
  margin-right: 20px;
  text-decoration: none;
  color: #333;
}

.menu a:hover {
  color: #007BFF;
}

.menu button {
  padding: 10px;
  width: 100px;
}
</style>
