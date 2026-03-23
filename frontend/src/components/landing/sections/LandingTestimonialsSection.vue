<script setup>
defineProps({
  items: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <section class="section section-alt snap-section">
    <div class="container">
      <h2 class="section-heading reveal">Что говорят инвесторы</h2>
      <p class="section-subheading reveal">
        Частные инвесторы, финансовые советники и трейдеры уже используют CapitalView для учёта
        портфелей и принятия решений. Вот что они говорят о продукте.
      </p>
      <div class="testimonials-grid">
        <div v-for="(review, i) in items" :key="i" class="testimonial-card reveal">
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
</template>
