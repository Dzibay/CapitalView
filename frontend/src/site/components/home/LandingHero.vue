<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { ArrowRight, Check } from 'lucide-vue-next'
import { gsap } from 'gsap'

const heroCenterRef = ref(null)
const titleWordsLine1 = ['Учёт', 'инвестиций']
const titleWordsLine2 = ['в', 'одном', 'месте']
const leadWords = 'Объединяйте брокерские счета, отслеживайте доходность портфеля и дивиденды — трекер инвестиций с автоимпортом из Т-Инвестиции, без таблиц и ручных пересчётов.'.split(' ')
let introTl = null

onMounted(() => {
  const center = heroCenterRef.value
  if (!center) return

  const prefersReduced =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (prefersReduced) return

  const badge = center.querySelector('.hero-badge')
  const title = center.querySelector('.hero-scene-title')
  const titleWordNodes = center.querySelectorAll('.hero-title-word')
  const leadWordNodes = center.querySelectorAll('.hero-lead-word')
  const lead = center.querySelector('.hero-scene-lead')
  const cta = center.querySelector('.hero-scene-cta')
  if (!badge || !title || !titleWordNodes.length || !leadWordNodes.length || !lead || !cta) return

  introTl = gsap.timeline({ defaults: { ease: 'power3.out' } })
  introTl
    .fromTo(
      badge,
      { autoAlpha: 0, y: 14, filter: 'blur(6px)' },
      { autoAlpha: 1, y: 0, filter: 'blur(0px)', duration: 0.8 }
    )
    .fromTo(
      titleWordNodes,
      { autoAlpha: 0, yPercent: 120, filter: 'blur(8px)' },
      { autoAlpha: 1, yPercent: 0, filter: 'blur(0px)', duration: 0.68, stagger: 0.12 },
      '-=0.28'
    )
    .fromTo(
      leadWordNodes,
      { autoAlpha: 0, yPercent: 120, filter: 'blur(8px)' },
      { autoAlpha: 1, yPercent: 0, filter: 'blur(0px)', duration: 0.62, stagger: 0.03 },
      '-=0.24'
    )
    .fromTo(
      cta,
      { autoAlpha: 0, y: 10, scale: 0.985 },
      { autoAlpha: 1, y: 0, scale: 1, duration: 0.74 },
      '-=0.14'
    )
})

onUnmounted(() => {
  introTl?.kill()
  introTl = null
})
</script>

<template>
  <div class="hero-scene-root">
    <section class="hero-scene" aria-labelledby="hero-scene-title">
      <div class="hero-scene-content container">
        <div ref="heroCenterRef" class="hero-center">
          <div class="hero-badge">
            <Check :size="14" :stroke-width="2.5" />
            Сервис временно бесплатный
          </div>
          <h1 id="hero-scene-title" class="hero-scene-title">
            <span class="hero-line">
              <span v-for="(word, i) in titleWordsLine1" :key="'title-w1-' + i" class="hero-title-word">
                {{ word }}
              </span>
            </span>
            <br />
            <span class="hero-line">
              <span v-for="(word, i) in titleWordsLine2" :key="'title-w2-' + i" class="hero-title-word">
                {{ word }}
              </span>
            </span>
          </h1>
          <p class="hero-scene-lead">
            <span v-for="(word, i) in leadWords" :key="'lead-word-' + i" class="hero-lead-word">
              {{ word }}
            </span>
          </p>
          <div class="hero-scene-cta">
            <router-link to="/login" class="btn-hero-primary">
              Начать бесплатно
              <ArrowRight :size="18" />
            </router-link>
            <a href="#how-it-works" class="btn-hero-ghost">Как это работает</a>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.hero-scene-root {
  position: relative;
  box-sizing: border-box;
}

.hero-scene {
  position: relative;
  z-index: 4;
  display: flex;
  flex-direction: column;
  padding: clamp(130px, 28vh, 280px) 0 0;
  box-sizing: border-box;
}

.hero-scene-content {
  position: relative;
  z-index: 5;
  width: 100%;
  max-width: 1120px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.hero-center {
  text-align: center;
  max-width: 800px;
  margin: 0 auto;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #2563eb;
  background: rgba(59, 130, 246, 0.1);
  border: 1px solid rgba(59, 130, 246, 0.18);
  border-radius: 999px;
  margin-bottom: 18px;
  letter-spacing: 0.02em;
}

.hero-scene-title {
  margin: 0 0 20px;
  font-family: 'Raleway', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  font-size: clamp(36px, 5.5vw + 14px, 62px);
  font-weight: 400;
  letter-spacing: -0.025em;
  line-height: 1.06;
  color: #0b1120;
}

.hero-line {
  display: inline-block;
}

.hero-title-word {
  display: inline-block;
  margin-right: 0.24em;
  will-change: transform, opacity, filter;
}

.hero-lead-word {
  display: inline-block;
  margin-right: 0.28em;
  will-change: transform, opacity, filter;
}

.hero-scene-lead {
  margin: 0 0 28px;
  font-size: clamp(16px, 1.2vw + 14px, 19px);
  line-height: 1.55;
  color: #64748b;
  font-weight: 450;
}

.hero-scene-cta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  justify-content: center;
}

.btn-hero-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px 32px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: #fff;
  font-size: 17px;
  font-weight: 600;
  border-radius: 999px;
  text-decoration: none;
  box-shadow: 0 8px 28px rgba(15, 23, 42, 0.22);
  transition: transform 0.2s, box-shadow 0.2s;
}

.btn-hero-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 36px rgba(15, 23, 42, 0.28);
}

.btn-hero-ghost {
  display: inline-flex;
  align-items: center;
  padding: 16px 28px;
  font-size: 17px;
  font-weight: 600;
  color: #0f172a;
  text-decoration: none;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  transition: border-color 0.2s, background 0.2s;
}

.btn-hero-ghost:hover {
  border-color: #cbd5e1;
  background: #fff;
}

@media (max-width: 767px) {
  .hero-scene {
    padding: clamp(100px, 18vh, 160px) 0 0;
  }

  .hero-scene-title {
    font-size: clamp(30px, 8vw, 44px);
  }

  .hero-scene-lead {
    font-size: clamp(15px, 3.8vw, 17px);
    margin-bottom: 24px;
  }

  .btn-hero-primary,
  .btn-hero-ghost {
    padding: 14px 24px;
    font-size: 15px;
  }
}

@media (max-width: 380px) {
  .hero-scene-cta {
    flex-direction: column;
    width: 100%;
  }

  .btn-hero-primary,
  .btn-hero-ghost {
    width: 100%;
    justify-content: center;
  }
}
</style>
