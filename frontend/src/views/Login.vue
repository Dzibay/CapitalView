<script setup>
import Header from '../components/Header.vue'
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
  <Header />
  <div class="form">
    <h2>Вход</h2>
    <input v-model="email" placeholder="Email" />
    <input v-model="password" type="password" placeholder="Пароль" />
    <div class="form-buttons">
      <button @click="doLogin">Войти</button>
      <button>
        <router-link to="/register">Регистрация</router-link>
      </button>
    </div>

    <p>{{ message }}</p>
    
  </div>
</template>


<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: center;
}

.form input {
  width: 400px;
  padding: 20px;
}

.form button {
  width: 190px;
  padding: 20px;
  cursor: pointer;
}
.form-buttons {
  display: flex;
  gap: 10px;
}
.form-buttons a {
  text-decoration: none;
  color: black
}

</style>