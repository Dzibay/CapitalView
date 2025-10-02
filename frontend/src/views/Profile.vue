<script setup>
import Header from '../components/Header.vue'
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const user = ref(null);
const router = useRouter();



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
  <Header />
  <div class="profile-block">
    <h2>Profile</h2>
    <p v-if="user">Привет, {{ user.email }}!</p>

    <div class="buttons">
      <button>
        <router-link to="/assets">Мои активы</router-link>
      </button>
    </div>

  </div>
</template>


<style>
.profile-block {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.buttons {
  margin-top: 50px;
  display: flex;
  gap: 10px;
}

.buttons button {
  width: 190px;
  padding: 20px;
}

.buttons button a {
  text-decoration: none;
  color: black;
}
</style>