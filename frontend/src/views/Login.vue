<script setup>
import Header from '../layouts/LandingHeader.vue';
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const route = useRoute();
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
    if (!isLoginMode.value && password.value.length < 4) {
      message.value = 'Пароль должен быть не менее 4 символов';
      loading.value = false;
      return;
    }
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

const googleAuthUrl = computed(() => {
  const base = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  const redirect = route.query.redirect;
  const path = (base.endsWith('/') ? base + 'auth/google' : base + '/auth/google').replace(/\/+/g, '/');
  const url = path.startsWith('http') ? new URL(path) : new URL(path, window.location.origin);
  if (redirect) url.searchParams.set('state', redirect);
  return url.pathname + url.search;
});

const oauthErrorMessages = {
  no_email: 'Google не предоставил email',
  no_code: 'Не получен код авторизации',
  token_exchange_failed: 'Ошибка обмена кода на токен',
  no_access_token: 'Не получен токен доступа',
  userinfo_failed: 'Не удалось получить данные пользователя',
  oauth_not_configured: 'Google OAuth не настроен',
};
const oauthErrorText = computed(() => {
  const err = route.query.error;
  return err ? (oauthErrorMessages[err] || `Ошибка авторизации: ${err}`) : '';
});
const handleGoogleLogin = () => {
  window.location.href = googleAuthUrl.value;
};
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
                  :placeholder="isLoginMode ? 'Пароль' : 'Пароль (мин. 4 символа)'"
                  required
                  autocomplete="current-password"
                  class="form-input"
                />
              </div>

              <div v-if="route.query.error" class="error-message">
                {{ oauthErrorText }}
              </div>
              <div v-else-if="message" class="error-message">
                {{ message }}
              </div>

              <button type="submit" class="btn-primary" :disabled="loading">
                {{ submitButtonText }}
              </button>

              <div class="auth-divider">
                <span>или</span>
              </div>

              <a :href="googleAuthUrl" class="btn-google" @click.prevent="handleGoogleLogin">
                <svg class="google-icon" viewBox="0 0 24 24" width="20" height="20">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Войти через Google
              </a>
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

.auth-divider {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 4px 0;
}

.auth-divider::before,
.auth-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e5e7eb;
}

.auth-divider span {
  font-size: 13px;
  color: #9ca3af;
}

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 12px;
  background: white;
  color: #374151;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.btn-google:hover {
  background: #f9fafb;
  border-color: #9ca3af;
}

.google-icon {
  flex-shrink: 0;
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

@media (max-width: 480px) {
  .auth-wrapper {
    padding: 16px 12px;
    align-items: flex-start;
    padding-top: 24px;
  }

  .auth-card {
    padding: 24px 20px;
    max-width: 100%;
  }

  .auth-title {
    font-size: 20px;
    margin-bottom: 20px;
  }

  .form-input {
    padding: 10px 14px;
    font-size: 16px;
  }
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