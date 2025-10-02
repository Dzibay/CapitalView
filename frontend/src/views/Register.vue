<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const router = useRouter();
const email = ref('');
const password = ref('');
const message = ref('');

const doRegister = async () => {
  try {
    await authService.register(email.value, password.value);
    // После регистрации сразу логиним
    const res = await authService.login(email.value, password.value);
    localStorage.setItem('access_token', res.data.access_token);
    router.push('/profile');
  } catch (err) {
    message.value = err.response?.data?.msg || 'Ошибка регистрации';
  }
};
</script>

<template>
  <div>
    <h2>Register</h2>
    <input v-model="email" placeholder="Email" />
    <input v-model="password" type="password" placeholder="Пароль" />
    <button @click="doRegister">Зарегистрироваться</button>
    <p>{{ message }}</p>
    <router-link to="/login">Вход</router-link>
  </div>
</template>
