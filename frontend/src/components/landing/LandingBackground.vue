<script setup>
import { defineAsyncComponent } from 'vue'

const SPLINE_SCENE_URL = ''

const Spline3DBackground = defineAsyncComponent(() => import('./Spline3DBackground.vue'))
</script>

<template>
  <div class="hero-bg">
    <Spline3DBackground v-if="SPLINE_SCENE_URL" :scene-url="SPLINE_SCENE_URL" />
    <div class="gradient-mesh" aria-hidden="true">
      <div class="orb orb-1" />
      <div class="orb orb-2" />
      <div class="orb orb-3" />
      <div class="orb orb-4" />
      <div class="orb orb-5" />
    </div>
  </div>
</template>
