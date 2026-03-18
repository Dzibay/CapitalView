<template>
  <BaseErrorPage
    :code="404"
    :icon="AlertTriangle"
    :phrase="phrase"
  />
</template>

<script setup>
import { AlertTriangle } from 'lucide-vue-next'
import BaseErrorPage from './BaseErrorPage.vue'
import { getErrorPhrase } from './errorPhrases'

const phrase = getErrorPhrase(404)
</script>

