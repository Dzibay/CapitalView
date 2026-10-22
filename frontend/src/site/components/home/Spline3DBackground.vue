<script setup>
/**
 * 3D фон на базе Spline.
 * Чтобы добавить свою 3D-сцену:
 * 1. Создайте сцену на spline.design (бесплатный план)
 * 2. Export → Vanilla JS → скопируйте URL scene.splinecode
 * 3. Передайте URL в проп sceneUrl
 */
import { ref, onMounted, watch } from 'vue'
import { Application } from '@splinetool/runtime'

const props = defineProps({
  sceneUrl: {
    type: String,
    default: ''
  }
})

const canvasRef = ref(null)
let app = null

onMounted(async () => {
  if (!props.sceneUrl || !canvasRef.value) return
  try {
    app = new Application(canvasRef.value)
    await app.load(props.sceneUrl)
  } catch (e) {
    console.warn('Spline scene failed to load:', e)
  }
})

watch(() => props.sceneUrl, async (url) => {
  if (app && url) {
    try {
      await app.load(url)
    } catch (e) {
      console.warn('Spline scene failed to load:', e)
    }
  }
})
</script>

<template>
  <canvas
    v-if="sceneUrl"
    ref="canvasRef"
    class="spline-canvas"
    aria-hidden="true"
  />
</template>

<style scoped>
.spline-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
  pointer-events: none;
}
</style>
