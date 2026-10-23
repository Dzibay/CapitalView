<script setup>
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.store'
import { authService } from '../services/authService'
import CvPageHead from '../cabinet/ui/CvPageHead.vue'
import CvWidget from '../cabinet/ui/CvWidget.vue'
import { LogOut, MessageCircle, CreditCard, Check, Mail, ShieldCheck } from 'lucide-vue-next'
import { dateLong, plural } from '../cabinet/format'
import BrokerConnections from '../cabinet/settings/BrokerConnections.vue'

const authStore = useAuthStore()
const router = useRouter()

/** false только для OAuth без пароля; если поля нет (старый API) — считаем, что пароль есть */
const userHasPassword = computed(() => authStore.user?.has_password !== false)

const handleLogout = () => {
  authStore.logout()
  router.push('/login')
}

// Состояния для настроек профиля
const settings = ref({
  profile: {
    name: authStore.user?.name || '',
    email: authStore.user?.email || '',
  },
  password: {
    current: '',
    new: '',
    confirm: '',
  },
})

// Состояния для UI
const isLoadingProfile = ref(false)
const isLoadingPassword = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')
// Обновляем значения при изменении пользователя в store
watch(() => authStore.user, (newUser) => {
  if (newUser) {
    settings.value.profile.name = newUser.name || ''
    settings.value.profile.email = newUser.email || ''
  }
}, { immediate: true })

// Функция для сохранения настроек профиля
const saveProfile = async () => {
  if (isLoadingProfile.value) return
  
  errorMessage.value = ''
  successMessage.value = ''
  isLoadingProfile.value = true

  try {
    if (!settings.value.profile.name || !settings.value.profile.name.trim()) {
      errorMessage.value = 'Имя не может быть пустым'
      isLoadingProfile.value = false
      return
    }

    const response = await authService.updateProfile(settings.value.profile.name.trim())

    const user = response?.user ?? response?.data?.user
    if (user) {
      authStore.setUser(user)
      successMessage.value = 'Профиль успешно обновлён'
      setTimeout(() => { successMessage.value = '' }, 3000)
    }
  } catch (error) {
    console.error('Ошибка при обновлении профиля:', error)
    errorMessage.value = error.response?.data?.detail || error.message || 'Произошла ошибка при обновлении профиля'
  } finally {
    isLoadingProfile.value = false
  }
}

// Функция для смены пароля
const savePassword = async () => {
  if (isLoadingPassword.value) return
  
  passwordError.value = ''
  passwordSuccess.value = ''

  const { current, new: newPass, confirm } = settings.value.password

  if (userHasPassword.value && !current) {
    passwordError.value = 'Введите текущий пароль'
    return
  }

  if (!newPass || !confirm) {
    passwordError.value = 'Заполните поля нового пароля'
    return
  }

  if (newPass.length < 8 || !/[a-zA-Z]/.test(newPass) || !/\d/.test(newPass)) {
    passwordError.value = 'Пароль: минимум 8 символов, буквы и цифры'
    return
  }

  if (newPass !== confirm) {
    passwordError.value = 'Новый пароль и подтверждение не совпадают'
    return
  }

  if (userHasPassword.value && current === newPass) {
    passwordError.value = 'Новый пароль должен отличаться от текущего'
    return
  }

  isLoadingPassword.value = true
  const wasWithoutPassword = !userHasPassword.value

  try {
    const data = await authService.changePassword(
      userHasPassword.value ? current : null,
      newPass,
    )
    const user = data?.user
    if (user) {
      authStore.setUser(user)
    }
    passwordSuccess.value = wasWithoutPassword
      ? 'Пароль добавлен — теперь можно входить по email и паролю'
      : 'Пароль успешно изменён'
    settings.value.password = { current: '', new: '', confirm: '' }
    setTimeout(() => { passwordSuccess.value = '' }, 3000)
  } catch (error) {
    console.error('Ошибка при смене пароля:', error)
    passwordError.value = error.response?.data?.detail || error.message || 'Произошла ошибка при смене пароля'
  } finally {
    isLoadingPassword.value = false
  }
}


const initials = computed(() => {
  const src = (settings.value.profile.name || settings.value.profile.email || '?').trim()
  const parts = src.split(/[\s@._-]+/).filter(Boolean)
  return ((parts[0]?.[0] || '?') + (parts[1]?.[0] || '')).toUpperCase()
})

const subscription = computed(() => authStore.user?.subscription || null)
const SUB_STATUS = { trial: 'Пробный период', active: 'Подписка активна' }
const subStatus = computed(() => SUB_STATUS[subscription.value?.status] || 'Доступ приостановлен')
const subTone = computed(() => (subscription.value?.has_access ? (subscription.value?.status === 'trial' ? 'trial' : 'on') : 'off'))
const subEndsAt = computed(() => {
  const s = subscription.value
  return s?.current_period_ends_at || s?.trial_ends_at || s?.access_ends_at || null
})
const subDaysLeft = computed(() => (subEndsAt.value ? Math.ceil((new Date(subEndsAt.value).getTime() - Date.now()) / 86400000) : null))

const profileDirty = computed(() => (settings.value.profile.name || '').trim() !== (authStore.user?.name || ''))
const pageMeta = computed(() => [
  settings.value.profile.email,
  authStore.user?.is_admin ? 'администратор' : subStatus.value.toLowerCase(),
])
</script>

<template>
  <div class="st">
    <CvPageHead eyebrow="Аккаунт" title="Настройки" :meta="pageMeta">
      <template #actions>
        <button type="button" class="cv-btn cv-btn--danger" @click="handleLogout">
          <LogOut :size="15" /> Выйти
        </button>
      </template>
    </CvPageHead>

    <div class="cv-grid is-intro">
      <!-- Профиль -->
      <CvWidget class="is-m" style="--i: 0" title="Профиль" subtitle="Как к вам обращаться в кабинете">
        <form class="st__form" @submit.prevent="saveProfile">
          <div class="st__who">
            <span class="st__avatar" aria-hidden="true">{{ initials }}</span>
            <div class="st__who-text">
              <b>{{ authStore.user?.name || 'Без имени' }}</b>
              <span>{{ settings.profile.email || '—' }}</span>
            </div>
          </div>

          <p v-if="errorMessage" class="cv-note cv-note--err" role="alert">{{ errorMessage }}</p>
          <p v-if="successMessage" class="cv-note cv-note--ok" role="status"><Check :size="14" />{{ successMessage }}</p>

          <label class="cv-field">
            <span class="cv-label">Имя</span>
            <input v-model="settings.profile.name" type="text" class="cv-input" placeholder="Введите ваше имя" autocomplete="name" :disabled="isLoadingProfile" />
          </label>
          <div class="cv-field">
            <span id="profile-email-label" class="cv-label">Email</span>
            <p class="cv-input cv-input--static" aria-labelledby="profile-email-label" aria-readonly="true">
              <Mail :size="14" class="st__static-ic" />{{ settings.profile.email || '—' }}
            </p>
          </div>

          <div class="st__actions">
            <button type="submit" class="cv-btn cv-btn--primary" :disabled="isLoadingProfile || !profileDirty">
              {{ isLoadingProfile ? 'Сохранение…' : 'Сохранить' }}
            </button>
          </div>
        </form>
      </CvWidget>

      <!-- Безопасность -->
      <CvWidget
        class="is-m"
        style="--i: 1"
        title="Безопасность"
        :subtitle="userHasPassword ? 'Пароль для входа по email' : 'Вход через Google'"
      >
        <form class="st__form" @submit.prevent="savePassword">
          <p v-if="passwordError" class="cv-note cv-note--err" role="alert">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="cv-note cv-note--ok" role="status"><Check :size="14" />{{ passwordSuccess }}</p>

          <p v-if="!userHasPassword" class="cv-note cv-note--info" role="status">
            <ShieldCheck :size="14" />
            Аккаунт создан через Google. Добавьте пароль, чтобы входить и по email — вход через Google останется.
          </p>

          <label v-if="userHasPassword" class="cv-field">
            <span class="cv-label">Текущий пароль</span>
            <input v-model="settings.password.current" type="password" class="cv-input" placeholder="Введите текущий пароль" autocomplete="current-password" :disabled="isLoadingPassword" />
          </label>
          <div class="st__pair">
            <label class="cv-field">
              <span class="cv-label">Новый пароль</span>
              <input v-model="settings.password.new" type="password" class="cv-input" placeholder="От 8 символов" autocomplete="new-password" :disabled="isLoadingPassword" />
            </label>
            <label class="cv-field">
              <span class="cv-label">Повторите пароль</span>
              <input v-model="settings.password.confirm" type="password" class="cv-input" placeholder="Ещё раз" autocomplete="new-password" :disabled="isLoadingPassword" />
            </label>
          </div>
          <p class="st__hint">Минимум 8 символов, обязательно буквы и цифры.</p>

          <div class="st__actions">
            <button type="submit" class="cv-btn cv-btn--primary" :disabled="isLoadingPassword">
              {{ isLoadingPassword ? 'Сохранение…' : userHasPassword ? 'Изменить пароль' : 'Задать пароль' }}
            </button>
          </div>
        </form>
      </CvWidget>

      <!-- Подключения брокеров (ссылки «/settings#brokers» из импорта и «Обновить портфели») -->
      <BrokerConnections id="brokers" class="is-xl" style="--i: 2" />

      <!-- Подписка -->
      <CvWidget v-if="!authStore.user?.is_admin" class="is-m" style="--i: 2" title="Подписка">
        <div class="st__sub">
          <div class="st__sub-row">
            <span class="st__pill" :class="`is-${subTone}`"><i />{{ subStatus }}</span>
            <span v-if="subDaysLeft != null && subDaysLeft >= 0" class="st__sub-days">
              <b class="cv-num">{{ subDaysLeft }}</b> {{ plural(subDaysLeft, 'день', 'дня', 'дней') }}
            </span>
          </div>
          <p class="st__lead">
            <template v-if="subEndsAt && subscription?.has_access">Доступ открыт до {{ dateLong(subEndsAt) }}. </template>
            <template v-else-if="subEndsAt">Доступ закончился {{ dateLong(subEndsAt) }}. </template>
            Тарифы, продление и оплата через ЮKassa.
          </p>
          <div class="st__actions">
            <router-link to="/billing" class="cv-btn">
              <CreditCard :size="15" /> {{ subscription?.has_access ? 'Управлять подпиской' : 'Выбрать тариф' }}
            </router-link>
          </div>
        </div>
      </CvWidget>

      <!-- Поддержка -->
      <CvWidget id="support" class="is-m" style="--i: 3" title="Поддержка">
        <div class="st__sub">
          <p class="st__lead">
            Чат с командой сервиса и ответы на частые вопросы собраны на отдельной странице.
          </p>
          <div class="st__actions">
            <router-link to="/support" class="cv-btn">
              <MessageCircle :size="15" /> Открыть поддержку
            </router-link>
          </div>
        </div>
      </CvWidget>
    </div>
  </div>
</template>

<style scoped>
.st__form, .st__sub { display: flex; flex-direction: column; gap: 14px; height: 100%; }
.st__who { display: flex; align-items: center; gap: 12px; padding-bottom: 14px; border-bottom: 1px solid var(--cv-line); }
.st__avatar {
  display: grid; place-items: center; flex: none; width: 44px; height: 44px; border-radius: 50%;
  font-family: var(--cv-display); font-size: 15px; font-weight: 600; letter-spacing: .02em; color: var(--cv-accent-ink);
  background: var(--cv-accent-soft); box-shadow: inset 0 0 0 1px var(--cv-accent-line);
}
.st__who-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.st__who-text b { font-size: 14.5px; font-weight: 600; color: var(--cv-ink); }
.st__who-text span { overflow: hidden; font-size: 12.5px; color: var(--cv-mut); text-overflow: ellipsis; white-space: nowrap; }
.st__static-ic { flex: none; margin-right: 8px; color: var(--cv-dim); }
.st__pair { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.st__hint { margin: -4px 0 0; font-size: 12px; color: var(--cv-dim); }
.st__actions { display: flex; gap: 8px; margin-top: auto; padding-top: 4px; }
.st__lead { margin: 0; font-size: 13px; line-height: 1.55; color: var(--cv-mut); }
.st__sub-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.st__sub-days { font-size: 12.5px; color: var(--cv-mut); }
.st__sub-days b { font-family: var(--cv-display); font-size: 22px; font-weight: 600; letter-spacing: -0.02em; color: var(--cv-ink); }
.st__pill {
  display: inline-flex; align-items: center; gap: 7px; height: 26px; padding: 0 10px; border-radius: 99px;
  font-size: 12px; font-weight: 550; color: var(--cv-ink-2); background: rgba(255, 255, 255, .04);
}
.st__pill i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.st__pill.is-on { color: var(--cv-up); background: var(--cv-up-bg); }
.st__pill.is-trial { color: var(--cv-accent-ink); background: var(--cv-accent-soft); }
.st__pill.is-off { color: var(--cv-down); background: var(--cv-down-bg); }
@media (max-width: 600px) {
  .st__pair { grid-template-columns: 1fr; }
  .st__actions > .cv-btn { flex: 1; }
}
</style>
