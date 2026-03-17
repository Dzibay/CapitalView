<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { authService } from '../services/authService.js';

const route = useRoute();
const router = useRouter();

const isLoginMode = ref(true);
const email = ref('root@gmail.com');
const password = ref('root');
const message = ref('');
const loading = ref(false);

onMounted(async () => {
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      const user = await authService.checkToken();
      if (user && user.user) {
        router.push('/dashboard');
      }
    } catch {
      authService.logout();
    }
  }
});

const toggleMode = () => {
  isLoginMode.value = !isLoginMode.value;
  message.value = '';
};

const handleSubmit = async () => {
  message.value = '';
  loading.value = true;

  try {
    if (!isLoginMode.value && (password.value.length < 8 || !/[a-zA-Z]/.test(password.value) || !/\d/.test(password.value))) {
      message.value = 'Пароль: минимум 8 символов, буквы и цифры';
      loading.value = false;
      return;
    }
    if (isLoginMode.value) {
      await authService.login(email.value, password.value);
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) throw new Error('Не удалось сохранить токен авторизации');
      await new Promise(resolve => setTimeout(resolve, 50));
      const redirectPath = router.currentRoute.value.query.redirect || '/dashboard';
      await router.replace(redirectPath);
    } else {
      await authService.register(email.value, password.value);
      await authService.login(email.value, password.value);
      const savedToken = localStorage.getItem('access_token');
      if (!savedToken) throw new Error('Не удалось сохранить токен авторизации');
      await new Promise(resolve => setTimeout(resolve, 50));
      const redirectPath = router.currentRoute.value.query.redirect || '/dashboard';
      await router.replace(redirectPath);
    }
  } catch (err) {
    const defaultMsg = isLoginMode.value ? 'Ошибка входа' : 'Ошибка регистрации';
    message.value = err.response?.data?.msg || err.message || defaultMsg;
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
  <div class="login-page">
    <!-- Фон как на лендинге -->
    <div class="login-bg" aria-hidden="true">
      <div class="gradient-mesh">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
      </div>
    </div>

    <header class="login-header">
      <div class="header-inner">
        <router-link to="/" class="logo">Capital<span>View</span></router-link>
        <router-link to="/" class="btn-ghost">На главную</router-link>
      </div>
    </header>

    <main class="auth-wrapper">
      <div class="auth-card">
        <transition name="fade" mode="out-in">
          <div :key="isLoginMode" class="auth-content">
            <h1 class="auth-title">{{ title }}</h1>
            <p class="auth-subtitle">
              {{ isLoginMode ? 'Войдите в аккаунт для доступа к портфелю' : 'Создайте аккаунт и начните отслеживать инвестиции' }}
            </p>

            <form @submit.prevent="handleSubmit" class="auth-form">
              <div class="input-group">
                <label for="email">Email</label>
                <input
                  id="email"
                  v-model="email"
                  type="email"
                  placeholder="example@mail.ru"
                  required
                  autocomplete="username"
                  class="form-input"
                />
              </div>

              <div class="input-group">
                <label for="password">Пароль</label>
                <input
                  id="password"
                  v-model="password"
                  type="password"
                  :placeholder="isLoginMode ? 'Введите пароль' : 'Минимум 8 символов, буквы и цифры'"
                  required
                  autocomplete="current-password"
                  class="form-input"
                />
              </div>

              <div v-if="route.query.error" class="message message-error">
                {{ oauthErrorText }}
              </div>
              <div v-else-if="message" class="message message-error">
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
            <button type="button" class="link-btn" @click="toggleMode">Зарегистрироваться</button>
          </p>
          <p v-else>
            Уже есть аккаунт?
            <button type="button" class="link-btn" @click="toggleMode">Войти</button>
          </p>
        </div>
      </div>
    </main>

    <footer class="login-footer">
      <router-link to="/" class="logo">Capital<span>View</span></router-link>
      <div class="footer-links">
        <a href="/privacy" target="_blank" rel="noopener noreferrer">Политика конфиденциальности</a>
        <span class="divider" />
        <a href="/terms" target="_blank" rel="noopener noreferrer">Условия использования</a>
      </div>
      <p class="copyright">© {{ new Date().getFullYear() }} CapitalView</p>
    </footer>
  </div>
</template>

<style scoped>
.login-page {
  --color-text: #0f172a;
  --color-text-secondary: #64748b;
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-border: #e2e8f0;
  --color-border-light: #f1f5f9;

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Фон */
.login-bg {
  position: fixed;
  inset: 0;
  z-index: -1;
  overflow: hidden;
}

.gradient-mesh {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse 80% 50% at 50% -20%, rgba(59, 130, 246, 0.15), transparent),
    radial-gradient(ellipse 60% 40% at 100% 0%, rgba(139, 92, 246, 0.12), transparent),
    radial-gradient(ellipse 50% 30% at 0% 50%, rgba(236, 72, 153, 0.08), transparent);
}

.orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.5;
  animation: orbFloat 20s ease-in-out infinite;
}

.orb-1 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.4) 0%, transparent 70%);
  top: -100px;
  right: 10%;
}

.orb-2 {
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.35) 0%, transparent 70%);
  bottom: 20%;
  left: -50px;
  animation-delay: -5s;
}

.orb-3 {
  width: 250px;
  height: 250px;
  background: radial-gradient(circle, rgba(236, 72, 153, 0.25) 0%, transparent 70%);
  top: 40%;
  right: -30px;
  animation-delay: -10s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 30px) scale(0.95); }
  75% { transform: translate(20px, 20px) scale(1.02); }
}

/* Хедер */
.login-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 100;
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}

.header-inner {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.logo {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  text-decoration: none;
  letter-spacing: -0.02em;
}

.logo span {
  color: var(--color-primary);
}

.btn-ghost {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-primary);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 20px;
  transition: background 0.2s;
}

.btn-ghost:hover {
  background: rgba(37, 99, 235, 0.06);
}

/* Контент */
.auth-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 100px 24px 48px;
}

.auth-card {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  padding: 40px;
  border-radius: 20px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}

.auth-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: -0.03em;
  text-align: center;
  margin: 0 0 8px;
  color: var(--color-text);
}

.auth-subtitle {
  font-size: 15px;
  color: var(--color-text-secondary);
  text-align: center;
  margin: 0 0 28px;
  line-height: 1.5;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.input-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 12px 16px;
  border: 1px solid var(--color-border);
  border-radius: 12px;
  font-size: 15px;
  color: var(--color-text);
  background: #fff;
  transition: border-color 0.2s, box-shadow 0.2s;
  box-sizing: border-box;
}

.form-input::placeholder {
  color: #94a3b8;
}

.form-input:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
}

.btn-primary {
  width: 100%;
  padding: 14px 24px;
  background: var(--color-primary);
  color: #fff;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
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
  background: var(--color-border);
}

.auth-divider span {
  font-size: 13px;
  color: var(--color-text-secondary);
}

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 12px 16px;
  background: #fff;
  color: var(--color-text);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  font-size: 15px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s;
}

.btn-google:hover {
  background: var(--color-border-light);
  border-color: #cbd5e1;
}

.google-icon {
  flex-shrink: 0;
}

.message {
  padding: 10px 14px;
  border-radius: 10px;
  font-size: 14px;
}

.message-error {
  background: rgba(239, 68, 68, 0.1);
  color: #dc2626;
  border: 1px solid rgba(239, 68, 68, 0.3);
}

.auth-footer {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--color-border-light);
  text-align: center;
}

.auth-footer p {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin: 0;
}

.link-btn {
  background: none;
  border: none;
  color: var(--color-primary);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  padding: 0;
  font-family: inherit;
}

.link-btn:hover {
  text-decoration: underline;
}

/* Футер */
.login-footer {
  padding: 24px;
  text-align: center;
  border-top: 1px solid var(--color-border-light);
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
}

.login-footer .logo {
  display: inline-block;
  font-size: 16px;
  margin-bottom: 12px;
}

.footer-links {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.footer-links a {
  font-size: 13px;
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: color 0.2s;
}

.footer-links a:hover {
  color: var(--color-primary);
}

.login-footer .divider {
  width: 1px;
  height: 12px;
  background: #cbd5e1;
}

.copyright {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
}

@media (max-width: 480px) {
  .auth-wrapper {
    padding: 88px 16px 32px;
    align-items: flex-start;
  }

  .auth-card {
    padding: 28px 20px;
  }

  .auth-title {
    font-size: 24px;
  }

  .auth-subtitle {
    font-size: 14px;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>