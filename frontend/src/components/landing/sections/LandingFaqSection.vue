<script setup>
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

defineProps({
  items: {
    type: Array,
    required: true
  }
})

const openIndex = ref(null)

function toggle(i) {
  openIndex.value = openIndex.value === i ? null : i
}
</script>

<template>
  <section id="faq" class="section snap-section">
    <div class="container container-narrow">
      <h2 class="section-heading reveal">Частые вопросы</h2>
      <div class="faq-list">
        <div
          v-for="(item, i) in items"
          :key="i"
          class="faq-item"
          :class="{ open: openIndex === i }"
        >
          <button class="faq-question" type="button" :aria-expanded="openIndex === i" @click="toggle(i)">
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
</template>
