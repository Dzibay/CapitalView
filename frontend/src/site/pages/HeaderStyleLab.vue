<script setup>
import SiteSeoPage from '../components/SiteSeoPage.vue'

/**
 * Черновая страница для сравнения вариантов шапки и кнопок.
 * Только токены палитры лендинга: slate, серые, синий primary, белый.
 */
const navDemo = ['Учёт портфеля', 'Акции и облигации', 'Сервис и гайды']

const buttonRows = [
  {
    id: 'a',
    title: 'A. Стекло + slate (как герой)',
    desc: 'Вторичный — полупрозрачный с рамкой; основной — градиент сланца.',
    loginClass: 'lab-b--a-login',
    regClass: 'lab-b--a-reg',
  },
  {
    id: 'b',
    title: 'B. Текст + градиент',
    desc: 'Войти без «коробки», только вес шрифта; регистрация — объёмная кнопка.',
    loginClass: 'lab-b--b-login',
    regClass: 'lab-b--b-reg',
  },
  {
    id: 'c',
    title: 'C. Два контура',
    desc: 'Обе в рамке: войти slate, регистрация — контур primary.',
    loginClass: 'lab-b--c-login',
    regClass: 'lab-b--c-reg',
  },
  {
    id: 'd',
    title: 'D. Светлая заливка + primary',
    desc: 'Войти на фоне #f1f5f9; регистрация — заливка primary.',
    loginClass: 'lab-b--d-login',
    regClass: 'lab-b--d-reg',
  },
  {
    id: 'e',
    title: 'E. Primary пара',
    desc: 'Войти outline primary; регистрация — сплошной primary.',
    loginClass: 'lab-b--e-login',
    regClass: 'lab-b--e-reg',
  },
  {
    id: 'f',
    title: 'F. Компактные пилюли',
    desc: 'Одинаковая высота, оба с лёгкой тенью; войти светлый, регистрация тёмный slate.',
    loginClass: 'lab-b--f-login',
    regClass: 'lab-b--f-reg',
  },
  {
    id: 'g',
    title: 'G. Минимум декора',
    desc: 'Войти подчёркивание при hover; регистрация — плоский slate без градиента.',
    loginClass: 'lab-b--g-login',
    regClass: 'lab-b--g-reg',
  },
  {
    id: 'h',
    title: 'H. Сегмент (связанная пара)',
    desc: 'Общая рамка, внутри два сегмента — визуально одна группа действий.',
    loginClass: 'lab-b--h-login',
    regClass: 'lab-b--h-reg',
    segmented: true,
  },
]
</script>

<template>
  <SiteSeoPage>
  <div class="header-lab">
    <div class="header-lab__intro">
      <p class="header-lab__badge">Черновик · не для индексации</p>
      <h1 class="header-lab__title">Варианты шапки и кнопок</h1>
      <p class="header-lab__lead">
        Ниже — разные приёмы вёрстки при одной палитре (slate, серые, синий primary). Выберите понравившийся вариант —
        его можно перенести в боевой <code>LandingHeader</code> и <code>landing-page.css</code>.
      </p>
      <p class="header-lab__url">Адрес страницы: <code>/labs/header-style</code></p>
      <router-link to="/" class="header-lab__back">← На главную</router-link>
    </div>

    <section class="header-lab__section" aria-labelledby="lab-headers-h">
      <h2 id="lab-headers-h" class="header-lab__h2">Шапка (десктоп, макет ~1120px)</h2>
      <p class="header-lab__hint">Кнопки справа нейтральные-заглушки, чтобы сравнивать именно «коробку» шапки и навигацию.</p>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">1. Стекло + навигация в чипе</h3>
        <p class="header-lab__desc">Как сейчас на сайте: размытие, навигация в светлой капсуле.</p>
        <div class="header-lab__viewport">
          <div class="lab-h lab-h--glass-chip">
            <div class="lab-h__inner">
              <span class="lab-h__logo">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--chip" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__pill">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">2. Плоская светлая полоса</h3>
        <p class="header-lab__desc">Без сильного стекла; акцент — тонкая граница и воздух.</p>
        <div class="header-lab__viewport">
          <div class="lab-h lab-h--flat">
            <div class="lab-h__inner">
              <span class="lab-h__logo">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--plain" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__link">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">3. Нижняя линия-акцент (primary)</h3>
        <p class="header-lab__desc">Минимализм: ссылки без фона, цветная полоска снизу всей шапки.</p>
        <div class="header-lab__viewport">
          <div class="lab-h lab-h--accent-line">
            <div class="lab-h__inner">
              <span class="lab-h__logo">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--plain" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__link">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">4. Разделители между пунктами</h3>
        <p class="header-lab__desc">Навигация как «таблетки» с вертикальными разделителями, без цветных заливок.</p>
        <div class="header-lab__viewport">
          <div class="lab-h lab-h--dividers">
            <div class="lab-h__inner">
              <span class="lab-h__logo">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--divided" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__seg">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">5. Тёмная полоса (slate)</h3>
        <p class="header-lab__desc">Тот же бренд, но инверсия: фон #0f172a, светлый текст, лёгкий контраст на hover.</p>
        <div class="header-lab__viewport">
          <div class="lab-h lab-h--dark">
            <div class="lab-h__inner">
              <span class="lab-h__logo lab-h__logo--on-dark">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--on-dark" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__link-dark">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy-dark">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>

      <article class="header-lab__card">
        <h3 class="header-lab__h3">6. «Парящая» панель</h3>
        <p class="header-lab__desc">Шапка как отдельная карточка с тенью и скруглением (в превью — отступ от краёв).</p>
        <div class="header-lab__viewport header-lab__viewport--float">
          <div class="lab-h lab-h--floating">
            <div class="lab-h__inner">
              <span class="lab-h__logo">Capital<span>View</span></span>
              <nav class="lab-h__nav lab-h__nav--chip lab-h__nav--chip-soft" aria-label="Демо">
                <span v-for="item in navDemo" :key="item" class="lab-h__pill">{{ item }}</span>
              </nav>
              <div class="lab-h__cta lab-h__cta--dummy">
                <span>Войти</span><span>Регистрация</span>
              </div>
            </div>
          </div>
        </div>
      </article>
    </section>

    <section class="header-lab__section" aria-labelledby="lab-buttons-h">
      <h2 id="lab-buttons-h" class="header-lab__h2">Кнопки «Войти» и «Регистрация»</h2>
      <p class="header-lab__hint">Одна палитра: slate, border, primary, светлые заливки.</p>

      <div class="header-lab__btn-grid">
        <article v-for="row in buttonRows" :key="row.id" class="header-lab__card header-lab__card--btns">
          <h3 class="header-lab__h3">{{ row.title }}</h3>
          <p class="header-lab__desc">{{ row.desc }}</p>
          <div v-if="row.segmented" class="lab-btns lab-btns--segmented">
            <a href="#" class="lab-b lab-b--login" :class="row.loginClass" @click.prevent>Войти</a>
            <a href="#" class="lab-b lab-b--reg" :class="row.regClass" @click.prevent>Регистрация</a>
          </div>
          <div v-else class="lab-btns">
            <a href="#" class="lab-b lab-b--login" :class="row.loginClass" @click.prevent>Войти</a>
            <a href="#" class="lab-b lab-b--reg" :class="row.regClass" @click.prevent>Регистрация</a>
          </div>
        </article>
      </div>
    </section>
  </div>
  </SiteSeoPage>
</template>

<style scoped>
.header-lab {
  --lab-text: #0f172a;
  --lab-muted: #64748b;
  --lab-border: #e2e8f0;
  --lab-primary: #3b82f6;
  --lab-primary-hi: #2563eb;
  --lab-slate: #0f172a;
  --lab-slate-mid: #1e293b;
  --lab-fill: #f8fafc;
  --lab-fill-2: #f1f5f9;

  max-width: 920px;
  margin: 0 auto;
  padding: 8px 0 80px;
  font-family: var(--font-body, 'Plus Jakarta Sans', system-ui, sans-serif);
  color: var(--lab-text);
}

.header-lab__intro {
  margin-bottom: 40px;
}

.header-lab__badge {
  display: inline-block;
  margin: 0 0 12px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--lab-muted);
  background: var(--lab-fill-2);
  border-radius: 6px;
  border: 1px solid rgba(148, 163, 184, 0.35);
}

.header-lab__title {
  margin: 0 0 12px;
  font-family: var(--font-display, 'Raleway', system-ui, sans-serif);
  font-size: clamp(26px, 4vw, 34px);
  font-weight: 700;
  letter-spacing: -0.02em;
}

.header-lab__lead {
  margin: 0 0 16px;
  font-size: 15px;
  line-height: 1.55;
  color: var(--lab-muted);
}

.header-lab__lead code {
  font-size: 0.9em;
  padding: 1px 6px;
  background: var(--lab-fill-2);
  border-radius: 4px;
}

.header-lab__url {
  margin: 0 0 12px;
  font-size: 13px;
  color: var(--lab-muted);
}

.header-lab__url code {
  font-size: 0.95em;
  padding: 2px 8px;
  background: var(--lab-fill-2);
  border-radius: 4px;
}

.header-lab__back {
  font-size: 14px;
  font-weight: 600;
  color: var(--lab-primary);
  text-decoration: none;
}

.header-lab__back:hover {
  color: var(--lab-primary-hi);
  text-decoration: underline;
}

.header-lab__section {
  margin-bottom: 48px;
}

.header-lab__h2 {
  margin: 0 0 8px;
  font-size: 20px;
  font-weight: 700;
}

.header-lab__hint {
  margin: 0 0 24px;
  font-size: 14px;
  color: var(--lab-muted);
  line-height: 1.45;
}

.header-lab__card {
  margin-bottom: 28px;
  padding: 20px 22px;
  background: #fff;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 14px;
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
}

.header-lab__card--btns {
  margin-bottom: 0;
}

.header-lab__h3 {
  margin: 0 0 6px;
  font-size: 16px;
  font-weight: 700;
}

.header-lab__desc {
  margin: 0 0 16px;
  font-size: 13px;
  color: var(--lab-muted);
  line-height: 1.45;
}

.header-lab__viewport {
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(180deg, #eef2f7 0%, #e2e8f0 100%);
  padding: 16px 14px;
}

.header-lab__viewport--float {
  padding: 20px 18px 24px;
  background: linear-gradient(180deg, #f1f5f9 0%, #e8edf3 100%);
}

/* ——— Mock headers ——— */
.lab-h__inner {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
  min-height: 56px;
  padding: 0 14px;
  box-sizing: border-box;
}

.lab-h__logo {
  font-family: var(--font-display, 'Raleway', system-ui, sans-serif);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--lab-text);
  justify-self: start;
}

.lab-h__logo span {
  color: var(--lab-primary);
}

.lab-h__nav {
  display: flex;
  align-items: center;
  justify-self: center;
  gap: 2px;
  flex-wrap: wrap;
  justify-content: center;
}

.lab-h__nav--chip {
  padding: 4px 6px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.22);
}

.lab-h__nav--chip-soft {
  background: rgba(248, 250, 252, 0.95);
}

.lab-h__pill {
  padding: 7px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--lab-muted);
  border-radius: 8px;
  white-space: nowrap;
}

.lab-h__nav--plain .lab-h__link {
  padding: 8px 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--lab-muted);
  white-space: nowrap;
}

.lab-h__nav--divided {
  gap: 0;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-radius: 10px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.65);
}

.lab-h__seg {
  padding: 8px 14px;
  font-size: 11px;
  font-weight: 600;
  color: var(--lab-muted);
  white-space: nowrap;
  border-right: 1px solid rgba(148, 163, 184, 0.25);
}

.lab-h__seg:last-child {
  border-right: none;
}

.lab-h__cta {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--lab-muted);
}

.lab-h__cta--dummy span:last-child {
  padding: 6px 12px;
  border-radius: 999px;
  background: var(--lab-slate);
  color: #fff;
}

.lab-h__cta--dummy-dark {
  justify-self: end;
  display: flex;
  gap: 8px;
  font-size: 11px;
  font-weight: 600;
  color: rgba(248, 250, 252, 0.75);
}

.lab-h__cta--dummy-dark span:last-child {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #fff;
}

/* Variant shells */
.lab-h--glass-chip {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88) 0%, rgba(248, 250, 252, 0.82) 100%);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 10px;
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset;
}

.lab-h--flat {
  background: #fff;
  border-bottom: 1px solid var(--lab-border);
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
}

.lab-h--accent-line {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-bottom: 3px solid var(--lab-primary);
}

.lab-h--dividers {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 10px;
}

.lab-h--dark {
  background: linear-gradient(180deg, #1e293b 0%, var(--lab-slate) 100%);
  border-radius: 10px;
  border: 1px solid rgba(0, 0, 0, 0.2);
}

.lab-h__logo--on-dark {
  color: #f8fafc;
}

.lab-h__logo--on-dark span {
  color: #93c5fd;
}

.lab-h__nav--on-dark .lab-h__link-dark {
  padding: 8px 10px;
  font-size: 12px;
  font-weight: 600;
  color: rgba(226, 232, 240, 0.85);
  white-space: nowrap;
}

.lab-h--floating {
  margin: 0 4px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 1) inset,
    0 12px 40px rgba(15, 23, 42, 0.1);
}

/* ——— Button pairs ——— */
.header-lab__btn-grid {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.lab-btns {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
}

.lab-b {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  cursor: default;
  border-radius: 999px;
  padding: 10px 20px;
  transition:
    color 0.2s,
    background 0.2s,
    border-color 0.2s,
    box-shadow 0.2s,
    transform 0.15s;
}

/* A */
.lab-b--a-login {
  color: var(--lab-text);
  border: 1px solid var(--lab-border);
  background: rgba(255, 255, 255, 0.55);
  backdrop-filter: blur(8px);
}

.lab-b--a-login:hover {
  background: #fff;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.06);
}

.lab-b--a-reg {
  color: #fff;
  border: none;
  background: linear-gradient(180deg, var(--lab-slate-mid) 0%, var(--lab-slate) 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.12) inset,
    0 6px 18px rgba(15, 23, 42, 0.18);
}

.lab-b--a-reg:hover {
  transform: translateY(-1px);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.14) inset,
    0 10px 26px rgba(15, 23, 42, 0.22);
}

/* B */
.lab-b--b-login {
  color: var(--lab-muted);
  padding: 10px 8px;
  background: transparent;
  border: none;
  border-radius: 8px;
}

.lab-b--b-login:hover {
  color: var(--lab-text);
}

.lab-b--b-reg {
  color: #fff;
  border: none;
  background: linear-gradient(180deg, var(--lab-slate-mid) 0%, var(--lab-slate) 100%);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.15);
}

/* C */
.lab-b--c-login {
  color: var(--lab-text);
  border: 1px solid rgba(15, 23, 42, 0.12);
  background: #fff;
}

.lab-b--c-login:hover {
  border-color: #cbd5e1;
}

.lab-b--c-reg {
  color: var(--lab-primary);
  border: 1px solid rgba(59, 130, 246, 0.45);
  background: rgba(59, 130, 246, 0.06);
}

.lab-b--c-reg:hover {
  background: rgba(59, 130, 246, 0.1);
  border-color: var(--lab-primary);
}

/* D */
.lab-b--d-login {
  color: var(--lab-text);
  border: 1px solid transparent;
  background: var(--lab-fill-2);
}

.lab-b--d-login:hover {
  background: #e2e8f0;
}

.lab-b--d-reg {
  color: #fff;
  border: none;
  background: var(--lab-primary);
  box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35);
}

.lab-b--d-reg:hover {
  background: var(--lab-primary-hi);
}

/* E */
.lab-b--e-login {
  color: var(--lab-primary);
  border: 1px solid rgba(59, 130, 246, 0.4);
  background: transparent;
}

.lab-b--e-login:hover {
  background: rgba(59, 130, 246, 0.06);
}

.lab-b--e-reg {
  color: #fff;
  border: none;
  background: var(--lab-primary);
}

.lab-b--e-reg:hover {
  background: var(--lab-primary-hi);
}

/* F */
.lab-b--f-login {
  color: var(--lab-text);
  border: 1px solid var(--lab-border);
  background: #fff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

.lab-b--f-reg {
  color: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: var(--lab-slate);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
}

/* G */
.lab-b--g-login {
  color: var(--lab-muted);
  border: none;
  background: transparent;
  border-radius: 6px;
  padding: 10px 12px;
  box-shadow: none;
  border-bottom: 2px solid transparent;
}

.lab-b--g-login:hover {
  color: var(--lab-text);
  border-bottom-color: rgba(148, 163, 184, 0.6);
}

.lab-b--g-reg {
  color: #fff;
  border: none;
  background: var(--lab-slate-mid);
  box-shadow: none;
}

.lab-b--g-reg:hover {
  background: var(--lab-slate);
}

/* H — segmented */
.lab-btns--segmented {
  padding: 0;
  gap: 0;
  border-radius: 999px;
  border: 1px solid var(--lab-border);
  background: var(--lab-fill);
  overflow: hidden;
  display: inline-flex;
}

.lab-b--h-login,
.lab-b--h-reg {
  border-radius: 0;
  margin: 0;
  box-shadow: none;
}

.lab-b--h-login {
  color: var(--lab-muted);
  border: none;
  background: transparent;
  padding: 10px 18px;
}

.lab-b--h-login:hover {
  background: rgba(255, 255, 255, 0.9);
  color: var(--lab-text);
}

.lab-b--h-reg {
  color: #fff;
  border: none;
  border-left: 1px solid rgba(15, 23, 42, 0.12);
  background: var(--lab-slate);
  padding: 10px 20px;
}

.lab-b--h-reg:hover {
  background: var(--lab-slate-mid);
}
</style>
