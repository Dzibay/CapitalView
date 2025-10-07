<script setup>
defineProps({
  user: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['toggle-sidebar']);

const handleToggle = () => {
  emit('toggle-sidebar');
};
</script>

<template>
  <header class="header">
    <button @click="handleToggle" class="burger-button">
      <svg xmlns="http://www.w3.org/2000/svg" height="24px" viewBox="0 0 24 24" width="24px" fill="#000000"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>
    </button>
    <h1 class="page-title">Мой капитал</h1>
    <div class="user-profile">
      <img :src="user.avatarUrl" alt="User Avatar" class="avatar">
      <div class="user-info">
        <span class="user-name">{{ user.firstName }} {{ user.lastName }}</span>
        <span class="user-email">{{ user.email }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  display: flex;
  align-items: center;
  padding: 1.5rem 2rem;
  background-color: #fff;
  border-bottom: 1px solid #e5e7eb;
}
.burger-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  margin-right: 1rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.burger-button:hover {
  background-color: #f3f4f6;
}
.page-title {
  font-size: 1.75rem;
  font-weight: 600;
  color: #111827;
  flex-grow: 1;
}
.user-profile {
  display: flex;
  align-items: center;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  margin-right: 0.75rem;
}
.user-info {
  display: flex;
  flex-direction: column;
  text-align: right;
}
.user-name {
  font-weight: 600;
  color: #1f2937;
}
.user-email {
  font-size: 0.875rem;
  color: #6b7280;
}
</style>