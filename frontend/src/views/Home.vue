<template>
  <div class="home">
    <Header />

    <!-- First section -->
    <section class="hero">
        <div class="title-text">
            <h1>Следите за ростом <br>
                вашего портфеля</h1>
            <p>Все активы и доходность в одном месте — <br>
                прозрачная аналитика и удобное <br>
                отслеживание инвестиций</p>
        </div>
    </section>
  </div>
</template>

<script setup>
import Header from '../components/Header.vue'
</script>

<style scoped>
.home {
  font-family: Arial, sans-serif;
}

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
  margin-left: 1rem;
  text-decoration: none;
  color: #333;
}

.menu a:hover {
  color: #007BFF;
}

.hero {
  text-align: center;
  padding: 4rem 2rem;
  background-color: #e0f7fa;
}

.hero h1 {
  font-size: 2.5rem;
  margin-bottom: 1rem;
}

.hero p {
  font-size: 1.2rem;
  margin-bottom: 2rem;
}

.btn-primary {
  display: inline-block;
  padding: 0.75rem 1.5rem;
  background-color: #007BFF;
  color: white;
  text-decoration: none;
  border-radius: 4px;
}

.btn-primary:hover {
  background-color: #0056b3;
}
</style>
