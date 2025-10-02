<template>
  <div class="assets-page">
    <h1>Мои активы</h1>
    <div v-if="loading">Загрузка...</div>
    <div v-else-if="assets.length === 0">Активов нет</div>
    <ul v-else>
      <li v-for="asset in assets" :key="asset.id">
        {{ asset.count }} {{ asset.name }} — {{ asset.price }} {{ asset.currency }}
      </li>
    </ul>
  </div>
</template>

<script>
import assetsService from "../services/assetsService";

export default {
  name: "Assets",
  data() {
    return {
      assets: [],
      loading: true,
    };
  },
  async mounted() {
    try {
      this.assets = await assetsService.getAssets();
    } catch (err) {
      console.error("Ошибка получения активов:", err);
    } finally {
      this.loading = false;
    }
  },
};
</script>
