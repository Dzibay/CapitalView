<script setup>
import { ref, onMounted } from 'vue';
import Header from '../components/Header.vue';

// Анимация появления элементов при скролле
const observer = ref(null);

onMounted(() => {
  observer.value = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.animate-on-scroll').forEach((el) => {
    observer.value.observe(el);
  });
});

const pricing = [
  {
    title: 'Начинающий',
    price: '0 ₽',
    features: ['До 3 портфелей', 'Базовая аналитика', 'Ручной ввод сделок', 'Поддержка 24/7'],
    cta: 'Попробовать бесплатно',
    popular: false
  },
  {
    title: 'Инвестор',
    price: '299 ₽',
    period: '/ мес',
    features: ['Неограниченные портфели', 'Импорт из 15+ брокеров', 'Дивидендный календарь', 'Ребалансировка'],
    cta: 'Начать пользоваться',
    popular: true
  },
  {
    title: 'PRO',
    price: '599 ₽',
    period: '/ мес',
    features: ['Все функции Инвестора', 'Налоговые отчеты', 'API доступ', 'Персональный менеджер'],
    cta: 'Выбрать PRO',
    popular: false
  }
];

const features = [
  {
    icon: '📊',
    title: 'Глубокая аналитика',
    desc: 'Следите за доходностью с учетом дивидендов, комиссий и налогов. Стройте красивые графики одним кликом.'
  },
  {
    icon: '🔄',
    title: 'Авто-импорт',
    desc: 'Забудьте о ручном вводе. Мы поддерживаем интеграцию с Тинькофф, Сбер, ВТБ, Interactive Brokers и др.'
  },
  {
    icon: '🛡️',
    title: 'Безопасность',
    desc: 'Ваши данные шифруются по банковским стандартам. Мы не имеем доступа к выводу средств.'
  }
];

const testimonials = [
  { name: 'Алексей М.', role: 'Частный инвестор', text: 'Наконец-то я вижу реальную доходность своих портфелей в одном месте. Интерфейс просто космос!' },
  { name: 'Елена С.', role: 'Финансовый советник', text: 'Использую сервис для ведения клиентов. Очень удобно формировать отчеты и следить за динамикой.' },
  { name: 'Дмитрий К.', role: 'Трейдер', text: 'Лучшая замена Excel. Автоматический импорт сделок экономит мне часы времени каждую неделю.' }
];
</script>

<template>
  <div class="landing-page">
    <header class="landing-header">
      <div class="container header-content">
        <div class="logo">Invest<span class="highlight">Flow</span></div>
        <nav>
          <a href="#features">Возможности</a>
          <a href="#pricing">Тарифы</a>
          <a href="#testimonials">Отзывы</a>
        </nav>
        <div class="auth-buttons">
            <router-link to="/login" class="btn btn-outline">Войти</router-link>
            <router-link to="/login" class="btn btn-primary">Регистрация</router-link>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="container hero-container">
        <div class="hero-text animate-on-scroll">
          <span class="badge">Новое поколение аналитики</span>
          <h1>Ваши инвестиции <br> под полным <span class="gradient-text">контролем</span></h1>
          <p class="subtitle">
            Объедините все брокерские счета в одном месте. Анализируйте доходность, 
            следите за дивидендами и принимайте взвешенные решения.
          </p>
          <div class="hero-buttons">
            <router-link to="/login" class="btn btn-primary btn-lg">Начать бесплатно</router-link>
            <a href="#demo" class="btn btn-outline btn-lg">Как это работает?</a>
          </div>
          <div class="trust-metrics">
            <div class="metric">
              <strong>10k+</strong>
              <span>Пользователей</span>
            </div>
            <div class="metric">
              <strong>₽500M+</strong>
              <span>Активов под наблюдением</span>
            </div>
          </div>
        </div>
        <div class="hero-image animate-on-scroll delay-200" >
           <div class="mockup-window">
             <div class="mockup-header">
               <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
             </div>
             <div class="mockup-content">
               <div class="chart-placeholder">
                  <svg viewBox="0 0 500 200" class="chart-svg">
                    <path d="M0,150 Q100,100 200,120 T400,50 T500,80" fill="none" stroke="#2563eb" stroke-width="4" />
                    <defs>
                      <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:rgba(37,99,235,0.2);stop-opacity:1" />
                        <stop offset="100%" style="stop-color:rgba(37,99,235,0);stop-opacity:1" />
                      </linearGradient>
                    </defs>
                    <path d="M0,150 Q100,100 200,120 T400,50 T500,80 V200 H0 Z" fill="url(#grad1)" />
                  </svg>
                  <div class="floating-card card-1">
                    <span>📈 Портфель</span>
                    <strong>+124,500 ₽</strong>
                  </div>
                   <div class="floating-card card-2">
                    <span>💰 Дивиденды</span>
                    <strong>+12,300 ₽</strong>
                  </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </section>

    <section id="features" class="features section-padding">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Почему выбирают нас?</h2>
        <div class="features-grid">
          <div v-for="(feat, index) in features" :key="index" class="feature-card animate-on-scroll" :class="{'wide': index === 1}">
            <div class="icon-box">{{ feat.icon }}</div>
            <h3>{{ feat.title }}</h3>
            <p>{{ feat.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="pricing" class="pricing section-padding bg-light">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Простые тарифы</h2>
        <p class="section-subtitle animate-on-scroll">Начните бесплатно, переходите на PRO, когда вырастете</p>
        
        <div class="pricing-grid">
          <div 
            v-for="plan in pricing" 
            :key="plan.title" 
            class="pricing-card animate-on-scroll"
            :class="{ 'popular': plan.popular }"
          >
            <div v-if="plan.popular" class="popular-badge">Популярный</div>
            <h3 class="plan-title">{{ plan.title }}</h3>
            <div class="plan-price">
              {{ plan.price }}<span v-if="plan.period" class="period">{{ plan.period }}</span>
            </div>
            <ul class="plan-features">
              <li v-for="feature in plan.features" :key="feature">✓ {{ feature }}</li>
            </ul>
            <router-link to="/login" class="btn btn-block" :class="plan.popular ? 'btn-primary' : 'btn-outline'">
              {{ plan.cta }}
            </router-link>
          </div>
        </div>
      </div>
    </section>

    <section id="testimonials" class="testimonials section-padding">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Что говорят инвесторы</h2>
        <div class="testimonials-grid">
          <div v-for="(review, idx) in testimonials" :key="idx" class="review-card animate-on-scroll">
            <p class="review-text">"{{ review.text }}"</p>
            <div class="review-author">
              <div class="avatar">{{ review.name.charAt(0) }}</div>
              <div>
                <div class="author-name">{{ review.name }}</div>
                <div class="author-role">{{ review.role }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="landing-footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-col">
            <div class="logo">Invest<span class="highlight">Flow</span></div>
            <p class="copyright">© 2024 Все права защищены</p>
          </div>
          <div class="footer-links">
            <a href="#">Политика конфиденциальности</a>
            <a href="#">Условия использования</a>
            <a href="#">Поддержка</a>
          </div>
        </div>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* === Глобальные переменные и сброс === */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

.landing-page {
  font-family: 'Inter', sans-serif;
  color: #1f2937;
  overflow-x: hidden;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --text-dark: #111827;
  --text-gray: #6b7280;
  --bg-light: #f9fafb;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.section-padding {
  padding: 100px 0;
}

.bg-light {
  background-color: var(--bg-light);
}

.gradient-text {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

/* === Кнопки === */
.btn {
  display: inline-block;
  padding: 12px 24px;
  border-radius: 8px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 15px;
}

.btn-lg {
  padding: 16px 32px;
  font-size: 17px;
}

.btn-block {
  display: block;
  width: 100%;
  text-align: center;
}

.btn-primary {
  background: var(--primary);
  color: white;
  border: 2px solid var(--primary);
  box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39);
}
.btn-primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  transform: translateY(-2px);
}

.btn-outline {
  background: transparent;
  color: var(--text-dark);
  border: 2px solid #e5e7eb;
}
.btn-outline:hover {
  border-color: var(--primary);
  color: var(--primary);
}

/* === Header === */
.landing-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(10px);
  z-index: 100;
  border-bottom: 1px solid #f3f4f6;
}

.header-content {
  height: 70px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-dark);
}
.highlight { color: var(--primary); }

.landing-header nav {
  display: none; /* Скрываем на мобильных для простоты */
}
.landing-header nav a {
  margin: 0 20px;
  text-decoration: none;
  color: var(--text-dark);
  font-weight: 500;
  transition: color 0.2s;
}
.landing-header nav a:hover { color: var(--primary); }

.auth-buttons {
    display: flex;
    gap: 10px;
}

@media (min-width: 768px) {
  .landing-header nav { display: block; }
}

/* === Hero Section === */
.hero {
  padding-top: 160px;
  padding-bottom: 100px;
  background: radial-gradient(circle at 50% 50%, rgba(37, 99, 235, 0.05) 0%, rgba(255, 255, 255, 0) 70%);
}

.hero-container {
  display: flex;
  flex-direction: column;
  gap: 50px;
  align-items: center;
  text-align: center;
}

@media (min-width: 992px) {
  .hero-container {
    flex-direction: row;
    text-align: left;
    justify-content: space-between;
  }
}

.hero-text {
  max-width: 600px;
}

.badge {
  display: inline-block;
  background: #eff6ff;
  color: var(--primary);
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
}

.hero h1 {
  font-size: 42px;
  line-height: 1.2;
  font-weight: 800;
  margin-bottom: 24px;
}
@media (min-width: 768px) { .hero h1 { font-size: 56px; } }

.subtitle {
  font-size: 18px;
  color: var(--text-gray);
  margin-bottom: 32px;
  line-height: 1.6;
}

.hero-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: center;
  margin-bottom: 40px;
}
@media (min-width: 992px) { .hero-buttons { justify-content: flex-start; } }

.trust-metrics {
  display: flex;
  gap: 40px;
  justify-content: center;
  padding-top: 20px;
  border-top: 1px solid #f3f4f6;
}
@media (min-width: 992px) { .trust-metrics { justify-content: flex-start; } }

.metric strong {
  display: block;
  font-size: 24px;
  color: var(--text-dark);
}
.metric span {
  font-size: 14px;
  color: var(--text-gray);
}

/* === Mockup (Визуализация) === */
.hero-image {
  width: 500px;
}

.mockup-window {
  background: white;
  border-radius: 12px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.15);
  border: 1px solid #e5e7eb;
  width: 100%;
  max-width: 500px;
  overflow: hidden;
  position: relative;
}

.mockup-header {
  background: #f9fafb;
  padding: 12px;
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #e5e7eb;
}
.dot { width: 10px; height: 10px; border-radius: 50%; background: #ccc; }
.red { background: #ef4444; } .yellow { background: #f59e0b; } .green { background: #10b981; }

.mockup-content {
  padding: 20px;
  height: 300px;
  background: linear-gradient(180deg, #fff 0%, #f3f4f6 100%);
  position: relative;
}

.floating-card {
  position: absolute;
  background: white;
  padding: 12px 20px;
  border-radius: 10px;
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
  animation: float 6s ease-in-out infinite;
}
.floating-card span { display: block; font-size: 12px; color: #6b7280; }
.floating-card strong { display: block; font-size: 16px; color: #111827; }

.card-1 { top: 40px; right: 20px; animation-delay: 0s; }
.card-2 { bottom: 60px; left: 20px; animation-delay: 2s; }

@keyframes float {
  0% { transform: translateY(0px); }
  50% { transform: translateY(-10px); }
  100% { transform: translateY(0px); }
}

/* === Features === */
.section-title {
  text-align: center;
  font-size: 36px;
  font-weight: 700;
  margin-bottom: 60px;
}
.section-subtitle {
    text-align: center;
    font-size: 18px;
    color: var(--text-gray);
    margin-top: -40px;
    margin-bottom: 60px;
}

.features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
}
@media (min-width: 768px) {
  .features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.feature-card {
  background: white;
  padding: 40px;
  border-radius: 16px;
  border: 1px solid #f3f4f6;
  transition: transform 0.3s;
}
.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}

.icon-box {
  font-size: 40px;
  margin-bottom: 20px;
}
.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
}
.feature-card p {
  color: var(--text-gray);
  line-height: 1.5;
}

/* === Pricing === */
.pricing-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  max-width: 1000px;
  margin: 0 auto;
}
@media (min-width: 768px) { .pricing-grid { grid-template-columns: repeat(3, 1fr); } }

.pricing-card {
  background: white;
  padding: 40px 30px;
  border-radius: 16px;
  border: 1px solid #e5e7eb;
  position: relative;
  display: flex;
  flex-direction: column;
}

.pricing-card.popular {
  border-color: var(--primary);
  box-shadow: 0 10px 40px -10px rgba(37, 99, 235, 0.2);
  transform: scale(1.05);
  z-index: 2;
}

.popular-badge {
  position: absolute;
  top: -12px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--primary);
  color: white;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.plan-title { font-size: 18px; font-weight: 600; margin-bottom: 16px; }
.plan-price { font-size: 36px; font-weight: 800; margin-bottom: 24px; color: var(--text-dark); }
.period { font-size: 16px; color: var(--text-gray); font-weight: 400; }

.plan-features {
  list-style: none;
  padding: 0;
  margin-bottom: 30px;
  flex-grow: 1;
}
.plan-features li {
  margin-bottom: 12px;
  font-size: 14px;
  color: var(--text-gray);
}

/* === Testimonials === */
.testimonials-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 30px;
}
@media (min-width: 768px) { .testimonials-grid { grid-template-columns: repeat(3, 1fr); } }

.review-card {
    background: var(--bg-light);
    padding: 30px;
    border-radius: 16px;
}
.review-text {
    font-style: italic;
    color: var(--text-dark);
    margin-bottom: 20px;
    line-height: 1.6;
}
.review-author {
    display: flex;
    align-items: center;
    gap: 12px;
}
.avatar {
    width: 40px;
    height: 40px;
    background: #e5e7eb;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: var(--text-gray);
}
.author-name { font-weight: 600; font-size: 14px; }
.author-role { font-size: 12px; color: var(--text-gray); }

/* === Footer === */
.landing-footer {
  padding: 60px 0;
  background: white;
  border-top: 1px solid #f3f4f6;
}
.footer-content {
    display: flex;
    flex-direction: column;
    gap: 30px;
    align-items: center;
    text-align: center;
}
@media (min-width: 768px) {
    .footer-content {
        flex-direction: row;
        justify-content: space-between;
        text-align: left;
    }
}
.copyright { color: var(--text-gray); font-size: 14px; margin-top: 8px; }
.footer-links a {
    margin: 0 10px;
    color: var(--text-gray);
    text-decoration: none;
    font-size: 14px;
}
.footer-links a:hover { color: var(--primary); }

/* === Animations === */
.animate-on-scroll {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease-out, transform 0.6s ease-out;
}
.animate-on-scroll.visible {
  opacity: 1;
  transform: translateY(0);
}
.delay-200 { transition-delay: 0.2s; }

</style>