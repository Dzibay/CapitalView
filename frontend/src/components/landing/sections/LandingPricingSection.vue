<script setup>
import { Check } from 'lucide-vue-next'

defineProps({
  plans: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section id="pricing" class="section snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Сервис временно бесплатный</h2>
      <p class="section-subheading reveal">
        Все функции доступны без ограничений. Начните пользоваться прямо сейчас.
      </p>

      <div class="pricing-grid pricing-grid-single">
        <div
          v-for="plan in plans"
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
</template>
