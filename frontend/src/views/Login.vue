<script setup>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const router = useRouter();
const email = ref('');
const password = ref('');
const message = ref('');

onMounted(async () => {
  try {
    const user = await authService.checkToken();
    if (user) router.push('/profile');
  } catch {
    authService.logout();
  }
});

const doLogin = async () => {
  try {
    const res = await authService.login(email.value, password.value);
    localStorage.setItem('access_token', res.data.access_token);
    router.push('/profile');
  } catch (err) {
    message.value = err.response?.data?.msg || 'Ошибка входа';
  }
};
</script>

<template>
  <div>
    <h2>Login</h2>
    <input v-model="email" placeholder="Email" />
    <input v-model="password" type="password" placeholder="Пароль" />
    <button @click="doLogin">Войти</button>
    <p>{{ message }}</p>
    <router-link to="/register">Регистрация</router-link>
  </div>
</template>
