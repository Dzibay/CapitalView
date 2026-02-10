<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue';
import Header from '../components/Header.vue';

// Анимация появления элементов при скролле
const observer = ref(null);
const mouseX = ref(0);
const mouseY = ref(0);
const particles = ref([]);
const activeStep = ref(0);
const openFaq = ref(null);
const hoveredService = ref(null);
const activeDemo = ref(null);
const demoStep = ref(0); // 0 = Дашборд, 1 = Активы открыты, 2 = Форма открыта, 3 = Форма заполнена, 4 = Актив добавлен
const selectedPortfolio = ref(null);
const showAddAssetModal = ref(false);
const assetForm = ref({ 
  type: 'real_estate', 
  name: '', 
  value: '', 
  address: '', 
  quantity: 1,
  purchasePrice: '',
  currentPrice: ''
});
const addedAssets = ref([
  { 
    id: 1, 
    name: 'Акция Сбербанк', 
    ticker: 'SBER', 
    value: 125000, 
    profit: 15000, 
    type: 'stock', 
    icon: '📈',
    quantity: 10,
    purchasePrice: 110,
    currentPrice: 125
  },
  { 
    id: 2, 
    name: 'Облигация ОФЗ', 
    ticker: 'ОФЗ-26207', 
    value: 98000, 
    profit: 3200, 
    type: 'bond', 
    icon: '📊',
    quantity: 100,
    purchasePrice: 950,
    currentPrice: 980
  }
]);

const handleAddAsset = () => {
  if (!assetForm.value.name || !assetForm.value.quantity || !assetForm.value.purchasePrice || !assetForm.value.currentPrice) {
    return;
  }
  
  const currentValue = parseFloat(assetForm.value.currentPrice?.replace(/[^\d.]/g, '') || '0') || 0;
  const purchaseValue = parseFloat(assetForm.value.purchasePrice?.replace(/[^\d.]/g, '') || '0') || 0;
  const quantity = parseFloat(assetForm.value.quantity) || 1;
  const totalValue = currentValue * quantity;
  const totalPurchase = purchaseValue * quantity;
  const profit = totalValue - totalPurchase;
  
  // Создаем новый актив
  const newAsset = {
    id: Date.now(),
    name: assetForm.value.name,
    ticker: assetForm.value.type === 'real_estate' ? 'REAL' : assetForm.value.type === 'crypto' ? 'CRYPTO' : 'CUSTOM',
    value: totalValue,
    profit: profit,
    type: assetForm.value.type,
    icon: assetForm.value.type === 'real_estate' ? '🏠' : assetForm.value.type === 'crypto' ? '₿' : '📈',
    quantity: quantity,
    purchasePrice: purchaseValue,
    currentPrice: currentValue
  };
  
  addedAssets.value.push(newAsset);
  
  // Обновляем демо шаг на 4 (актив добавлен)
  if (demoStep.value < 4) {
    demoStep.value = 4;
  }
  
  // Сбрасываем форму
  assetForm.value = { 
    type: 'real_estate', 
    name: '', 
    value: '', 
    address: '', 
    quantity: 1,
    purchasePrice: '',
    currentPrice: ''
  };
  
  // Закрываем модальное окно
  setTimeout(() => {
    showAddAssetModal.value = false;
  }, 300);
};

// Автоматическое обновление шагов при взаимодействии
const updateDemoStep = () => {
  // Шаг 2: форма открыта
  if (showAddAssetModal.value && demoStep.value === 1) {
    demoStep.value = 2;
  }
  
  // Шаг 3: форма заполнена
  const isFormFilled = assetForm.value.name && 
                       assetForm.value.quantity && 
                       assetForm.value.purchasePrice && 
                       assetForm.value.currentPrice;
  
  if (isFormFilled && demoStep.value === 2) {
    demoStep.value = 3;
  }
};

// Отслеживание изменений формы для автоматического обновления шагов
watch([() => showAddAssetModal.value, () => assetForm.value.name, () => assetForm.value.quantity, () => assetForm.value.purchasePrice, () => assetForm.value.currentPrice], () => {
  updateDemoStep();
});

const deleteAsset = (assetId) => {
  addedAssets.value = addedAssets.value.filter(asset => asset.id !== assetId);
};

const formatCurrency = (value) => {
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const handleDemoStepClick = (index) => {
  demoStep = index;
  
  if (index === 0) {
    // Возврат к дашборду
    showAddAssetModal = false;
    assetForm.name = '';
    assetForm.value = '';
    assetForm.address = '';
    assetForm.quantity = 1;
    assetForm.purchasePrice = '';
    assetForm.currentPrice = '';
  } else if (index === 1) {
    // Переход к активам
    showAddAssetModal = false;
  } else if (index === 2) {
    // Открытие формы
    showAddAssetModal = true;
    assetForm.name = 'Квартира в Москве';
    assetForm.quantity = 1;
    assetForm.purchasePrice = '8000000';
    assetForm.currentPrice = '8500000';
  } else if (index >= 3) {
    // Актив добавлен
    showAddAssetModal = false;
  }
};

const handleAssetsTabClick = () => {
  if (demoStep.value < 1) {
    demoStep.value = 1;
  }
};

const demoSteps = [
  { title: 'Откройте раздел активов', desc: 'Нажмите на вкладку "Активы" в боковом меню' },
  { title: 'Нажмите "Добавить актив"', desc: 'Кнопка откроет форму для ввода данных' },
  { title: 'Заполните информацию', desc: 'Укажите тип, название, количество и цены актива' },
  { title: 'Актив добавлен!', desc: 'Новый актив появится в списке активов' }
];

// Обработка движения мыши для параллакса
const handleMouseMove = (e) => {
  mouseX.value = (e.clientX / window.innerWidth) * 100;
  mouseY.value = (e.clientY / window.innerHeight) * 100;
};

// Создание частиц для фона
const createParticles = () => {
  const count = 50;
  particles.value = [];
  for (let i = 0; i < count; i++) {
    particles.value.push({
      x: Math.random() * 100,
      y: Math.random() * 100,
      size: Math.random() * 3 + 1,
      speed: Math.random() * 0.5 + 0.2,
      delay: Math.random() * 2
    });
  }
};

// Данные о функциях сервиса
const serviceFeatures = [
  {
    icon: '📊',
    title: 'Аналитика портфеля',
    desc: 'Детальная аналитика по доходности, рискам и распределению активов. Графики и отчеты в реальном времени.',
    color: '#2563eb'
  },
  {
    icon: '💰',
    title: 'Дивиденды и купоны',
    desc: 'Автоматический учет всех дивидендных выплат и купонных доходов. Календарь предстоящих выплат.',
    color: '#10b981'
  },
  {
    icon: '📈',
    title: 'История сделок',
    desc: 'Полная история всех операций с активами. Фильтрация и поиск по любым параметрам.',
    color: '#f59e0b'
  },
  {
    icon: '🔄',
    title: 'Автосинхронизация',
    desc: 'Автоматическое обновление данных из брокерского счета. Никакого ручного ввода.',
    color: '#8b5cf6'
  },
  {
    icon: '📱',
    title: 'Мультипортфели',
    desc: 'Создавайте неограниченное количество портфелей. Группируйте активы по стратегиям.',
    color: '#ec4899'
  },
  {
    icon: '📋',
    title: 'Отчеты и экспорт',
    desc: 'Формируйте детальные отчеты для налоговой. Экспорт данных в Excel и PDF.',
    color: '#06b6d4'
  }
];

const serviceBenefits = [
  {
    title: 'Экономия времени',
    desc: 'Автоматический импорт сделок избавляет от ручного ввода данных',
    icon: '⏱️'
  },
  {
    title: 'Точность данных',
    desc: 'Прямая синхронизация с брокером гарантирует актуальность информации',
    icon: '🎯'
  },
  {
    title: 'Полный контроль',
    desc: 'Вся информация об инвестициях в одном месте с удобной аналитикой',
    icon: '👁️'
  }
];

// Автоматическая смена шагов "Как это работает"
let stepInterval = null;
let userInteracting = false;

const startStepAnimation = () => {
  stepInterval = setInterval(() => {
    if (!userInteracting) {
      activeStep.value = (activeStep.value + 1) % 4;
    }
  }, 3000);
};

const howItWorks = [
  {
    step: '01',
    title: 'Подключите брокера',
    desc: 'Выберите вашего брокера из списка и авторизуйтесь. Мы используем только read-only доступ.',
    icon: '🔌'
  },
  {
    step: '02',
    title: 'Автоматический импорт',
    desc: 'Все ваши сделки, дивиденды и купоны автоматически синхронизируются в реальном времени.',
    icon: '⚡'
  },
  {
    step: '03',
    title: 'Анализируйте',
    desc: 'Получайте детальную аналитику по доходности, рискам и распределению активов.',
    icon: '📈'
  },
  {
    step: '04',
    title: 'Принимайте решения',
    desc: 'Используйте данные для ребалансировки портфеля и оптимизации инвестиций.',
    icon: '🎯'
  }
];

const integrationFeatures = [
  { icon: '🔐', title: 'Безопасное подключение', desc: 'Используем только read-only доступ. Ваши средства в безопасности' },
  { icon: '⚡', title: 'Мгновенная синхронизация', desc: 'Все сделки и дивиденды обновляются автоматически' },
  { icon: '📊', title: 'Полная аналитика', desc: 'Детальная статистика по всем вашим инвестициям' }
];

const comingSoonBrokers = [
  { name: 'Сбер', logo: '💚', status: 'скоро' },
  { name: 'ВТБ', logo: '🔵', status: 'скоро' },
  { name: 'Альфа-Банк', logo: '🔴', status: 'скоро' }
];

const faq = [
  {
    question: 'Безопасно ли подключать брокерский счет?',
    answer: 'Да, абсолютно безопасно. Мы используем только read-only доступ, что означает, что мы можем только читать данные о ваших сделках. Мы не можем выводить средства, совершать сделки или изменять настройки вашего счета.'
  },
  {
    question: 'Какие брокеры поддерживаются?',
    answer: 'Временно доступен импорт только брокера Т-Инвестиции. Вскоре мы добавим и других российских брокеров! Список постоянно расширяется.'
  },
  {
    question: 'Как часто обновляются данные?',
    answer: 'Данные синхронизируются автоматически в реальном времени при подключении брокера. Для ручного ввода вы можете обновлять информацию в любое время.'
  },
  {
    question: 'Можно ли использовать бесплатно?',
    answer: 'Да, у нас есть бесплатный пробный период 30 дней, чтобы Вы могли протестировать наш сервис и принять решение об использовании.'
  },
  {
    question: 'Поддерживается ли мобильное приложение?',
    answer: 'В настоящее время доступна веб-версия, которая полностью адаптирована для мобильных устройств. Мобильное приложение находится в разработке.'
  }
];

onMounted(() => {
  // Intersection Observer для анимаций
  observer.value = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        // Не отключаем наблюдение, чтобы элементы оставались видимыми
      } else {
        // НЕ удаляем класс visible при выходе из viewport, чтобы элементы не исчезали
        // entry.target.classList.remove('visible');
      }
    });
  }, { 
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px' // Запускаем анимацию немного раньше
  });

  // Наблюдаем за всеми элементами с анимацией
  setTimeout(() => {
    document.querySelectorAll('.animate-on-scroll').forEach((el) => {
      if (observer.value) {
        observer.value.observe(el);
      }
    });
  }, 100);

  // Создаем частицы
  createParticles();

  // Добавляем обработчик движения мыши
  window.addEventListener('mousemove', handleMouseMove);

  // Запускаем анимацию шагов
  startStepAnimation();
  
  // Отслеживаем взаимодействие пользователя с шагами
  setTimeout(() => {
    const stepCards = document.querySelectorAll('.step-card');
    stepCards.forEach(card => {
      card.addEventListener('mouseenter', () => {
        userInteracting = true;
        setTimeout(() => {
          userInteracting = false;
        }, 5000);
      });
    });
  }, 500);
});

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }
  if (stepInterval) {
    clearInterval(stepInterval);
  }
  window.removeEventListener('mousemove', handleMouseMove);
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
    <!-- Анимированный фон с частицами -->
    <div class="animated-background">
      <div 
        v-for="(particle, index) in particles" 
        :key="index"
        class="particle"
        :style="{
          left: particle.x + '%',
          top: particle.y + '%',
          width: particle.size + 'px',
          height: particle.size + 'px',
          animationDelay: particle.delay + 's',
          animationDuration: (10 / particle.speed) + 's'
        }"
      ></div>
      <div class="gradient-orb orb-1" :style="{ transform: `translate(${mouseX * 0.02}px, ${mouseY * 0.02}px)` }"></div>
      <div class="gradient-orb orb-2" :style="{ transform: `translate(${mouseX * -0.03}px, ${mouseY * -0.03}px)` }"></div>
    </div>

    <header class="landing-header">
      <div class="container header-content">
        <div class="logo">Capital<span class="highlight">View</span></div>
        <nav>
          <a href="#features">Возможности</a>
          <a href="#how-it-works">Как это работает</a>
          <a href="#integrations">Интеграции</a>
          <a href="#pricing">Тарифы</a>
          <a href="#testimonials">Отзывы</a>
        </nav>
        <div class="auth-buttons">
            <router-link to="/login" class="btn btn-outline magnetic-btn">Войти</router-link>
            <router-link to="/login" class="btn btn-primary magnetic-btn">Регистрация</router-link>
        </div>
      </div>
    </header>

    <section class="hero">
      <div class="container hero-container">
        <div class="hero-text animate-on-scroll">
          <span class="badge pulse-badge">✨ Новое поколение аналитики</span>
          <h1 class="hero-title">
            <span class="title-line">Ваши инвестиции</span>
            <span class="title-line">под полным <span class="gradient-text typing-text">контролем</span></span>
          </h1>
          <p class="subtitle fade-in-up">
            Объедините все брокерские счета в одном месте. Анализируйте доходность, 
            следите за дивидендами и принимайте взвешенные решения.
          </p>
          <div class="hero-buttons">
            <router-link to="/login" class="btn btn-primary btn-lg magnetic-btn glow-btn">
              <span>Начать бесплатно</span>
              <svg class="btn-arrow" width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </router-link>
            <a href="#how-it-works" class="btn btn-outline btn-lg magnetic-btn">
              Как это работает?
            </a>
          </div>
        </div>
        <div class="hero-image animate-on-scroll delay-200" :style="{ transform: `translate(${mouseX * 0.01}px, ${mouseY * 0.01}px) rotateY(${(mouseX - 50) * 0.1}deg)` }">
           <div class="mockup-window glass-effect">
             <div class="mockup-header">
               <span class="dot red"></span><span class="dot yellow"></span><span class="dot green"></span>
             </div>
             <div class="mockup-content">
               <div class="chart-placeholder">
                  <svg viewBox="0 0 500 200" class="chart-svg">
                    <path d="M0,150 Q100,100 200,120 T400,50 T500,80" fill="none" stroke="#2563eb" stroke-width="4" class="chart-line">
                      <animate attributeName="stroke-dasharray" values="0,1000;1000,0" dur="2s" fill="freeze"/>
                    </path>
                    <defs>
                      <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
                        <stop offset="0%" style="stop-color:rgba(37,99,235,0.3);stop-opacity:1" />
                        <stop offset="100%" style="stop-color:rgba(37,99,235,0);stop-opacity:1" />
                      </linearGradient>
                    </defs>
                    <path d="M0,150 Q100,100 200,120 T400,50 T500,80 V200 H0 Z" fill="url(#grad1)" class="chart-fill">
                      <animate attributeName="opacity" values="0;1" dur="2s" fill="freeze"/>
                    </path>
                  </svg>
                  <div class="floating-card card-1">
                    <div class="card-icon">📈</div>
                    <div class="card-content">
                      <span>Портфель</span>
                      <strong>+124,500 ₽</strong>
                    </div>
                  </div>
                   <div class="floating-card card-2">
                    <div class="card-icon">💰</div>
                    <div class="card-content">
                      <span>Дивиденды</span>
                      <strong>+12,300 ₽</strong>
                    </div>
                  </div>
               </div>
             </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция функций сервиса -->
    <section id="service-features" class="service-features section-padding">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Возможности сервиса</h2>
        <p class="section-subtitle animate-on-scroll">Все инструменты для управления инвестициями в одном месте</p>
        <div class="features-grid-large">
          <div 
            v-for="(feature, index) in serviceFeatures" 
            :key="index"
            class="service-feature-card animate-on-scroll"
            :class="{ 'hovered': hoveredService === index }"
            :style="{ '--feature-color': feature.color, '--delay': index * 0.1 + 's' }"
            @mouseenter="hoveredService = index"
            @mouseleave="hoveredService = null"
          >
            <div class="service-feature-icon-wrapper">
              <div class="service-feature-icon">{{ feature.icon }}</div>
              <div class="feature-glow"></div>
            </div>
            <h3 class="service-feature-title">{{ feature.title }}</h3>
            <p class="service-feature-desc">{{ feature.desc }}</p>
            <div class="feature-hover-line"></div>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция преимуществ -->
    <section class="benefits-section section-padding bg-light">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Почему выбирают CapitalView?</h2>
        <div class="benefits-grid">
          <div 
            v-for="(benefit, index) in serviceBenefits" 
            :key="index"
            class="benefit-card animate-on-scroll"
            :style="{ '--delay': index * 0.15 + 's' }"
          >
            <div class="benefit-icon">{{ benefit.icon }}</div>
            <h3 class="benefit-title">{{ benefit.title }}</h3>
            <p class="benefit-desc">{{ benefit.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция: Кастомные активы -->
    <section id="custom-assets" class="feature-demo-section section-padding">
      <div class="container">
        <div class="demo-section-header animate-on-scroll">
          <div class="demo-header-content">
            <span class="demo-badge">🏠 Кастомные активы</span>
            <h2 class="demo-title">Добавляйте любые активы</h2>
            <p class="demo-subtitle">
              Недвижимость, драгоценности, бизнес — отслеживайте все ваши активы в одном месте. 
              Простое добавление с детальной информацией.
            </p>
          </div>
        </div>
        
        <div class="demo-container">
          <div class="demo-preview animate-on-scroll">
            <div class="dashboard-mockup">
              <div class="mockup-header-bar">
                <div class="mockup-dots">
                  <span class="mockup-dot red"></span>
                  <span class="mockup-dot yellow"></span>
                  <span class="mockup-dot green"></span>
                </div>
                <div class="mockup-title">CapitalView</div>
              </div>
              
              <div class="mockup-content-area">
                <div class="mockup-sidebar">
                  <div 
                    class="sidebar-item"
                    :class="{ 'active': demoStep < 1 }"
                    @click="demoStep = 0"
                  >
                    📊 Дашборд
                  </div>
                  <div class="sidebar-item">💼 Портфели</div>
                  <div 
                    class="sidebar-item"
                    :class="{ 'active': demoStep >= 1 }"
                    @click="handleAssetsTabClick"
                  >
                    📈 Активы
                  </div>
                </div>
                
                <div class="mockup-main">
                  <!-- Дашборд -->
                  <div v-if="demoStep < 1" class="mockup-dashboard">
                    <div class="mockup-toolbar">
                      <h3 class="mockup-page-title">Дашборд</h3>
                    </div>
                    
                    <div class="dashboard-widgets">
                      <div class="widget-chart">
                        <div class="widget-title">График портфеля</div>
                        <div class="chart-container">
                          <svg viewBox="0 0 400 200" class="portfolio-chart">
                            <defs>
                              <linearGradient id="chartGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                <stop offset="0%" style="stop-color:rgba(37,99,235,0.3);stop-opacity:1" />
                                <stop offset="100%" style="stop-color:rgba(37,99,235,0);stop-opacity:1" />
                              </linearGradient>
                            </defs>
                            <path d="M0,150 Q50,140 100,130 T200,100 T300,80 T400,70" 
                                  fill="none" 
                                  stroke="#2563eb" 
                                  stroke-width="3" 
                                  class="chart-line"/>
                            <path d="M0,150 Q50,140 100,130 T200,100 T300,80 T400,70 V200 H0 Z" 
                                  fill="url(#chartGradient)" 
                                  class="chart-fill"/>
                          </svg>
                        </div>
                      </div>
                      
                      <div class="widget-pie">
                        <div class="widget-title">Распределение активов</div>
                        <div class="pie-chart-container">
                          <svg viewBox="0 0 200 200" class="pie-chart">
                            <circle cx="100" cy="100" r="80" fill="none" stroke="#e5e7eb" stroke-width="40"/>
                            <circle cx="100" cy="100" r="80" fill="none" stroke="#2563eb" stroke-width="40" 
                                    stroke-dasharray="251.2 502.4" transform="rotate(-90 100 100)"/>
                            <circle cx="100" cy="100" r="80" fill="none" stroke="#10b981" stroke-width="40" 
                                    stroke-dasharray="125.6 502.4" stroke-dashoffset="-251.2" transform="rotate(-90 100 100)"/>
                            <circle cx="100" cy="100" r="80" fill="none" stroke="#f59e0b" stroke-width="40" 
                                    stroke-dasharray="62.8 502.4" stroke-dashoffset="-376.8" transform="rotate(-90 100 100)"/>
                            <circle cx="100" cy="100" r="80" fill="none" stroke="#8b5cf6" stroke-width="40" 
                                    stroke-dasharray="62.8 502.4" stroke-dashoffset="-439.6" transform="rotate(-90 100 100)"/>
                          </svg>
                          <div class="pie-legend">
                            <div class="legend-item">
                              <span class="legend-color" style="background: #2563eb"></span>
                              <span>Акции 50%</span>
                            </div>
                            <div class="legend-item">
                              <span class="legend-color" style="background: #10b981"></span>
                              <span>Облигации 25%</span>
                            </div>
                            <div class="legend-item">
                              <span class="legend-color" style="background: #f59e0b"></span>
                              <span>Недвижимость 12.5%</span>
                            </div>
                            <div class="legend-item">
                              <span class="legend-color" style="background: #8b5cf6"></span>
                              <span>Другое 12.5%</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <!-- Активы -->
                  <div v-else class="mockup-assets-view">
                    <div class="mockup-toolbar">
                      <h3 class="mockup-page-title">Мои активы</h3>
                      <button 
                        class="mockup-btn-primary"
                        @click="showAddAssetModal = true; if (demoStep < 2) demoStep = 2"
                        :class="{ 'pulse': demoStep >= 2 }"
                      >
                        + Добавить актив
                      </button>
                    </div>
                    
                    <div class="mockup-assets-list">
                    <div class="assets-table-header">
                      <div class="header-cell asset-name-col">Актив</div>
                      <div class="header-cell asset-quantity-col">Кол-во</div>
                      <div class="header-cell asset-price-col">Цена покупки</div>
                      <div class="header-cell asset-price-col">Текущая цена</div>
                      <div class="header-cell asset-value-col">Стоимость</div>
                      <div class="header-cell asset-profit-col">P&L</div>
                    </div>
                    
                    <div 
                      v-for="asset in addedAssets" 
                      :key="asset.id"
                      class="mockup-asset-item"
                      :class="{ 'new-asset slide-in': asset.id > 2 }"
                    >
                      <div class="asset-cell asset-name-cell">
                        <div class="asset-info">
                          <div class="asset-name">{{ asset.name }}</div>
                          <div class="asset-ticker">{{ asset.ticker }}</div>
                        </div>
                      </div>
                      <div class="asset-cell asset-quantity-cell">
                        {{ asset.quantity }}
                      </div>
                      <div class="asset-cell asset-price-cell">
                        {{ formatCurrency(asset.purchasePrice || 0) }}
                      </div>
                      <div class="asset-cell asset-price-cell">
                        {{ formatCurrency(asset.currentPrice || asset.value / (asset.quantity || 1)) }}
                      </div>
                      <div class="asset-cell asset-value-cell">
                        <div class="asset-value">{{ formatCurrency(asset.value) }}</div>
                      </div>
                      <div class="asset-cell asset-profit-cell">
                        <div 
                          class="asset-profit"
                          :class="asset.profit >= 0 ? 'positive' : 'negative'"
                        >
                          {{ asset.profit >= 0 ? '+' : '' }}{{ formatCurrency(asset.profit) }}
                        </div>
                      </div>
                      <button 
                        class="asset-delete-btn"
                        @click="deleteAsset(asset.id)"
                        title="Удалить актив"
                      >
                        ×
                      </button>
                    </div>
                    
                    <div v-if="addedAssets.length === 0" class="empty-assets">
                      <div class="empty-icon">📭</div>
                      <div class="empty-text">Нет активов</div>
                      <div class="empty-desc">Добавьте первый актив, нажав кнопку выше</div>
                    </div>
                  </div>
                  </div>
                  
                  <!-- Модальное окно добавления -->
                  <div 
                    v-if="showAddAssetModal" 
                    class="mockup-modal"
                    :class="{ 'show': showAddAssetModal }"
                  >
                    <div class="modal-content">
                      <div class="modal-header">
                        <h3>Добавить актив</h3>
                        <button class="modal-close" @click="showAddAssetModal = false">×</button>
                      </div>
                      <div class="modal-body">
                        <div class="form-group">
                          <label>Тип актива</label>
                          <select v-model="assetForm.type" class="form-input">
                            <option value="real_estate">🏠 Недвижимость</option>
                            <option value="stock">📈 Акции</option>
                            <option value="crypto">₿ Криптовалюты</option>
                          </select>
                        </div>
                        <div class="form-group">
                          <label>Название</label>
                          <input 
                            v-model="assetForm.name" 
                            type="text" 
                            class="form-input" 
                            placeholder="Квартира в Москве"
                            @input="updateDemoStep"
                          />
                        </div>
                        <div class="form-group">
                          <label>Количество</label>
                          <input 
                            v-model.number="assetForm.quantity" 
                            type="number" 
                            class="form-input" 
                            placeholder="1"
                            min="1"
                            step="0.01"
                            @input="updateDemoStep"
                          />
                        </div>
                        <div class="form-group">
                          <label>Цена покупки (₽ за единицу)</label>
                          <input 
                            v-model="assetForm.purchasePrice" 
                            type="text" 
                            class="form-input" 
                            placeholder="1000"
                            @input="assetForm.purchasePrice = assetForm.purchasePrice.replace(/[^\d.]/g, ''); updateDemoStep()"
                          />
                        </div>
                        <div class="form-group">
                          <label>Текущая цена (₽ за единицу)</label>
                          <input 
                            v-model="assetForm.currentPrice" 
                            type="text" 
                            class="form-input" 
                            placeholder="1200"
                            @input="assetForm.currentPrice = assetForm.currentPrice.replace(/[^\d.]/g, ''); updateDemoStep()"
                          />
                        </div>
                        <div class="form-group" v-if="assetForm.type === 'real_estate'">
                          <label>Адрес (необязательно)</label>
                          <input 
                            v-model="assetForm.address" 
                            type="text" 
                            class="form-input" 
                            placeholder="Москва, ул. Примерная, д. 1"
                          />
                        </div>
                        <button 
                          class="modal-submit"
                          @click="handleAddAsset"
                          :disabled="!assetForm.name || !assetForm.quantity || !assetForm.purchasePrice || !assetForm.currentPrice"
                          :class="{ 'pulse': demoStep >= 3, 'disabled': !assetForm.name || !assetForm.quantity || !assetForm.purchasePrice || !assetForm.currentPrice }"
                        >
                          Добавить актив
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="demo-controls animate-on-scroll">
            <div class="demo-steps">
              <div 
                v-for="(step, index) in demoSteps"
                :key="index"
                class="demo-step-item"
                :class="{ 'active': demoStep === index, 'completed': demoStep > index }"
                @click="handleDemoStepClick(index)"
              >
                <div class="step-indicator">
                  <span v-if="demoStep > index">✓</span>
                  <span v-else>{{ index + 1 }}</span>
                </div>
                <div class="step-content">
                  <div class="step-title">{{ step.title }}</div>
                  <div class="step-desc">{{ step.desc }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция: Иерархия портфелей -->
    <section id="portfolio-hierarchy" class="feature-demo-section section-padding bg-light">
      <div class="container">
        <div class="demo-section-header animate-on-scroll">
          <div class="demo-header-content">
            <span class="demo-badge">📁 Иерархия портфелей</span>
            <h2 class="demo-title">Организуйте инвестиции</h2>
            <p class="demo-subtitle">
              Создавайте родительские и дочерние портфели. Группируйте активы по стратегиям, 
              целям или типам инвестиций. Полная гибкость структурирования.
            </p>
          </div>
        </div>
        
        <div class="hierarchy-demo animate-on-scroll">
          <div class="hierarchy-tree">
            <div 
              class="portfolio-node root"
              :class="{ 'highlight': selectedPortfolio === 'root' }"
              @click="selectedPortfolio = 'root'"
            >
              <div class="node-icon">💼</div>
              <div class="node-content">
                <div class="node-name">Основной портфель</div>
                <div class="node-value">15,250,000 ₽</div>
              </div>
              <div class="node-arrow">▼</div>
            </div>
            
            <div class="children-container">
              <div 
                class="portfolio-node child"
                :class="{ 'highlight': selectedPortfolio === 'conservative' }"
                @click="selectedPortfolio = 'conservative'"
              >
                <div class="node-icon">🛡️</div>
                <div class="node-content">
                  <div class="node-name">Консервативный</div>
                  <div class="node-value">8,500,000 ₽</div>
                </div>
              </div>
              
              <div 
                class="portfolio-node child"
                :class="{ 'highlight': selectedPortfolio === 'aggressive' }"
                @click="selectedPortfolio = 'aggressive'"
              >
                <div class="node-icon">⚡</div>
                <div class="node-content">
                  <div class="node-name">Агрессивный</div>
                  <div class="node-value">4,200,000 ₽</div>
                </div>
              </div>
              
              <div 
                class="portfolio-node child"
                :class="{ 'highlight': selectedPortfolio === 'real_estate' }"
                @click="selectedPortfolio = 'real_estate'"
              >
                <div class="node-icon">🏠</div>
                <div class="node-content">
                  <div class="node-name">Недвижимость</div>
                  <div class="node-value">2,550,000 ₽</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="hierarchy-info">
            <div class="info-card" v-if="selectedPortfolio">
              <h3>Информация о портфеле</h3>
              <div class="info-content">
                <div class="info-item" v-if="selectedPortfolio === 'root'">
                  <span class="info-label">Тип:</span>
                  <span class="info-value">Родительский портфель</span>
                </div>
                <div class="info-item" v-else>
                  <span class="info-label">Тип:</span>
                  <span class="info-value">Дочерний портфель</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Активов:</span>
                  <span class="info-value">{{ selectedPortfolio === 'root' ? '12' : selectedPortfolio === 'conservative' ? '5' : selectedPortfolio === 'aggressive' ? '4' : '3' }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Доходность:</span>
                  <span class="info-value positive">+{{ selectedPortfolio === 'root' ? '18.5' : selectedPortfolio === 'conservative' ? '12.3' : selectedPortfolio === 'aggressive' ? '25.7' : '8.2' }}%</span>
                </div>
              </div>
            </div>
            <div class="info-placeholder" v-else>
              <p>Выберите портфель для просмотра деталей</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция: Дополнительные функции -->
    <section id="advanced-features" class="feature-demo-section section-padding">
      <div class="container">
        <div class="demo-section-header animate-on-scroll">
          <div class="demo-header-content">
            <span class="demo-badge">⚙️ Дополнительно</span>
            <h2 class="demo-title">Еще больше возможностей</h2>
            <p class="demo-subtitle">
              Экспорт данных, настройка уведомлений, API доступ и многое другое
            </p>
          </div>
        </div>
        
        <div class="advanced-features-grid">
          <div class="advanced-feature-card animate-on-scroll">
            <div class="feature-icon-large">📊</div>
            <h3>Экспорт отчетов</h3>
            <p>Выгружайте данные в Excel, PDF или CSV. Идеально для налоговой отчетности.</p>
          </div>
          
          <div class="advanced-feature-card animate-on-scroll">
            <div class="feature-icon-large">🔔</div>
            <h3>Уведомления</h3>
            <p>Получайте уведомления о важных событиях: выплаты дивидендов, изменения цен.</p>
          </div>
          
          <div class="advanced-feature-card animate-on-scroll">
            <div class="feature-icon-large">🔌</div>
            <h3>API доступ</h3>
            <p>Интегрируйте CapitalView с вашими системами через REST API.</p>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция "Как это работает" -->
    <section id="how-it-works" class="how-it-works section-padding">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Как это работает?</h2>
        <p class="section-subtitle animate-on-scroll">Всего 4 простых шага до полного контроля над инвестициями</p>
        <div class="steps-container">
          <div 
            v-for="(step, index) in howItWorks" 
            :key="index"
            class="step-card animate-on-scroll"
            :class="{ 'active': activeStep === index }"
            @mouseenter="activeStep = index"
          >
            <div class="step-number">{{ step.step }}</div>
            <div class="step-icon">{{ step.icon }}</div>
            <h3 class="step-title">{{ step.title }}</h3>
            <p class="step-desc">{{ step.desc }}</p>
            <div class="step-connector" v-if="index < howItWorks.length - 1">
              <div class="connector-line"></div>
              <div class="connector-arrow">→</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Секция интеграций -->
    <section id="integrations" class="integrations section-padding bg-light">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Интеграции с брокерами</h2>
        <p class="section-subtitle animate-on-scroll">Подключайте брокерские счета и получайте полную аналитику</p>
        
        <!-- Главная карточка Т-Инвестиции -->
        <div class="main-integration-card animate-on-scroll">
          <div class="integration-header">
            <div class="integration-logo-wrapper">
              <div class="integration-logo">🏦</div>
              <div class="pulse-ring"></div>
              <div class="pulse-ring delay-1"></div>
            </div>
            <div class="integration-title-group">
              <h3 class="integration-title">Т-Инвестиции</h3>
              <span class="integration-badge active-badge">
                <span class="badge-dot"></span>
                Активно
              </span>
            </div>
          </div>
          
          <p class="integration-description">
            Подключите свой брокерский счет Т-Инвестиции и получите полный контроль над инвестициями. 
            Все сделки, дивиденды и купоны синхронизируются автоматически.
          </p>
          
          <div class="integration-features-grid">
            <div 
              v-for="(feature, index) in integrationFeatures" 
              :key="index"
              class="integration-feature-item"
              :style="{ '--delay': index * 0.1 + 's' }"
            >
              <div class="feature-icon-wrapper">
                <div class="feature-icon">{{ feature.icon }}</div>
              </div>
              <h4 class="feature-title">{{ feature.title }}</h4>
              <p class="feature-desc">{{ feature.desc }}</p>
            </div>
          </div>
          
          <div class="integration-cta">
            <router-link to="/login" class="btn btn-primary btn-lg integration-btn">
              <span class="btn-text">Подключить Т-Инвестиции</span>
              <div class="btn-icon-wrapper">
                <svg class="btn-arrow" width="20" height="20" viewBox="0 0 20 20" fill="none">
                  <path d="M7.5 15L12.5 10L7.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
              </div>
              <div class="btn-shine"></div>
            </router-link>
          </div>
        </div>
        
        <!-- Скоро появятся -->
        <div class="coming-soon-section animate-on-scroll">
          <div class="coming-soon-header">
            <h3 class="coming-soon-title">Скоро появятся</h3>
            <p class="coming-soon-subtitle">Мы активно работаем над добавлением новых брокеров</p>
          </div>
          <div class="coming-soon-brokers">
            <div 
              v-for="(broker, index) in comingSoonBrokers" 
              :key="index"
              class="coming-soon-broker"
              :style="{ '--delay': index * 0.15 + 's' }"
            >
              <div class="coming-soon-logo">{{ broker.logo }}</div>
              <div class="coming-soon-name">{{ broker.name }}</div>
              <div class="coming-soon-badge">Скоро</div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="features" class="features section-padding">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Почему выбирают нас?</h2>
        <div class="features-grid">
          <div 
            v-for="(feat, index) in features" 
            :key="index" 
            class="feature-card animate-on-scroll"
            :style="{ '--delay': index * 0.1 + 's' }"
          >
            <div class="icon-box">{{ feat.icon }}</div>
            <h3>{{ feat.title }}</h3>
            <p>{{ feat.desc }}</p>
            <div class="feature-shine"></div>
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
          <div 
            v-for="(review, idx) in testimonials" 
            :key="idx" 
            class="review-card animate-on-scroll"
            :style="{ '--delay': idx * 0.1 + 's' }"
          >
            <div class="quote-icon">"</div>
            <p class="review-text">{{ review.text }}</p>
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

    <!-- Секция FAQ -->
    <section id="faq" class="faq section-padding bg-light">
      <div class="container">
        <h2 class="section-title animate-on-scroll">Часто задаваемые вопросы</h2>
        <div class="faq-container">
          <div 
            v-for="(item, index) in faq" 
            :key="index"
            class="faq-item animate-on-scroll"
            :class="{ 'open': openFaq === index }"
            @click="openFaq = openFaq === index ? null : index"
          >
            <div class="faq-question">
              <span>{{ item.question }}</span>
              <svg class="faq-icon" width="24" height="24" viewBox="0 0 24 24" fill="none">
                <path d="M6 9L12 15L18 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="faq-answer">
              <p>{{ item.answer }}</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <footer class="landing-footer">
      <div class="container">
        <div class="footer-content">
          <div class="footer-col">
            <div class="logo">Capital<span class="highlight">View</span></div>
            <p class="copyright">© 2026 Все права защищены</p>
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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.landing-page {
  font-family: 'Inter', sans-serif;
  color: #1f2937;
  overflow-x: hidden;
  position: relative;
  --primary: #2563eb;
  --primary-hover: #1d4ed8;
  --text-dark: #111827;
  --text-gray: #6b7280;
  --bg-light: #f9fafb;
}

/* === Анимированный фон === */
.animated-background {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

.particle {
  position: absolute;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: particleFloat 20s infinite ease-in-out;
  opacity: 0.6;
  will-change: transform, opacity;
}

@keyframes particleFloat {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.3;
  }
  25% {
    transform: translate(20px, -30px) scale(1.2);
    opacity: 0.6;
  }
  50% {
    transform: translate(-15px, -50px) scale(0.8);
    opacity: 0.4;
  }
  75% {
    transform: translate(30px, -20px) scale(1.1);
    opacity: 0.5;
  }
}

.gradient-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
  pointer-events: none;
  transition: transform 0.1s ease-out;
  will-change: transform;
}

.orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.4) 0%, transparent 70%);
  top: -200px;
  right: -200px;
}

.orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(124, 58, 237, 0.3) 0%, transparent 70%);
  bottom: -150px;
  left: -150px;
}

.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 20px;
  position: relative;
  z-index: 3;
}

.section-padding {
  padding: 100px 0;
  position: relative;
  z-index: 2;
  background: inherit;
}

.bg-light {
  background-color: var(--bg-light);
  position: relative;
  z-index: 2;
}

.gradient-text {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  position: relative;
  display: inline-block;
}

.typing-text::after {
  content: '|';
  animation: blink 1s infinite;
  color: var(--primary);
}

@keyframes blink {
  0%, 50% { opacity: 1; }
  51%, 100% { opacity: 0; }
}

/* === Кнопки === */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 12px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-size: 15px;
  position: relative;
  overflow: hidden;
  border: 2px solid transparent;
}

.btn-lg {
  padding: 16px 32px;
  font-size: 17px;
}

.btn-block {
  display: block;
  width: 100%;
  text-align: center;
  justify-content: center;
}

.btn-primary {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
  box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.39);
}

.btn-primary::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.btn-primary:hover::before {
  width: 300px;
  height: 300px;
}

.btn-primary:hover {
  background: var(--primary-hover);
  border-color: var(--primary-hover);
  transform: translateY(-2px);
  box-shadow: 0 8px 20px 0 rgba(37, 99, 235, 0.5);
}

.btn-outline {
  background: transparent;
  color: var(--text-dark);
  border-color: #e5e7eb;
}

.btn-outline:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: rgba(37, 99, 235, 0.05);
  transform: translateY(-2px);
}

.magnetic-btn {
  position: relative;
}

.magnetic-btn:hover {
  transform: translateY(-2px) scale(1.02);
}

.glow-btn {
  position: relative;
}

.glow-btn::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 12px;
  padding: 2px;
  background: linear-gradient(45deg, #2563eb, #7c3aed, #2563eb);
  background-size: 200% 200%;
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  animation: glow-border 3s ease infinite;
  transition: opacity 0.3s;
}

.glow-btn:hover::after {
  opacity: 1;
}

@keyframes glow-border {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.btn-arrow {
  transition: transform 0.3s ease;
}

.glow-btn:hover .btn-arrow {
  transform: translateX(4px);
}

.pulse-badge {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 8px rgba(37, 99, 235, 0);
  }
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
  .landing-header nav { 
    display: flex;
    gap: 8px;
  }
  
  .landing-header nav a {
    margin: 0;
    padding: 8px 16px;
    border-radius: 8px;
    transition: background 0.2s;
  }
  
  .landing-header nav a:hover {
    background: rgba(37, 99, 235, 0.05);
  }
}

/* Мобильная адаптация */
@media (max-width: 767px) {
  .hero-title {
    font-size: 32px;
  }
  
  .section-title {
    font-size: 28px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .steps-container {
    gap: 20px;
  }
  
  .brokers-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .hero-image {
    max-width: 100%;
  }
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
  position: relative;
  z-index: 2;
}

.badge {
  display: inline-block;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: var(--primary);
  padding: 8px 16px;
  border-radius: 30px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 20px;
  border: 1px solid rgba(37, 99, 235, 0.2);
}

.hero-title {
  font-size: 42px;
  line-height: 1.2;
  font-weight: 800;
  margin-bottom: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (min-width: 768px) { 
  .hero-title { 
    font-size: 56px; 
  } 
}

.title-line {
  display: block;
  animation: slideInLeft 0.8s ease-out;
}

.title-line:nth-child(2) {
  animation-delay: 0.2s;
  animation-fill-mode: both;
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.subtitle {
  font-size: 18px;
  color: var(--text-gray);
  margin-bottom: 32px;
  line-height: 1.6;
  animation: fadeInUp 0.8s ease-out 0.4s both;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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
  width: 100%;
  max-width: 500px;
  position: relative;
  z-index: 2;
  perspective: 1000px;
  will-change: transform;
}

.mockup-window {
  background: white;
  border-radius: 16px;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25), 0 0 0 1px rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 100%;
  max-width: 500px;
  overflow: hidden;
  position: relative;
  transition: transform 0.3s ease;
  /* Улучшаем четкость всего контента */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
  transform: translateZ(0); /* Аппаратное ускорение */
}

.glass-effect {
  background: white;
  /* Убираем backdrop-filter чтобы текст не был размытым */
}

.mockup-header {
  background: linear-gradient(180deg, #f9fafb 0%, #f3f4f6 100%);
  padding: 12px 16px;
  display: flex;
  gap: 8px;
  border-bottom: 1px solid #e5e7eb;
}

.dot { 
  width: 12px; 
  height: 12px; 
  border-radius: 50%; 
  background: #ccc;
  transition: transform 0.2s;
}

.mockup-window:hover .dot {
  transform: scale(1.1);
}

.red { background: #ef4444; } 
.yellow { background: #f59e0b; } 
.green { background: #10b981; }

.mockup-content {
  padding: 20px;
  height: 300px;
  background: linear-gradient(180deg, #fff 0%, #f9fafb 100%);
  position: relative;
  overflow: hidden;
  /* Улучшаем четкость текста */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.chart-placeholder {
  position: relative;
  width: 100%;
  height: 100%;
}

.chart-svg {
  width: 100%;
  height: 100%;
}

.chart-line {
  filter: drop-shadow(0 2px 4px rgba(37, 99, 235, 0.3));
}

.floating-card {
  position: absolute;
  background: white;
  padding: 16px;
  border-radius: 12px;
  box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 0 0 1px rgba(0, 0, 0, 0.05);
  animation: float 6s ease-in-out infinite;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
  /* Улучшаем четкость текста */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.floating-card:hover {
  transform: translateY(-5px) scale(1.05);
  box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.2);
}

.card-icon {
  font-size: 24px;
  line-height: 1;
}

.card-content {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-content span { 
  font-size: 12px; 
  color: #6b7280; 
  font-weight: 500;
  /* Улучшаем четкость */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.card-content strong { 
  font-size: 18px; 
  color: #111827; 
  font-weight: 700;
  /* Улучшаем четкость */
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.card-1 { 
  top: 40px; 
  right: 20px; 
  animation-delay: 0s; 
}

.card-2 { 
  bottom: 60px; 
  left: 20px; 
  animation-delay: 2s; 
}

@keyframes float {
  0%, 100% { 
    transform: translateY(0px) rotate(0deg); 
  }
  25% {
    transform: translateY(-15px) rotate(1deg);
  }
  50% { 
    transform: translateY(-10px) rotate(-1deg); 
  }
  75% {
    transform: translateY(-12px) rotate(0.5deg);
  }
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
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
  transition-delay: var(--delay, 0s);
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.1), transparent);
  transition: left 0.5s;
}

.feature-card:hover::before {
  left: 100%;
}

.feature-card:hover {
  transform: translateY(-8px) scale(1.02);
  box-shadow: 0 20px 40px rgba(37, 99, 235, 0.15);
  border-color: rgba(37, 99, 235, 0.3);
}

.feature-shine {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.4s;
  pointer-events: none;
}

.feature-card:hover .feature-shine {
  opacity: 1;
  animation: shine 1s ease-out;
}

@keyframes shine {
  0% {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  100% {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

.icon-box {
  font-size: 48px;
  margin-bottom: 20px;
  display: inline-block;
  transition: transform 0.3s;
}

.feature-card:hover .icon-box {
  transform: scale(1.1) rotate(5deg);
}

.feature-card h3 {
  font-size: 20px;
  margin-bottom: 12px;
  font-weight: 700;
}

.feature-card p {
  color: var(--text-gray);
  line-height: 1.6;
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
  border: 2px solid #e5e7eb;
  position: relative;
  display: flex;
  flex-direction: column;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.pricing-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, var(--primary), #7c3aed);
  transform: scaleX(0);
  transition: transform 0.3s;
}

.pricing-card:hover::before {
  transform: scaleX(1);
}

.pricing-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border-color: var(--primary);
}

.pricing-card.popular {
  border-color: var(--primary);
  box-shadow: 0 10px 40px -10px rgba(37, 99, 235, 0.3);
  transform: scale(1.05);
  z-index: 2;
  background: linear-gradient(180deg, white 0%, #f8faff 100%);
}

.pricing-card.popular::before {
  transform: scaleX(1);
}

.pricing-card.popular:hover {
  transform: scale(1.08) translateY(-8px);
  box-shadow: 0 25px 50px rgba(37, 99, 235, 0.4);
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

/* === Service Features Section === */
.service-features {
  position: relative;
  z-index: 2;
  background: white;
}

.features-grid-large {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
}

@media (min-width: 768px) {
  .features-grid-large {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 992px) {
  .features-grid-large {
    grid-template-columns: repeat(3, 1fr);
  }
}

.service-feature-card {
  background: white;
  padding: 32px;
  border-radius: 20px;
  border: 2px solid #f3f4f6;
  position: relative;
  overflow: hidden;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transition-delay: var(--delay, 0s);
  cursor: pointer;
  /* Гарантируем видимость */
  opacity: 1 !important;
  transform: translateY(0) !important;
}

.service-feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: var(--feature-color, var(--primary));
  transform: scaleX(0);
  transform-origin: left;
  transition: transform 0.4s ease;
}

.service-feature-card:hover::before,
.service-feature-card.hovered::before {
  transform: scaleX(1);
}

.service-feature-card:hover,
.service-feature-card.hovered {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(37, 99, 235, 0.15);
  border-color: var(--feature-color, var(--primary));
}

.service-feature-icon-wrapper {
  position: relative;
  margin-bottom: 20px;
  display: inline-block;
}

.service-feature-icon {
  font-size: 56px;
  position: relative;
  z-index: 2;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  display: inline-block;
}

.service-feature-card:hover .service-feature-icon,
.service-feature-card.hovered .service-feature-icon {
  transform: scale(1.15) rotate(5deg);
}

.feature-glow {
  position: absolute;
  inset: -20px;
  background: radial-gradient(circle, var(--feature-color, var(--primary)) 0%, transparent 70%);
  opacity: 0;
  filter: blur(20px);
  transition: opacity 0.4s ease;
  z-index: 1;
}

.service-feature-card:hover .feature-glow,
.service-feature-card.hovered .feature-glow {
  opacity: 0.3;
}

.service-feature-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 12px;
  transition: color 0.3s;
}

.service-feature-card:hover .service-feature-title,
.service-feature-card.hovered .service-feature-title {
  color: var(--feature-color, var(--primary));
}

.service-feature-desc {
  font-size: 15px;
  color: var(--text-gray);
  line-height: 1.6;
}

.feature-hover-line {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--feature-color, var(--primary));
  transition: width 0.4s ease;
}

.service-feature-card:hover .feature-hover-line,
.service-feature-card.hovered .feature-hover-line {
  width: 100%;
}

/* === Benefits Section === */
.benefits-section {
  position: relative;
  z-index: 2;
}

.benefits-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  max-width: 900px;
  margin: 0 auto;
}

@media (min-width: 768px) {
  .benefits-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.benefit-card {
  background: white;
  padding: 40px 30px;
  border-radius: 20px;
  border: 2px solid #f3f4f6;
  text-align: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  transition-delay: var(--delay, 0s);
  position: relative;
  overflow: hidden;
}

.benefit-card::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(37, 99, 235, 0.1) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.4s ease;
}

.benefit-card:hover::before {
  opacity: 1;
}

.benefit-card:hover {
  transform: translateY(-10px) scale(1.02);
  box-shadow: 0 25px 50px rgba(37, 99, 235, 0.15);
  border-color: var(--primary);
}

.benefit-icon {
  font-size: 64px;
  margin-bottom: 20px;
  display: inline-block;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  z-index: 1;
}

.benefit-card:hover .benefit-icon {
  transform: scale(1.2) rotate(10deg);
}

.benefit-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}

.benefit-desc {
  font-size: 15px;
  color: var(--text-gray);
  line-height: 1.6;
  position: relative;
  z-index: 1;
}

/* === Feature Demo Sections === */
.feature-demo-section {
  position: relative;
  z-index: 2;
}

.demo-section-header {
  text-align: center;
  margin-bottom: 60px;
}

.demo-header-content {
  max-width: 700px;
  margin: 0 auto;
}

.demo-badge {
  display: inline-block;
  padding: 8px 16px;
  border-radius: 20px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  color: var(--primary);
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 20px;
}

.demo-title {
  font-size: 36px;
  font-weight: 800;
  color: var(--text-dark);
  margin-bottom: 16px;
}

.demo-subtitle {
  font-size: 18px;
  color: var(--text-gray);
  line-height: 1.6;
}

/* === Custom Assets Demo === */
.demo-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 40px;
  margin-top: 60px;
}

@media (min-width: 992px) {
  .demo-container {
    grid-template-columns: 1.8fr 1fr;
  }
}

.demo-preview {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.dashboard-mockup {
  background: #f9fafb;
  border-radius: 16px;
  overflow: hidden;
}

.mockup-header-bar {
  background: white;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #e5e7eb;
}

.mockup-dots {
  display: flex;
  gap: 6px;
}

.mockup-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.mockup-dot.red { background: #ef4444; }
.mockup-dot.yellow { background: #f59e0b; }
.mockup-dot.green { background: #10b981; }

.mockup-title {
  font-weight: 700;
  color: var(--text-dark);
  font-size: 14px;
}

.mockup-content-area {
  display: flex;
  min-height: 400px;
  position: relative;
  overflow: visible;
}

.mockup-sidebar {
  width: 140px;
  background: white;
  border-right: 1px solid #e5e7eb;
  padding: 12px 0;
}

.sidebar-item {
  padding: 8px 12px;
  color: var(--text-gray);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;
}

.sidebar-item:hover {
  background: #f9fafb;
  color: var(--primary);
}

.sidebar-item.active {
  background: #eff6ff;
  color: var(--primary);
  font-weight: 600;
  border-left: 3px solid var(--primary);
}

.mockup-main {
  flex: 1;
  padding: 24px;
  background: #f9fafb;
  position: relative;
  overflow: visible;
  min-width: 0;
}

.mockup-dashboard {
  width: 100%;
}

.mockup-assets-view {
  width: 100%;
}

.dashboard-widgets {
  display: grid;
  grid-template-columns: 1fr;
  gap: 20px;
  margin-top: 20px;
}

@media (min-width: 768px) {
  .dashboard-widgets {
    grid-template-columns: 1.5fr 1fr;
  }
}

.widget-chart,
.widget-pie {
  background: white;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e5e7eb;
}

.widget-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 16px;
}

.chart-container {
  width: 100%;
  height: 200px;
}

.portfolio-chart {
  width: 100%;
  height: 100%;
}

.chart-line {
  animation: drawLine 2s ease-out;
}

.chart-fill {
  animation: fillArea 2s ease-out;
}

@keyframes drawLine {
  from {
    stroke-dasharray: 1000;
    stroke-dashoffset: 1000;
  }
  to {
    stroke-dasharray: 1000;
    stroke-dashoffset: 0;
  }
}

@keyframes fillArea {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.pie-chart-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.pie-chart {
  width: 180px;
  height: 180px;
}

.pie-legend {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-dark);
}

.legend-color {
  width: 12px;
  height: 12px;
  border-radius: 3px;
  flex-shrink: 0;
}

.mockup-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.mockup-page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark);
}

.mockup-btn-primary {
  padding: 10px 20px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}

.mockup-btn-primary:hover {
  background: var(--primary-hover);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.mockup-btn-primary.pulse {
  animation: button-pulse 2s ease-in-out infinite;
}

@keyframes button-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(37, 99, 235, 0);
  }
}

.mockup-assets-list {
  display: flex;
  flex-direction: column;
  gap: 0;
  background: white;
  border-radius: 12px;
  overflow: hidden;
}

.assets-table-header {
  display: grid;
  grid-template-columns: 2.2fr 0.8fr 1.1fr 1.1fr 1.2fr 1.1fr 32px;
  gap: 8px;
  padding: 8px 12px;
  background: #f9fafb;
  border-bottom: 2px solid #e5e7eb;
  font-size: 10px;
  font-weight: 600;
  color: #6b7280;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.header-cell {
  text-align: right;
  font-size: 10px;
}

.header-cell.asset-name-col {
  text-align: left;
}

.mockup-asset-item {
  background: white;
  padding: 10px 12px;
  border-bottom: 1px solid #e5e7eb;
  display: grid;
  grid-template-columns: 2.2fr 0.8fr 1.1fr 1.1fr 1.2fr 1.1fr 32px;
  gap: 8px;
  align-items: center;
  transition: all 0.3s;
  position: relative;
}

.mockup-asset-item:last-child {
  border-bottom: none;
}

.mockup-asset-item:hover {
  background: #f9fafb;
}

.mockup-asset-item.new-asset {
  background: #f0fdf4;
  border-left: 3px solid #10b981;
}

.asset-name-cell {
  justify-content: flex-start;
  gap: 0;
}

.asset-quantity-cell,
.asset-price-cell {
  font-weight: 500;
  color: var(--text-dark);
  font-family: 'Inter', monospace;
  font-size: 11px;
}

.asset-info {
  flex: 1;
  min-width: 0;
}

.asset-name {
  display: block;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 2px;
  font-size: 12px;
  line-height: 1.3;
}

.asset-ticker {
  font-size: 10px;
  color: #6b7280;
  font-weight: 400;
  line-height: 1.2;
}

.asset-cell {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  font-size: 12px;
  line-height: 1.4;
}

.asset-value {
  font-weight: 600;
  color: var(--text-dark);
  font-size: 12px;
}

.asset-profit {
  font-size: 11px;
  font-weight: 600;
}

.asset-profit.positive {
  color: #10b981;
}

.asset-profit.negative {
  color: #ef4444;
}

.asset-delete-btn {
  background: none;
  border: none;
  font-size: 18px;
  color: #9ca3af;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.2s;
  flex-shrink: 0;
  opacity: 0;
  line-height: 1;
}

.mockup-asset-item:hover .asset-delete-btn {
  opacity: 1;
}

.asset-delete-btn:hover {
  background: #fee2e2;
  color: #ef4444;
}

@media (max-width: 768px) {
  .assets-table-header,
  .mockup-asset-item {
    grid-template-columns: 1fr;
    gap: 8px;
  }
  
  .header-cell {
    display: none;
  }
  
  .asset-cell {
    justify-content: space-between;
    padding: 4px 0;
  }
  
  .asset-cell::before {
    content: attr(data-label);
    font-weight: 600;
    color: #6b7280;
    font-size: 12px;
  }
}

.empty-assets {
  text-align: center;
  padding: 60px 20px;
  color: var(--text-gray);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
  opacity: 0.5;
}

.empty-text {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--text-gray);
}

.new-asset {
  opacity: 0;
  transform: translateX(-20px);
}

.new-asset.slide-in {
  animation: slide-in-asset 0.5s ease-out forwards;
}

@keyframes slide-in-asset {
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.mockup-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
  z-index: 1000;
  padding: 20px;
  overflow-y: auto;
}

.mockup-modal.show {
  opacity: 1;
  pointer-events: all;
}

.modal-content {
  background: white;
  border-radius: 16px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow: visible;
  transform: scale(0.9);
  transition: transform 0.3s;
  display: flex;
  flex-direction: column;
  position: relative;
  margin: auto;
}

.mockup-modal.show .modal-content {
  transform: scale(1);
}

.modal-header {
  padding: 20px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.modal-header h3 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-dark);
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  color: var(--text-gray);
  cursor: pointer;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #f9fafb;
  color: var(--text-dark);
}

.modal-body {
  padding: 20px;
  overflow-y: auto !important;
  overflow-x: hidden;
  flex: 1 1 auto;
  min-height: 200px;
  max-height: calc(90vh - 100px);
  -webkit-overflow-scrolling: touch;
  position: relative;
}

.modal-body::-webkit-scrollbar {
  width: 8px;
}

.modal-body::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 4px;
}

.modal-body::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 14px;
  transition: all 0.2s;
  background: white;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.modal-submit {
  width: 100%;
  padding: 12px;
  background: var(--primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  margin-top: 8px;
}

.modal-submit:hover:not(.disabled) {
  background: var(--primary-hover);
}

.modal-submit.disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.modal-submit.pulse {
  animation: button-pulse 2s ease-in-out infinite;
}

/* === Demo Controls === */
.demo-controls {
  display: flex;
  flex-direction: column;
}

.demo-steps {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.demo-step-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  background: white;
  border-radius: 12px;
  border: 2px solid #e5e7eb;
  cursor: pointer;
  transition: all 0.3s;
}

.demo-step-item:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
}

.demo-step-item.active {
  border-color: var(--primary);
  background: #eff6ff;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.15);
}

.demo-step-item.completed {
  border-color: #10b981;
  background: #f0fdf4;
}

.step-indicator {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: var(--text-gray);
  flex-shrink: 0;
  transition: all 0.3s;
}

.demo-step-item.active .step-indicator {
  background: var(--primary);
  color: white;
}

.demo-step-item.completed .step-indicator {
  background: #10b981;
  color: white;
}

.step-content {
  flex: 1;
}

.step-title {
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 4px;
  font-size: 16px;
}

.step-desc {
  font-size: 14px;
  color: var(--text-gray);
  line-height: 1.5;
}

/* === Portfolio Hierarchy Demo === */
.hierarchy-demo {
  display: grid;
  grid-template-columns: 1fr;
  gap: 40px;
  margin-top: 40px;
}

@media (min-width: 992px) {
  .hierarchy-demo {
    grid-template-columns: 1.5fr 1fr;
  }
}

.hierarchy-tree {
  background: white;
  padding: 32px;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.portfolio-node {
  background: white;
  padding: 20px;
  border-radius: 12px;
  border: 2px solid #e5e7eb;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s;
  margin-bottom: 12px;
  position: relative;
}

.portfolio-node:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
  transform: translateX(4px);
}

.portfolio-node.highlight {
  border-color: var(--primary);
  background: #eff6ff;
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.15);
}

.portfolio-node.root {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: var(--primary);
}

.portfolio-node.child {
  margin-left: 40px;
  position: relative;
}

.portfolio-node.child::before {
  content: '';
  position: absolute;
  left: -30px;
  top: 50%;
  width: 20px;
  height: 2px;
  background: #e5e7eb;
}

.node-icon {
  font-size: 32px;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
  border-radius: 12px;
}

.node-content {
  flex: 1;
}

.node-name {
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 4px;
  font-size: 16px;
}

.node-value {
  font-size: 14px;
  color: var(--text-gray);
}

.node-arrow {
  color: var(--primary);
  font-size: 20px;
}

.children-container {
  margin-top: 12px;
}

.hierarchy-info {
  background: white;
  padding: 32px;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  height: fit-content;
}

.info-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 20px;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
}

.info-label {
  font-size: 14px;
  color: var(--text-gray);
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  font-weight: 700;
  color: var(--text-dark);
}

.info-value.positive {
  color: #10b981;
}

.info-placeholder {
  text-align: center;
  padding: 40px;
  color: var(--text-gray);
}

/* === Advanced Features === */
.advanced-features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-top: 40px;
}

@media (min-width: 768px) {
  .advanced-features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.advanced-feature-card {
  background: white;
  padding: 32px;
  border-radius: 16px;
  border: 2px solid #f3f4f6;
  text-align: center;
  transition: all 0.3s;
}

.advanced-feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.1);
  border-color: var(--primary);
}

.feature-icon-large {
  font-size: 64px;
  margin-bottom: 20px;
  display: inline-block;
  transition: transform 0.3s;
}

.advanced-feature-card:hover .feature-icon-large {
  transform: scale(1.1) rotate(5deg);
}

.advanced-feature-card h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 12px;
}

.advanced-feature-card p {
  font-size: 15px;
  color: var(--text-gray);
  line-height: 1.6;
}

/* === How It Works Section === */
.how-it-works {
  position: relative;
  z-index: 2;
  background: white;
}

.steps-container {
  display: grid;
  grid-template-columns: 1fr;
  gap: 30px;
  position: relative;
}

@media (min-width: 992px) {
  .steps-container {
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
  }
}

.step-card {
  background: white;
  padding: 30px;
  border-radius: 16px;
  border: 2px solid #f3f4f6;
  position: relative;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  cursor: pointer;
  z-index: 1;
  /* Гарантируем видимость */
  opacity: 1 !important;
  transform: translateY(0) !important;
}

.step-card::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  padding: 2px;
  background: linear-gradient(135deg, var(--primary), #7c3aed);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0;
  transition: opacity 0.3s;
}

.step-card.active::before,
.step-card:hover::before {
  opacity: 1;
}

.step-card.active,
.step-card:hover {
  transform: translateY(-8px) scale(1.02) !important;
  box-shadow: 0 20px 40px rgba(37, 99, 235, 0.2);
  border-color: transparent;
  /* Гарантируем видимость при активном состоянии */
  opacity: 1 !important;
  z-index: 2;
}

.step-number {
  font-size: 14px;
  font-weight: 700;
  color: var(--primary);
  margin-bottom: 12px;
  opacity: 0.6;
}

.step-card.active .step-number,
.step-card:hover .step-number {
  opacity: 1;
  transform: scale(1.1);
}

.step-icon {
  font-size: 48px;
  margin-bottom: 16px;
  display: inline-block;
  transition: transform 0.3s;
}

.step-card.active .step-icon,
.step-card:hover .step-icon {
  transform: scale(1.2) rotate(5deg);
}

.step-title {
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
  color: var(--text-dark);
}

.step-desc {
  font-size: 14px;
  color: var(--text-gray);
  line-height: 1.6;
}

.step-connector {
  display: none;
}

@media (min-width: 992px) {
  .step-connector {
    display: block;
    position: absolute;
    right: -10px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 1;
  }

  .connector-line {
    width: 40px;
    height: 2px;
    background: linear-gradient(90deg, var(--primary), transparent);
    position: relative;
  }

  .connector-arrow {
    position: absolute;
    right: -10px;
    top: 50%;
    transform: translateY(-50%);
    font-size: 20px;
    color: var(--primary);
    animation: arrowPulse 2s ease-in-out infinite;
  }
}

@keyframes arrowPulse {
  0%, 100% {
    transform: translateY(-50%) translateX(0);
    opacity: 0.5;
  }
  50% {
    transform: translateY(-50%) translateX(5px);
    opacity: 1;
  }
}

/* === Integrations Section === */
.integrations {
  position: relative;
  z-index: 2;
}

/* Главная карточка интеграции */
.main-integration-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8faff 100%);
  border-radius: 24px;
  padding: 50px 40px;
  border: 2px solid #e5e7eb;
  box-shadow: 0 20px 60px rgba(37, 99, 235, 0.1);
  position: relative;
  overflow: hidden;
  margin-bottom: 60px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.main-integration-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 4px;
  background: linear-gradient(90deg, #2563eb, #7c3aed, #2563eb);
  background-size: 200% 100%;
  animation: gradient-shift 3s ease infinite;
}

@keyframes gradient-shift {
  0%, 100% { background-position: 0% 50%; }
  50% { background-position: 100% 50%; }
}

.main-integration-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 25px 70px rgba(37, 99, 235, 0.15);
  border-color: var(--primary);
}

.integration-header {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-bottom: 24px;
}

.integration-logo-wrapper {
  position: relative;
  width: 80px;
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.integration-logo {
  font-size: 48px;
  position: relative;
  z-index: 2;
  animation: logo-float 3s ease-in-out infinite;
}

@keyframes logo-float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-10px) scale(1.05); }
}

.pulse-ring {
  position: absolute;
  inset: -10px;
  border: 2px solid var(--primary);
  border-radius: 50%;
  opacity: 0.3;
  animation: pulse-ring 2s ease-out infinite;
}

.pulse-ring.delay-1 {
  animation-delay: 1s;
  inset: -20px;
  opacity: 0.2;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  100% {
    transform: scale(1.2);
    opacity: 0;
  }
}

.integration-title-group {
  flex: 1;
}

.integration-title {
  font-size: 32px;
  font-weight: 800;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.integration-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 14px;
  font-weight: 600;
  background: #dcfce7;
  color: #166534;
}

.active-badge {
  background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
}

.badge-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #22c55e;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(34, 197, 94, 0);
  }
}

.integration-description {
  font-size: 18px;
  color: var(--text-gray);
  line-height: 1.6;
  margin-bottom: 40px;
  max-width: 700px;
}

.integration-features-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-bottom: 40px;
}

@media (min-width: 768px) {
  .integration-features-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.integration-feature-item {
  background: white;
  padding: 24px;
  border-radius: 16px;
  border: 1px solid #f3f4f6;
  transition: all 0.3s ease;
  transition-delay: var(--delay, 0s);
  position: relative;
  overflow: hidden;
}

.integration-feature-item::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.05), transparent);
  transition: left 0.5s;
}

.integration-feature-item:hover::before {
  left: 100%;
}

.integration-feature-item:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.1);
  border-color: var(--primary);
}

.feature-icon-wrapper {
  margin-bottom: 16px;
}

.feature-icon {
  font-size: 40px;
  display: inline-block;
  transition: transform 0.3s;
}

.integration-feature-item:hover .feature-icon {
  transform: scale(1.2) rotate(5deg);
}

.feature-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.feature-desc {
  font-size: 14px;
  color: var(--text-gray);
  line-height: 1.5;
}

.integration-cta {
  text-align: center;
}

.integration-btn {
  position: relative;
  overflow: hidden;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  padding: 18px 36px;
  border-radius: 14px;
  font-weight: 700;
  font-size: 18px;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: linear-gradient(135deg, var(--primary) 0%, #1d4ed8 100%);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.4);
  border: none;
}

.integration-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, #1d4ed8 0%, var(--primary) 100%);
  opacity: 0;
  transition: opacity 0.4s ease;
  border-radius: 14px;
}

.integration-btn:hover::before {
  opacity: 1;
}

.integration-btn:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.5);
}

.integration-btn:active {
  transform: translateY(-1px) scale(1.02);
}

.btn-text {
  position: relative;
  z-index: 2;
  transition: transform 0.3s ease;
}

.integration-btn:hover .btn-text {
  transform: translateX(-4px);
}

.btn-icon-wrapper {
  position: relative;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.integration-btn:hover .btn-icon-wrapper {
  transform: translateX(6px) scale(1.1);
}

.btn-arrow {
  transition: transform 0.3s ease;
}

.integration-btn:hover .btn-arrow {
  transform: translateX(2px);
}

.btn-shine {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: linear-gradient(
    45deg,
    transparent 30%,
    rgba(255, 255, 255, 0.3) 50%,
    transparent 70%
  );
  transform: translateX(-100%) translateY(-100%) rotate(45deg);
  transition: transform 0.6s ease;
  z-index: 1;
}

.integration-btn:hover .btn-shine {
  transform: translateX(100%) translateY(100%) rotate(45deg);
}

/* Секция "Скоро появятся" */
.coming-soon-section {
  background: white;
  border-radius: 20px;
  padding: 40px;
  border: 1px solid #e5e7eb;
}

.coming-soon-header {
  text-align: center;
  margin-bottom: 32px;
}

.coming-soon-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.coming-soon-subtitle {
  font-size: 16px;
  color: var(--text-gray);
}

.coming-soon-brokers {
  display: flex;
  justify-content: center;
  gap: 24px;
  flex-wrap: wrap;
}

.coming-soon-broker {
  background: linear-gradient(135deg, #f9fafb 0%, #f3f4f6 100%);
  padding: 24px 32px;
  border-radius: 16px;
  border: 2px dashed #d1d5db;
  text-align: center;
  position: relative;
  transition: all 0.3s ease;
  transition-delay: var(--delay, 0s);
  min-width: 120px;
}

.coming-soon-broker::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--primary), #7c3aed);
  opacity: 0;
  transition: opacity 0.3s;
  z-index: -1;
}

.coming-soon-broker:hover::before {
  opacity: 0.1;
}

.coming-soon-broker:hover {
  transform: translateY(-5px) scale(1.05);
  border-color: var(--primary);
  box-shadow: 0 10px 25px rgba(37, 99, 235, 0.15);
}

.coming-soon-logo {
  font-size: 40px;
  margin-bottom: 12px;
  filter: grayscale(0.5);
  transition: filter 0.3s;
}

.coming-soon-broker:hover .coming-soon-logo {
  filter: grayscale(0);
  animation: logo-bounce 0.6s ease;
}

@keyframes logo-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.coming-soon-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-dark);
  margin-bottom: 8px;
}

.coming-soon-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
  animation: badge-pulse 2s ease-in-out infinite;
}

@keyframes badge-pulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 0 0 0 rgba(251, 191, 36, 0.4);
  }
  50% {
    transform: scale(1.05);
    box-shadow: 0 0 0 4px rgba(251, 191, 36, 0);
  }
}

/* === Testimonials === */
.testimonials-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 30px;
}
@media (min-width: 768px) { .testimonials-grid { grid-template-columns: repeat(3, 1fr); } }

.review-card {
    background: white;
    padding: 30px;
    border-radius: 16px;
    border: 1px solid #f3f4f6;
    position: relative;
    transition: all 0.4s ease;
    transition-delay: var(--delay, 0s);
}

.review-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
  border-color: var(--primary);
}

.quote-icon {
  position: absolute;
  top: 20px;
  left: 20px;
  font-size: 60px;
  color: var(--primary);
  opacity: 0.2;
  font-family: Georgia, serif;
  line-height: 1;
}

.review-text {
    font-style: italic;
    color: var(--text-dark);
    margin-bottom: 20px;
    line-height: 1.6;
    position: relative;
    z-index: 1;
    padding-top: 20px;
}
.review-author {
    display: flex;
    align-items: center;
    gap: 12px;
}
.avatar {
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, var(--primary), #7c3aed);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    color: white;
    font-size: 18px;
}
.author-name { font-weight: 600; font-size: 14px; }
.author-role { font-size: 12px; color: var(--text-gray); }

/* === FAQ Section === */
.faq {
  position: relative;
  z-index: 2;
}

.faq-container {
  max-width: 800px;
  margin: 0 auto;
}

.faq-item {
  background: white;
  border-radius: 16px;
  border: 1px solid #f3f4f6;
  margin-bottom: 16px;
  overflow: hidden;
  transition: all 0.3s ease;
  cursor: pointer;
  position: relative;
  z-index: 1;
  /* Гарантируем видимость */
  opacity: 1 !important;
  transform: translateY(0) !important;
}

.faq-item:hover {
  border-color: var(--primary);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
}

.faq-item.open {
  border-color: var(--primary);
  box-shadow: 0 8px 24px rgba(37, 99, 235, 0.15);
  /* Гарантируем видимость при открытом состоянии */
  opacity: 1 !important;
  z-index: 2;
}

.faq-question {
  padding: 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  color: var(--text-dark);
  font-size: 16px;
}

.faq-icon {
  transition: transform 0.3s ease;
  color: var(--primary);
  flex-shrink: 0;
  margin-left: 16px;
}

.faq-item.open .faq-icon {
  transform: rotate(180deg);
}

.faq-answer {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.3s ease, padding 0.3s ease;
  padding: 0 24px;
  /* Гарантируем видимость при открытии */
  visibility: hidden;
}

.faq-item.open .faq-answer {
  max-height: 500px;
  padding: 0 24px 24px;
  visibility: visible;
}

.faq-answer p {
  color: var(--text-gray);
  line-height: 1.6;
  font-size: 15px;
}

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
  transform: translateY(30px);
  transition: opacity 0.8s cubic-bezier(0.4, 0, 0.2, 1), 
              transform 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  /* Гарантируем, что после появления элемент остается видимым */
  will-change: opacity, transform;
}

.animate-on-scroll.visible {
  opacity: 1 !important;
  transform: translateY(0) !important;
}

/* Исключаем step-card и faq-item из общей анимации, так как они должны быть всегда видимы */
.step-card.animate-on-scroll,
.faq-item.animate-on-scroll {
  opacity: 1 !important;
  transform: translateY(0) !important;
}

/* Гарантируем видимость контента внутри */
.step-card *,
.faq-item * {
  opacity: 1 !important;
  visibility: visible !important;
}

.delay-200 { transition-delay: 0.2s; }

/* Плавная прокрутка */
html {
  scroll-behavior: smooth;
}

/* Улучшенные hover эффекты для навигации */
.landing-header nav a {
  position: relative;
}

.landing-header nav a::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 0;
  width: 0;
  height: 2px;
  background: var(--primary);
  transition: width 0.3s ease;
}

.landing-header nav a:hover::after {
  width: 100%;
}

</style>