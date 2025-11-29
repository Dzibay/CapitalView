<script setup>
import Header from '../components/Header.vue';
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const router = useRouter();

// Состояние: true = Вход, false = Регистрация
const isLoginMode = ref(true);

const email = ref('root@gmail.com');
const password = ref('root');
const message = ref('');
const loading = ref(false);

// Проверка токена при загрузке (только если мы в режиме входа)
// Теперь это обрабатывается в router guard, но оставляем для совместимости
onMounted(async () => {
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      const user = await authService.checkToken();
      if (user && user.user) {
        router.push('/dashboard');
      }
    } catch {
      // Токен недействителен, остаемся на странице логина
      authService.logout();
    }
  }
});

// Переключение режимов и очистка ошибок
const toggleMode = () => {
  isLoginMode.value = !isLoginMode.value;
  message.value = '';
  // Опционально: можно очищать поля, но часто удобнее оставлять введенное
  // email.value = '';
  // password.value = '';
};

const handleSubmit = async () => {
  message.value = '';
  loading.value = true;

  try {
    if (isLoginMode.value) {
      // === Логика ВХОДА ===
      // authService.login уже сохраняет токен автоматически
      const res = await authService.login(email.value, password.value);
      
      // Дополнительная проверка, что токен действительно сохранен
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) {
        throw new Error('Не удалось сохранить токен авторизации');
      }
      
      // Небольшая задержка для гарантии сохранения токена перед навигацией
      await new Promise(resolve => setTimeout(resolve, 50));
      
      // Получаем путь для редиректа из query параметров или используем dashboard
      const redirectPath = router.currentRoute.value.query.redirect || '/dashboard';
      
      // Используем replace вместо push, чтобы избежать возврата на страницу логина через back
      await router.replace(redirectPath);
    } else {
      // === Логика РЕГИСТРАЦИИ ===
      await authService.register(email.value, password.value);
      // Сразу логиним после успешной регистрации
      const res = await authService.login(email.value, password.value);
      
      // Дополнительная проверка, что токен действительно сохранен
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) {
        throw new Error('Не удалось сохранить токен авторизации');
      }
      
      // Небольшая задержка для гарантии сохранения токена перед навигацией
      await new Promise(resolve => setTimeout(resolve, 50));
      
      const redirectPath = router.currentRoute.value.query.redirect || '/dashboard';
      await router.replace(redirectPath);
    }
  } catch (err) {
    const defaultMsg = isLoginMode.value ? 'Ошибка входа' : 'Ошибка регистрации';
    message.value = err.response?.data?.msg || err.message || defaultMsg;
    // Очищаем токен при ошибке (authService.login уже очистит, но для надежности)
    authService.logout();
  } finally {
    loading.value = false;
  }
};

const title = computed(() => isLoginMode.value ? 'Вход в систему' : 'Создание аккаунта');
const submitButtonText = computed(() => loading.value ? 'Загрузка...' : (isLoginMode.value ? 'Войти' : 'Зарегистрироваться'));
</script>

<template>
  <div class="page-container">
    <Header />
    
    <div class="auth-wrapper">
      <div class="auth-card">
        
        <transition name="fade" mode="out-in">
          <div :key="isLoginMode" class="auth-content">
            <h2 class="auth-title">{{ title }}</h2>
            
            <form @submit.prevent="handleSubmit" class="auth-form">
              <div class="input-group">
                <input
                  v-model="email"
                  type="email"
                  placeholder="Email"
                  required
                  autocomplete="username"
                  class="form-input"
                />
              </div>
              
              <div class="input-group">
                <input
                  v-model="password"
                  type="password"
                  placeholder="Пароль"
                  required
                  autocomplete="current-password"
                  class="form-input"
                />
              </div>

              <div v-if="message" class="error-message">
                {{ message }}
              </div>

              <button type="submit" class="btn-primary" :disabled="loading">
                {{ submitButtonText }}
              </button>
            </form>
          </div>
        </transition>

        <div class="auth-footer">
          <p v-if="isLoginMode">
            Нет аккаунта? 
            <a href="#" @click.prevent="toggleMode">Зарегистрироваться</a>
          </p>
          <p v-else>
            Уже есть аккаунт? 
            <a href="#" @click.prevent="toggleMode">Войти</a>
          </p>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* Общий контейнер */
.page-container {
  min-height: 100vh;
  background-color: #f3f4f6;
  display: flex;
  flex-direction: column;
}

/* Центрирование карточки */
.auth-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 20px;
}

/* Карточка */
.auth-card {
  background: white;
  width: 100%;
  max-width: 420px;
  padding: 40px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid #e5e7eb;
}

.auth-title {
  font-size: 24px;
  font-weight: 700;
  text-align: center;
  margin-bottom: 24px;
  color: #1f2937;
}

/* Форма */
.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.input-group {
  width: 100%;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box; /* Важно, чтобы padding не ломал ширину */
}

.form-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Кнопка */
.btn-primary {
  width: 100%;
  padding: 12px;
  background-color: #2563eb;
  color: white;
  font-weight: 600;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  font-size: 15px;
  margin-top: 8px;
}

.btn-primary:hover {
  background-color: #1d4ed8;
}

.btn-primary:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

/* Сообщение об ошибке */
.error-message {
  color: #dc2626;
  font-size: 14px;
  text-align: center;
  background-color: #fef2f2;
  padding: 8px;
  border-radius: 6px;
}

/* Подвал карточки */
.auth-footer {
  margin-top: 24px;
  text-align: center;
  border-top: 1px solid #f3f4f6;
  padding-top: 20px;
}

.auth-footer p {
  color: #6b7280;
  font-size: 14px;
  margin: 0;
}

.auth-footer a {
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
}

.auth-footer a:hover {
  text-decoration: underline;
}

/* === Анимация переходов === */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(5px);
}
</style>