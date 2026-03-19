<template>
  <BaseErrorPage
    :code="statusCode"
    :phrase="phrase"
    :icon="icon"
  />
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { AlertTriangle, XCircle, Info } from 'lucide-vue-next'
import BaseErrorPage from './BaseErrorPage.vue'
import { getErrorPhrase } from './errorPhrases'

const route = useRoute()

const statusCode = computed(() => {
  const raw = route.params.code ?? route.query.status
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const phrase = computed(() => getErrorPhrase(statusCode.value))

const icon = computed(() => {
  switch (statusCode.value) {
    case 500:
      return XCircle
    case 503:
      return AlertTriangle
    default:
      return Info
  }
})
</script>

