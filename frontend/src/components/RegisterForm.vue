<template>
  <form @submit.prevent="handleRegister">
    <h2>Register</h2>
    <input v-model="email" type="email" placeholder="Email" required />
    <input v-model="password" type="password" placeholder="Password" required />
    <button type="submit">Register</button>
    <p v-if="error" style="color:red">{{ error }}</p>
  </form>
</template>

<script setup>
import { ref } from "vue";
import { register } from "../services/authService.js";

const email = ref("");
const password = ref("");
const error = ref("");

const handleRegister = async () => {
  try {
    await register(email.value, password.value);
    alert("Registered successfully! Please login.");
    email.value = "";
    password.value = "";
    error.value = "";
  } catch (err) {
    error.value = err.response?.data?.msg || "Registration failed";
  }
};
</script>
