<template>
  <form @submit.prevent="handleLogin">
    <h2>Login</h2>
    <input v-model="email" type="email" placeholder="Email" required />
    <input v-model="password" type="password" placeholder="Password" required />
    <button type="submit">Login</button>
    <p v-if="error" style="color:red">{{ error }}</p>
  </form>
</template>

<script setup>
import { ref } from "vue";
import { login } from "../services/authService.js";

const email = ref("");
const password = ref("");
const error = ref("");

const handleLogin = async () => {
  try {
    await login(email.value, password.value);
    alert("Login successful!");
    error.value = "";
  } catch (err) {
    error.value = err.response?.data?.msg || "Login failed";
  }
};
</script>
