<script setup>
import { ref, onMounted, onUnmounted, defineAsyncComponent } from 'vue'
import {
  BarChart3,
  RefreshCw,
  Coins,
  FileSpreadsheet,
  Smartphone,
  Calculator,
  Shield,
  Zap,
  Lock,
  ChevronDown,
  ArrowRight,
  Check,
  ImageIcon
} from 'lucide-vue-next'

const SPLINE_SCENE_URL = ''

const Spline3DBackground = defineAsyncComponent(() =>
  import('../components/landing/Spline3DBackground.vue')
)

const openFaq = ref(null)
const observer = ref(null)

const painPoints = [
  {
    icon: FileSpreadsheet,
    title: 'Excel-таблицы с формулами',
    desc: 'Ручные расчёты доходности, копирование данных из брокерских отчётов, ошибки в формулах. Каждая новая сделка — обновление десятков ячеек. Налоговый учёт превращается в головоломку.'
  },
  {
    icon: Smartphone,
    title: 'Несколько приложений брокеров',
    desc: 'Переключение между приложениями Тинькофф, Сбер, ВТБ. Невозможность увидеть общую картину портфеля. Разные форматы отчётов, разные даты — консолидация данных вручную занимает часы.'
  },
  {
    icon: Calculator,
    title: 'Ручной подсчёт дивидендов',
    desc: 'Отслеживание купонов облигаций, дивидендов по акциям, амортизаций и налогов в разных местах. Календарь выплат в голове или в разрозненных заметках. Риск пропустить важную дату.'
  }
]

const features = [
  {
    icon: BarChart3,
    title: 'Аналитика в реальном времени',
    desc: 'Доходность с учётом дивидендов, комиссий и налогов. Графики распределения активов, динамика портфеля, сравнение с бенчмарками. Вся аналитика обновляется автоматически — никаких ручных пересчётов.'
  },
  {
    icon: RefreshCw,
    title: 'Автоматический импорт сделок',
    desc: 'Подключите брокера — все сделки, дивиденды и купоны загрузятся автоматически. Поддержка Т-Инвестиции, скоро Сбер и ВТБ. Забудьте о ручном вводе: одна авторизация, и данные всегда актуальны.'
  },
  {
    icon: Coins,
    title: 'Учёт дивидендов и купонов',
    desc: 'Полный календарь выплат по всем активам. Автоматический расчёт доходности с учётом дивидендов, купонов и амортизаций. Уведомления о предстоящих выплатах. Всё для осознанного управления портфелем.'
  }
]

const steps = [
  {
    number: '01',
    title: 'Подключите брокера',
    desc: 'Авторизуйтесь через Т-Инвестиции. Мы используем только read-only доступ — ваши средства в безопасности.'
  },
  {
    number: '02',
    title: 'Данные загрузятся сами',
    desc: 'Все сделки, дивиденды и купоны синхронизируются за минуту. Никакого ручного ввода.'
  },
  {
    number: '03',
    title: 'Анализируйте и действуйте',
    desc: 'Полная картина портфеля: доходность, распределение, динамика. Решения на основе данных.'
  }
]

const integrationFeatures = [
  { icon: Lock, title: 'Безопасно', desc: 'Read-only доступ. Мы не можем совершать сделки или выводить средства.' },
  { icon: Zap, title: 'Мгновенно', desc: 'Синхронизация за минуту. Все данные обновляются автоматически.' },
  { icon: BarChart3, title: 'Полная картина', desc: 'Сделки, дивиденды, купоны, комиссии — всё в одном месте.' }
]

const comingSoonBrokers = [
  { name: 'Сбер', initials: 'С', color: '#21a038' },
  { name: 'ВТБ', initials: 'В', color: '#002882' },
  { name: 'Альфа', initials: 'А', color: '#ef3124' }
]

// Временно: сервис бесплатный
const pricing = [
  {
    title: 'Сервис временно бесплатный',
    price: '0 ₽',
    period: '',
    features: ['Все функции доступны бесплатно', 'Неограниченные портфели', 'Импорт из Т-Инвестиции', 'Дивидендный календарь', 'Полная аналитика'],
    cta: 'Начать бесплатно',
    popular: true
  }
]

const testimonials = [
  {
    name: 'Алексей М.',
    role: 'Частный инвестор',
    text: 'Наконец-то я вижу реальную доходность портфелей в одном месте. Раньше тратил час в неделю на таблицы — теперь всё автоматически.'
  },
  {
    name: 'Елена С.',
    role: 'Финансовый советник',
    text: 'Использую для ведения клиентских портфелей. Удобно формировать отчёты и отслеживать динамику по каждому клиенту.'
  },
  {
    name: 'Дмитрий К.',
    role: 'Трейдер',
    text: 'Лучшая замена Excel. Автоматический импорт сделок экономит часы каждую неделю. Дивидендный календарь — находка.'
  }
]

const faq = [
  {
    question: 'Безопасно ли подключать брокерский счёт?',
    answer: 'Абсолютно безопасно. Мы используем только read-only доступ через официальный API брокера. Мы не можем совершать сделки, выводить средства или изменять настройки вашего счёта.'
  },
  {
    question: 'Какие брокеры поддерживаются?',
    answer: 'Сейчас доступна интеграция с Т-Инвестиции. В ближайшее время добавим Сбер, ВТБ и Альфа-Банк. Вы также можете вносить данные вручную или добавлять кастомные активы — недвижимость, крипто и другое.'
  },
  {
    question: 'Как часто обновляются данные?',
    answer: 'Данные синхронизируются автоматически при каждом входе в систему. Для подключённых брокеров обновление происходит в реальном времени.'
  },
  {
    question: 'Можно ли использовать бесплатно?',
    answer: 'Да. Сервис временно полностью бесплатный — все функции доступны без ограничений. Неограниченные портфели, импорт из Т-Инвестиции, дивидендный календарь и полная аналитика.'
  },
  {
    question: 'Есть ли мобильное приложение?',
    answer: 'Веб-версия полностью адаптирована для мобильных устройств. Мобильное приложение для iOS и Android находится в разработке.'
  }
]

const toggleFaq = (index) => {
  openFaq.value = openFaq.value === index ? null : index
}

onMounted(() => {
  observer.value = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('is-visible')
        // Оптимизация: прекращаем следить за элементом после появления
        observer.value.unobserve(entry.target)
      }
    })
  }, { threshold: 0.08, rootMargin: '0px 0px -40px 0px' })

  document.querySelectorAll('.reveal').forEach((el) => {
    observer.value.observe(el)
  })
})

onUnmounted(() => {
  if (observer.value) observer.value.disconnect()
})
</script>

<template>
  <div class="landing">

    <div class="hero-bg">
      <Spline3DBackground v-if="SPLINE_SCENE_URL" :scene-url="SPLINE_SCENE_URL" />
      <div class="gradient-mesh" aria-hidden="true">
        <div class="orb orb-1"></div>
        <div class="orb orb-2"></div>
        <div class="orb orb-3"></div>
        <div class="orb orb-4"></div>
        <div class="orb orb-5"></div>
      </div>
    </div>

    <header class="header">
      <div class="container header-inner">
        <router-link to="/" class="logo">Capital<span>View</span></router-link>
        
        <nav class="nav">
          <div class="nav-links">
            <a href="#features">Возможности</a>
            <a href="#how-it-works">Как это работает</a>
            <a href="#pricing">Бесплатно</a>
            <a href="#faq">FAQ</a>
          </div>
        </nav>

        <div class="header-actions">
          <div class="desktop-actions">
            <router-link to="/login" class="btn-ghost">Войти</router-link>
            <router-link to="/login" class="btn-primary-sm">Начать бесплатно</router-link>
          </div>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="container hero-layout">
        <div class="hero-content">
          <div class="hero-badge">
            <Check :size="14" :stroke-width="2.5" />
            Сервис временно бесплатный
          </div>
          <h1 class="hero-title">Ваши инвестиции.<br>Одна картина.</h1>
          <p class="hero-subtitle">
            Объединяйте все брокерские счета в одном месте. Отслеживайте доходность
            с учётом дивидендов и комиссий, анализируйте распределение активов
            и принимайте решения на основе данных — не интуиции.
          </p>
          <div class="hero-actions">
            <router-link to="/login" class="btn-primary">
              Начать бесплатно
              <ArrowRight :size="18" />
            </router-link>
            <a href="#how-it-works" class="btn-secondary">Как это работает</a>
          </div>
        </div>
        <!-- 1200 × 750 px - рекомендуемый размер -->
        <div class="hero-device">
          <div class="laptop-mockup">
            <div class="laptop-screen">
              <img
                src="/screenshots/hero-laptop-dashboard.webp" 
                alt="Дашборд CapitalView на экране ноутбука — учёт и аналитика инвестиционного портфеля"
                class="laptop-image"
                loading="eager"
                fetchpriority="high"
                decoding="async"
                width="1200"
                height="750"
                @error="(e) => { e.target.style.display = 'none'; e.target.nextElementSibling?.classList.add('show') }"
              />
            </div>
            <div class="laptop-base"></div>
          </div>
        </div>
      </div>

      <div class="container">
        <div class="hero-metrics">
          <div class="metric">
            <strong>500+</strong>
            <span>Инвесторов</span>
          </div>
          <div class="metric-divider"></div>
          <div class="metric">
            <strong>97%</strong>
            <span>Точность данных</span>
          </div>
          <div class="metric-divider"></div>
          <div class="metric">
            <Shield :size="20" />
            <span>Данные защищены</span>
          </div>
        </div>
      </div>
    </section>

    <section class="section section-alt">
      <div class="container">
        <h2 class="section-heading reveal">Знакомо?</h2>
        <p class="section-intro reveal">
          Управление инвестициями не должно отнимать часы. Но для многих инвесторов
          реальность выглядит иначе: разрозненные данные, ручные расчёты, риск ошибок.
          Вот три типичные проблемы, с которыми сталкиваются частные инвесторы.
        </p>
        <div class="pain-grid">
          <div
            v-for="(pain, i) in painPoints"
            :key="i"
            class="pain-card reveal"
          >
            <div class="pain-icon">
              <component :is="pain.icon" :size="28" :stroke-width="1.5" />
            </div>
            <h3>{{ pain.title }}</h3>
            <p>{{ pain.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="features" class="section">
      <div class="container">
        <h2 class="section-heading reveal">Всё, что нужно инвестору</h2>
        <p class="section-subheading reveal">
          Три инструмента, которые заменят десяток таблиц и приложений.
          CapitalView объединяет учёт сделок, аналитику доходности и календарь выплат
          в единую платформу с автоматической синхронизацией данных.
        </p>
        <div class="features-grid">
          <div
            v-for="(feat, i) in features"
            :key="i"
            class="feature-card reveal"
          >
            <div class="feature-icon">
              <component :is="feat.icon" :size="28" :stroke-width="1.5" />
            </div>
            <h3>{{ feat.title }}</h3>
            <p>{{ feat.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="how-it-works" class="section">
      <div class="container">
        <h2 class="section-heading reveal">Три шага к полному контролю</h2>
        <p class="section-subheading reveal">
          Никаких сложных настроек. Подключите брокера, дождитесь синхронизации
          и начните анализировать. Вся настройка занимает не более 2 минут.
        </p>
        <div class="steps-grid">
          <div
            v-for="(step, i) in steps"
            :key="i"
            class="step-card reveal"
          >
            <div class="step-number">{{ step.number }}</div>
            <h3>{{ step.title }}</h3>
            <p>{{ step.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="integrations" class="section section-alt">
      <div class="container">
        <h2 class="section-heading reveal">Подключается за 2 минуты</h2>
        <p class="section-subheading reveal">
          Один раз авторизуйтесь через брокера — и все сделки, дивиденды и купоны
          будут синхронизироваться автоматически. Мы используем только read-only доступ:
          выводить средства или совершать сделки через CapitalView невозможно.
        </p>

        <div class="integration-card reveal">
          <div class="integration-header">
            <div class="integration-logo">Т</div>
            <div>
              <h3 class="integration-name">Т-Инвестиции</h3>
              <div class="integration-status">
                <span class="status-dot"></span>
                Активно
              </div>
            </div>
          </div>
          <p class="integration-desc">
            Подключите брокерский счёт и получите полный контроль над инвестициями.
            Все сделки, дивиденды и купоны синхронизируются автоматически.
          </p>
          <div class="integration-features">
            <div
              v-for="(feat, i) in integrationFeatures"
              :key="i"
              class="integration-feature"
            >
              <component :is="feat.icon" :size="20" :stroke-width="1.5" />
              <div>
                <strong>{{ feat.title }}</strong>
                <p>{{ feat.desc }}</p>
              </div>
            </div>
          </div>
          <router-link to="/login" class="btn-primary">
            Подключить Т-Инвестиции
            <ArrowRight :size="18" />
          </router-link>
        </div>

        <div class="coming-soon reveal">
          <p class="coming-soon-label">Скоро</p>
          <div class="coming-soon-list">
            <div
              v-for="broker in comingSoonBrokers"
              :key="broker.name"
              class="coming-soon-item"
            >
              <div class="coming-soon-avatar" :style="{ borderColor: broker.color, color: broker.color }">
                {{ broker.initials }}
              </div>
              <span>{{ broker.name }}</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="pricing" class="section">
      <div class="container">
        <h2 class="section-heading reveal">Сервис временно бесплатный</h2>
        <p class="section-subheading reveal">Все функции доступны без ограничений. Начните пользоваться прямо сейчас.</p>

        <div class="pricing-grid pricing-grid-single">
          <div
            v-for="plan in pricing"
            :key="plan.title"
            class="pricing-card reveal"
            :class="{ popular: plan.popular }"
          >
            <div v-if="plan.popular" class="popular-tag">Бесплатно</div>
            <h3>{{ plan.title }}</h3>
            <div class="price">
              {{ plan.price }}
              <span v-if="plan.period">{{ plan.period }}</span>
            </div>
            <ul>
              <li v-for="feat in plan.features" :key="feat">
                <Check :size="16" :stroke-width="2.5" />
                {{ feat }}
              </li>
            </ul>
            <router-link
              to="/login"
              class="pricing-cta"
              :class="plan.popular ? 'btn-primary' : 'btn-outline'"
            >
              {{ plan.cta }}
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <section class="section section-alt">
      <div class="container">
        <h2 class="section-heading reveal">Что говорят инвесторы</h2>
        <p class="section-subheading reveal">
          Частные инвесторы, финансовые советники и трейдеры уже используют CapitalView
          для учёта портфелей и принятия решений. Вот что они говорят о продукте.
        </p>
        <div class="testimonials-grid">
          <div
            v-for="(review, i) in testimonials"
            :key="i"
            class="testimonial-card reveal"
          >
            <p class="testimonial-text">&laquo;{{ review.text }}&raquo;</p>
            <div class="testimonial-author">
              <div class="author-avatar">{{ review.name.charAt(0) }}</div>
              <div>
                <strong>{{ review.name }}</strong>
                <span>{{ review.role }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="faq" class="section">
      <div class="container container-narrow">
        <h2 class="section-heading reveal">Частые вопросы</h2>
        <div class="faq-list">
          <div v-for="(item, i) in faq" :key="i" class="faq-item" :class="{ open: openFaq === i }">
            <button class="faq-question" @click="toggleFaq(i)" :aria-expanded="openFaq === i">
              <span>{{ item.question }}</span>
              <ChevronDown :size="20" class="faq-chevron" />
            </button>
            <div class="faq-answer-container">
              <div class="faq-answer">
                <p>{{ item.answer }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container footer-inner">
        <div class="footer-brand">
          <router-link to="/" class="logo">Capital<span>View</span></router-link>
          <p>Учёт и аналитика инвестиционного портфеля</p>
        </div>
        <div class="footer-links">
          <div class="footer-col">
            <h4>Продукт</h4>
            <a href="#features">Возможности</a>
            <a href="#pricing">Бесплатно</a>
            <a href="#integrations">Интеграции</a>
          </div>
          <div class="footer-col">
            <h4>Поддержка</h4>
            <a href="#faq">FAQ</a>
            <router-link :to="{ path: '/login', query: { redirect: '/settings#support' } }">Написать нам</router-link>
          </div>
          <div class="footer-col">
            <h4>Правовая информация</h4>
            <a href="/privacy" target="_blank" rel="noopener noreferrer">Политика конфиденциальности</a>
            <a href="/terms" target="_blank" rel="noopener noreferrer">Условия использования</a>
          </div>
        </div>
      </div>
      <div class="container footer-bottom">
        <p>© 2026 CapitalView. Все права защищены.</p>
      </div>
    </footer>

  </div>
</template>

<style scoped>
/* ========================================
   Variables & Base
   ======================================== */
.landing {
  --color-text: #0f172a;
  --color-text-secondary: #64748b;
  --color-bg: #ffffff;
  --color-bg-alt: #f8fafc;
  --color-primary: #3b82f6;
  --color-primary-hover: #2563eb;
  --color-primary-light: rgba(59, 130, 246, 0.08);
  --color-accent-purple: #8b5cf6;
  --color-accent-pink: #ec4899;
  --color-border: #e2e8f0;
  --color-border-light: #f1f5f9;
  --color-success: #10b981;

  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: var(--color-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  overflow-x: hidden;
}

/* ========================================
   3D / Gradient Background
   ======================================== */
.hero-bg {
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
    radial-gradient(ellipse 50% 30% at 0% 50%, rgba(236, 72, 153, 0.08), transparent),
    radial-gradient(ellipse 70% 50% at 100% 100%, rgba(59, 130, 246, 0.1), transparent);
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
  animation-delay: 0s;
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

.orb-4 {
  width: 200px;
  height: 200px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%);
  bottom: -50px;
  left: 30%;
  animation-delay: -15s;
}

.orb-5 {
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%);
  top: 60%;
  left: 10%;
  animation-delay: -7s;
}

@keyframes orbFloat {
  0%, 100% { transform: translate(0, 0) scale(1); }
  25% { transform: translate(30px, -20px) scale(1.05); }
  50% { transform: translate(-20px, 30px) scale(0.95); }
  75% { transform: translate(20px, 20px) scale(1.02); }
}

.container {
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
}

.container-narrow {
  max-width: 800px;
  margin: 0 auto;
  padding: 0 24px;
}

.section {
  padding: 120px 0;
}

.section-alt {
  background: var(--color-bg-alt);
}

.section-heading {
  text-align: center;
  font-size: 48px;
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.1;
  margin-bottom: 16px;
  color: var(--color-text);
}

.section-subheading {
  text-align: center;
  font-size: 18px;
  color: var(--color-text-secondary);
  margin: 0 auto 40px;
  line-height: 1.7;
  max-width: 640px;
}

.section-intro {
  text-align: center;
  font-size: 17px;
  color: var(--color-text-secondary);
  line-height: 1.7;
  max-width: 640px;
  margin: -8px auto 48px;
}

/* ========================================
   Header & Nav
   ======================================== */
.header {
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 64px;
}

.logo {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text);
  text-decoration: none;
  letter-spacing: -0.02em;
  z-index: 102; /* Поверх мобильного меню */
}

.logo span {
  color: var(--color-primary);
}

.nav {
  display: flex;
  gap: 4px;
}

.nav a {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-text-secondary);
  text-decoration: none;
  padding: 8px 16px;
  border-radius: 8px;
  transition: color 0.2s, background 0.2s;
}

.nav a:hover {
  color: var(--color-text);
  background: rgba(0, 0, 0, 0.04);
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.desktop-actions {
  display: flex;
  gap: 8px;
}

.mobile-only-actions {
  display: none;
}

.mobile-menu-btn {
  display: none !important;
  background: none;
  border: none;
  color: var(--color-text);
  cursor: pointer;
  padding: 4px;
  z-index: 102;
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

.btn-primary-sm {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  text-decoration: none;
  padding: 8px 20px;
  border-radius: 20px;
  background: var(--color-primary);
  transition: background 0.2s;
}

.btn-primary-sm:hover {
  background: var(--color-primary-hover);
}

/* --- Мобильная шапка без бургер-меню --- */
@media (max-width: 767px) {
  .nav {
    display: none;
  }

  .desktop-actions .btn-ghost {
    display: none;
  }
}

/* ========================================
   Buttons
   ======================================== */
.btn-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 32px;
  background: var(--color-primary);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border-radius: 14px;
  text-decoration: none;
  border: none;
  cursor: pointer;
  transition: background 0.2s, transform 0.15s;
}

.btn-primary:hover {
  background: var(--color-primary-hover);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 16px 32px;
  background: transparent;
  color: var(--color-text);
  font-size: 17px;
  font-weight: 600;
  border-radius: 14px;
  text-decoration: none;
  border: 1px solid var(--color-border);
  transition: border-color 0.2s, background 0.2s;
}

.btn-secondary:hover {
  border-color: var(--color-text);
  background: rgba(0, 0, 0, 0.02);
}

.btn-outline {
  display: block;
  text-align: center;
  padding: 14px 24px;
  background: transparent;
  color: var(--color-text);
  font-size: 16px;
  font-weight: 600;
  border-radius: 12px;
  text-decoration: none;
  border: 1px solid var(--color-border);
  transition: border-color 0.2s, color 0.2s, background 0.2s;
}

.btn-outline:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
  background: rgba(37, 99, 235, 0.04);
}

/* ========================================
   Hero
   ======================================== */
.hero {
  padding: 120px 0 64px;
  position: relative;
}

.hero-layout {
  display: grid;
  grid-template-columns: 1fr;
  gap: 40px;
  align-items: center;
}

@media (min-width: 992px) {
  .hero-layout {
    grid-template-columns: 1fr 1fr;
    gap: 56px;
  }
}

.hero-content {
  max-width: 520px;
  text-align: left;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-primary);
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.2);
  border-radius: 20px;
  margin-bottom: 20px;
  letter-spacing: 0.02em;
}

.hero-title {
  /* Плавная адаптивность для шрифта H1 */
  font-size: clamp(32px, 5vw + 16px, 55px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.1;
  margin: 0 0 20px;
  color: var(--color-text);
}

.hero-subtitle {
  font-size: 17px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin: 0 0 32px;
}

.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

@media (max-width: 991px) {
  .hero-content {
    text-align: center;
    max-width: 100%;
  }
  .hero-actions {
    justify-content: center;
  }
}

/* Ноутбук с дашбордом (справа) */
.hero-device {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
}

.laptop-mockup {
  width: 100%;
  max-width: 560px;
  margin-left: auto;
  margin-right: auto;
  filter: drop-shadow(0 24px 48px rgba(0, 0, 0, 0.12)) drop-shadow(0 8px 24px rgba(0, 0, 0, 0.08));
}

.laptop-screen {
  position: relative;
  background: var(--color-bg);
  border-radius: 12px 12px 0 0;
  border: 3px solid #1a1a1a;
  border-bottom: none;
  overflow: hidden;
  aspect-ratio: 2 / 1;
}

.laptop-image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
}

.laptop-placeholder {
  display: none;
  position: absolute;
  inset: 0;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 48px 24px;
  background: var(--color-bg-alt);
  color: var(--color-text-secondary);
}

.laptop-placeholder.show {
  display: flex;
}

.laptop-placeholder p {
  font-size: 15px;
  font-weight: 500;
  color: var(--color-text-secondary);
}

.laptop-placeholder span {
  font-size: 12px;
  color: var(--color-border);
  text-align: center;
}

.laptop-placeholder code {
  font-size: 11px;
  background: rgba(0, 0, 0, 0.06);
  padding: 2px 6px;
  border-radius: 4px;
}

.laptop-placeholder .hint {
  font-size: 11px;
  opacity: 0.8;
}

.laptop-base {
  height: 14px;
  background: linear-gradient(180deg, #2a2a2a 0%, #1a1a1a 100%);
  border-radius: 0 0 24px 24px;
  border: 3px solid #1a1a1a;
  border-top: 2px solid #333;
  margin-top: -2px;
  position: relative;
}

.laptop-base::after {
  content: '';
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  width: 80px;
  height: 4px;
  background: #0d0d0d;
  border-radius: 2px;
}

/* Metrics */
.hero-metrics {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
  margin-top: 48px;
  padding-top: 32px;
  border-top: 1px solid var(--color-border-light);
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.metric strong {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.02em;
}

.metric span {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.metric-divider {
  width: 1px;
  height: 32px;
  background: var(--color-border-light);
}

/* ========================================
   Pain Points
   ======================================== */
.pain-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-top: 56px;
}

.pain-card {
  background: var(--color-bg);
  border-radius: 16px;
  padding: 32px;
  border: 1px solid var(--color-border-light);
  transition: transform 0.2s, box-shadow 0.2s;
}

.pain-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}

.pain-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fef2f2;
  border-radius: 14px;
  color: #ef4444;
  margin-bottom: 20px;
}

.pain-card h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 8px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.pain-card p {
  font-size: 16px;
  line-height: 1.6;
  color: var(--color-text-secondary);
}

@media (min-width: 768px) {
  .pain-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================================
   Features
   ======================================== */
.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-top: 56px;
}

.feature-card {
  background: var(--color-bg);
  border-radius: 20px;
  padding: 40px;
  border: 1px solid var(--color-border-light);
  transition: transform 0.2s, box-shadow 0.2s;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}

.feature-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(37, 99, 235, 0.08);
  border-radius: 14px;
  color: var(--color-primary);
  margin-bottom: 24px;
}

.feature-card h3 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 12px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.feature-card p {
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-text-secondary);
}

@media (min-width: 768px) {
  .features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================================
   Steps
   ======================================== */
.steps-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-top: 56px;
}

.step-card {
  text-align: center;
  padding: 48px 32px;
  border-radius: 20px;
  background: var(--color-bg-alt);
  transition: transform 0.2s, box-shadow 0.2s;
}

.step-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}

.step-number {
  display: inline-block;
  font-size: 13px;
  font-weight: 700;
  color: var(--color-primary);
  background: rgba(37, 99, 235, 0.08);
  padding: 6px 14px;
  border-radius: 20px;
  margin-bottom: 24px;
  letter-spacing: 0.05em;
}

.step-card h3 {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 12px;
  letter-spacing: -0.01em;
  color: var(--color-text);
}

.step-card p {
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  max-width: 320px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .steps-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================================
   Integration
   ======================================== */
.integration-card {
  background: var(--color-bg);
  border-radius: 24px;
  padding: 48px;
  border: 1px solid var(--color-border-light);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02);
  margin-top: 56px;
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 24px;
}

.integration-logo {
  width: 56px;
  height: 56px;
  background: #fef08a;
  color: var(--color-text);
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 700;
  flex-shrink: 0;
}

.integration-name {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
  margin-bottom: 4px;
  color: var(--color-text);
}

.integration-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 14px;
  font-weight: 500;
  color: var(--color-success);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-success);
}

.integration-desc {
  font-size: 18px;
  line-height: 1.6;
  color: var(--color-text-secondary);
  margin-bottom: 32px;
  max-width: 640px;
}

.integration-features {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-bottom: 40px;
}

.integration-feature {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  color: var(--color-primary);
}

.integration-feature > svg {
  flex-shrink: 0;
  margin-top: 2px;
}

.integration-feature div {
  flex: 1;
}

.integration-feature strong {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 4px;
}

.integration-feature p {
  font-size: 15px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}

/* Coming Soon */
.coming-soon {
  margin-top: 48px;
  text-align: center;
}

.coming-soon-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 20px;
}

.coming-soon-list {
  display: flex;
  justify-content: center;
  gap: 32px;
}

.coming-soon-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}

.coming-soon-avatar {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  border: 2px dashed var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-secondary);
  transition: border-color 0.2s, color 0.2s;
}

.coming-soon-item:hover .coming-soon-avatar {
  border-style: solid;
}

.coming-soon-item span {
  font-size: 14px;
  color: var(--color-text-secondary);
}

@media (min-width: 768px) {
  .integration-features {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================================
   Pricing
   ======================================== */
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  max-width: 960px;
  margin: 56px auto 0;
}

.pricing-grid-single {
  max-width: 420px;
  margin-left: auto;
  margin-right: auto;
}

.pricing-card {
  background: var(--color-bg);
  border-radius: 20px;
  padding: 40px 32px;
  border: 1px solid var(--color-border-light);
  position: relative;
  display: flex;
  flex-direction: column;
  transition: transform 0.2s, box-shadow 0.2s;
}

.pricing-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.06);
}

.pricing-card.popular {
  border-color: var(--color-primary);
  box-shadow: 0 8px 32px rgba(37, 99, 235, 0.1);
}

.popular-tag {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--color-primary);
  color: #fff;
  padding: 4px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.pricing-card h3 {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--color-text);
}

.price {
  font-size: 44px;
  font-weight: 700;
  margin-bottom: 32px;
  letter-spacing: -0.02em;
  color: var(--color-text);
}

.price span {
  font-size: 16px;
  font-weight: 400;
  color: var(--color-text-secondary);
}

.pricing-card ul {
  list-style: none;
  padding: 0;
  margin: 0 0 32px;
  flex: 1;
}

.pricing-card li {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 15px;
  color: var(--color-text-secondary);
  margin-bottom: 14px;
}

.pricing-card li svg {
  color: var(--color-success);
  flex-shrink: 0;
}

.pricing-cta {
  width: 100%;
}

.pricing-cta.btn-primary {
  display: block;
  text-align: center;
  width: 100%;
}


/* ========================================
   Testimonials
   ======================================== */
.testimonials-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-top: 56px;
}

.testimonial-card {
  background: var(--color-bg);
  border-radius: 20px;
  padding: 32px;
  border: 1px solid var(--color-border-light);
  transition: transform 0.2s;
}

.testimonial-card:hover {
  transform: translateY(-4px);
}

.testimonial-text {
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-text);
  margin-bottom: 24px;
}

.testimonial-author {
  display: flex;
  align-items: center;
  gap: 12px;
}

.author-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 16px;
  flex-shrink: 0;
}

.testimonial-author strong {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text);
}

.testimonial-author span {
  font-size: 13px;
  color: var(--color-text-secondary);
}

@media (min-width: 768px) {
  .testimonials-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* ========================================
   FAQ
   ======================================== */
.faq-list {
  margin-top: 56px;
}

.faq-item {
  border-bottom: 1px solid var(--color-border-light);
}

.faq-item:first-child {
  border-top: 1px solid var(--color-border-light);
}

.faq-question {
  width: 100%;
  background: none;
  border: none;
  padding: 24px 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  text-align: left;
  font-size: 17px;
  font-weight: 600;
  color: var(--color-text);
  font-family: inherit;
  gap: 16px;
  transition: all 0.3s ease;
}

.faq-question:hover {
  color: var(--color-primary);
}

.faq-chevron {
  color: var(--color-text-secondary);
  transition: transform 0.3s;
  flex-shrink: 0;
}

.faq-item.open .faq-chevron {
  transform: rotate(180deg);
}

.faq-answer {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.35s ease-out;
  padding: 0 24px;
}

.faq-item.open .faq-answer {
  max-height: 600px;
  overflow: visible;
}
.faq-item.open .faq-question {
  color: var(--color-primary);
}

.faq-answer p {
  font-size: 16px;
  line-height: 1.7;
  color: var(--color-text-secondary);
  padding: 0 0 24px;
}
.faq-answer {
  min-height: 0; /* Важно для работы grid-анимации */
}
.faq-answer-container {
  display: grid;
  grid-template-rows: 0fr; /* Изначально 0 высоты */
  transition: grid-template-rows 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}
.faq-item.open .faq-answer-container {
  grid-template-rows: 1fr; /* Плавно расширяется до контента */
}

/* ========================================
   Footer
   ======================================== */
.footer {
  padding: 64px 0 32px;
  border-top: 1px solid var(--color-border-light);
}

.footer-inner {
  display: grid;
  grid-template-columns: 1fr;
  gap: 48px;
  margin-bottom: 48px;
}

.footer-brand .logo {
  display: inline-block;
  margin-bottom: 4px;
}

.footer-brand p {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin-top: 8px;
}

.footer-links {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.footer-col h4 {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-text);
  margin-bottom: 16px;
}

.footer-col a {
  display: block;
  font-size: 14px;
  color: var(--color-text-secondary);
  text-decoration: none;
  margin-bottom: 10px;
  transition: color 0.2s;
}

.footer-col a:hover {
  color: var(--color-primary);
}

.footer-bottom {
  padding-top: 24px;
  border-top: 1px solid var(--color-border-light);
}

.footer-bottom p {
  font-size: 13px;
  color: var(--color-text-secondary);
}

@media (min-width: 768px) {
  .footer-inner {
    grid-template-columns: 1fr 2fr;
  }
}

/* ========================================
   Animations
   ======================================== */
.reveal {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}

.reveal.is-visible {
  opacity: 1;
  transform: translateY(0);
}

/* ========================================
   Responsive (Mobile overrides)
   ======================================== */
@media (max-width: 767px) {
  /* Упрощаем тяжёлые эффекты на мобильных ради FCP/LCP */
  .header {
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
    background: rgba(255, 255, 255, 0.96);
  }

  .hero-device {
    display: none;
  }

  .orb {
    display: none;
  }

  .section {
    padding: 64px 0; /* Уменьшили отступы на мобильных */
  }

  .hero {
    padding: 100px 0 48px;
  }

  .hero-subtitle {
    font-size: 16px;
  }

  .laptop-mockup {
    max-width: 100%;
  }

  .section-heading {
    font-size: 32px;
  }

  .section-subheading {
    font-size: 17px;
  }

  .hero-metrics {
    flex-direction: column;
    gap: 24px;
  }

  .metric-divider {
    display: none;
  }

  .integration-card {
    padding: 32px 24px;
  }

  .footer-links {
    grid-template-columns: 1fr;
    gap: 32px;
  }
}

/* Smooth scrolling */
:global(html) {
  scroll-behavior: smooth;
}
</style>