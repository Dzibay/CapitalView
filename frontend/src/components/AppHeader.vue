<script setup>
import { ref } from 'vue'

defineProps({
  user: {
    type: Object,
    required: true,
  },
});

const emit = defineEmits(['toggle-sidebar']);
const sidebar = ref(false)

const handleToggle = () => {
  emit('toggle-sidebar');
  sidebar.value = !sidebar.value
};
</script>

<template>
  <header class="header" :class="sidebar ? 'sidebarOff' : 'sidebarOn'">
    <button @click="handleToggle" class="burger-button">
      <svg xmlns="http://www.w3.org/2000/svg" width="30" height="30" fill="none" viewBox="0 0 30 30">
        <path fill="#000" d="m5.861 2.79.247-.001h.673l.728-.001a516.191 516.191 0 0 1 2.582-.001h.502c1.047-.002 2.095-.001 3.142 0 .958 0 1.915 0 2.872-.002a1595.764 1595.764 0 0 1 4.608-.003h3.137c.857.006 1.493.29 2.118.87.608.642.744 1.35.74 2.21l.001.246v.673l.001.728c.001.475.002.95.001 1.424v1.66c.002 1.047.001 2.095 0 3.142 0 .958 0 1.915.002 2.872a1613.494 1613.494 0 0 1 .003 4.608v3.137c-.006.857-.29 1.493-.87 2.118-.642.608-1.35.744-2.21.74l-.246.001h-.673l-.728.001-1.424.001h-1.66c-1.047.002-2.095.001-3.142 0-.958 0-1.915 0-2.872.002a1613.494 1613.494 0 0 1-4.608.003H5.649c-.858-.006-1.494-.29-2.119-.87-.608-.642-.744-1.35-.74-2.21l-.001-.246v-.673l-.001-.728a520.183 520.183 0 0 1-.001-2.582v-.502c-.002-1.047-.001-2.095 0-3.142 0-.958 0-1.915-.002-2.872a1595.764 1595.764 0 0 1-.003-4.608V5.649c.006-.858.29-1.494.87-2.119.642-.608 1.35-.744 2.21-.74Zm-.935 2.234c-.276.434-.255.858-.254 1.359v.867l-.001.686a675.997 675.997 0 0 0-.001 2.436v3.435l-.002 2.708a1897.352 1897.352 0 0 0-.003 4.344 417.803 417.803 0 0 0 0 2.008v.951c.002.406.006.846.273 1.177.91.837 3.943.317 4.085.317V4.688c-1.728-.257-1.728-.257-4.097.337Zm6.031-.337v20.625l6.676.011 2.108.005a2590.23 2590.23 0 0 0 2.08.003 269.142 269.142 0 0 0 1.454.003h.527l.154.001c.359-.002.75-.041 1.04-.273.375-.412.333-.923.332-1.445v-.867l.002-.686a601.633 601.633 0 0 0 0-2.436v-3.435l.002-2.708a1984.922 1984.922 0 0 0 .003-4.344 392.776 392.776 0 0 0 0-2.008 112.746 112.746 0 0 0 0-.951c-.002-.406-.006-.846-.273-1.177-.356-.327-.79-.335-1.246-.332h-.166a122.771 122.771 0 0 0-.956.001c-.36 0-.72 0-1.08.002h-1.012l-2.962.004-6.683.008Z"/>
      </svg>
    </button>
    
    <div class="user-profile">
      <img src="https://avatar.iran.liara.run/public/46" alt="User Avatar" class="avatar">
      <div class="user-info">
        <span class="user-name">{{ user.name }}</span>
        <span class="user-email">{{ user.email }}</span>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  position: fixed;
  height: var(--headerHeight);
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--spacing);
  background-color: #fff;
  transition: width 0.3s ease-in-out;
  box-shadow: 0 4px 10px rgba(0,0,0,0.05);
}
.header.sidebarOn {
  width: calc(100% - var(--sidebarWidth))
}
header.sidebarOff {
  width: 100%;
}
.burger-button {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 12px;
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
  gap: calc(var(--spacing) / 2);
  align-items: center;
}
.user-profile:hover {
  cursor: pointer;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
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