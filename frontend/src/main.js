import { createApp } from 'vue';
import { createPinia } from 'pinia';
import { piniaPersistedState } from './stores/plugins/persist';
import App from './App.vue';
import router from './router';
import './assets/main.css'

function bootstrap() {
  const app = createApp(App);
  const pinia = createPinia();
  pinia.use(piniaPersistedState);

  app.use(pinia);
  app.use(router);
  app.mount('#app');
}

// Демо-режим без backend (`npm run dev:demo`): адаптер axios ставится до первой навигации роутера
if (import.meta.env.DEV && import.meta.env.VITE_MOCK_API) {
  import('./dev/mockApi.js').then((m) => {
    m.installMockApi();
    bootstrap();
  });
} else {
  bootstrap();
}
