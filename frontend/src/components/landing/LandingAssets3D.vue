<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { prefersReducedMotion } from './useLandingMotion'

gsap.registerPlugin(ScrollTrigger)

/** Закреплённая 3D-сцена: разрозненные активы при скролле собираются в единое кольцо. */
const CHIPS = [
  { k: 'Акции', c: '#3d5afe' },
  { k: 'Облигации', c: '#22b8cf' },
  { k: 'Фонды', c: '#8b5cf6' },
  { k: 'Валюта', c: '#12b76a' },
  { k: 'Золото', c: '#f5b544' },
  { k: 'Крипто', c: '#ff7a45' },
  { k: 'Недвижимость', c: '#c4b5fd' },
  { k: 'Вклады', c: '#7dd3fc' }
]

const root = ref(null)
const stage = ref(null)
const canvas = ref(null)
let three = null
let ctx = null
let io = null

async function initScene(reduced) {
  const THREE = await import('three')
  const { RoomEnvironment } = await import('three/examples/jsm/environments/RoomEnvironment.js')
  const { RoundedBoxGeometry } = await import('three/examples/jsm/geometries/RoundedBoxGeometry.js')
  if (!canvas.value) return null

  const renderer = new THREE.WebGLRenderer({ canvas: canvas.value, antialias: true, alpha: true, powerPreference: 'high-performance' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75))
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.05
  renderer.outputColorSpace = THREE.SRGBColorSpace

  const scene = new THREE.Scene()
  const pmrem = new THREE.PMREMGenerator(renderer)
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.environment = envTex

  const camera = new THREE.PerspectiveCamera(34, 1, 0.1, 100)
  camera.position.set(0, 0.6, 15)

  scene.add(new THREE.AmbientLight(0x8090ff, 0.35))
  const key = new THREE.DirectionalLight(0xffffff, 2.2)
  key.position.set(4, 6, 8)
  scene.add(key)
  const rim = new THREE.DirectionalLight(0x6b7dff, 3)
  rim.position.set(-6, 2, -6)
  scene.add(rim)
  const core = new THREE.PointLight(0x7c8cff, 30, 12, 1.6)
  scene.add(core)

  /* ---------- материалы ---------- */
  const gold = new THREE.MeshPhysicalMaterial({ color: 0xf3c56b, metalness: 1, roughness: 0.22, clearcoat: 0.6, clearcoatRoughness: 0.15 })
  const silver = new THREE.MeshPhysicalMaterial({ color: 0xdfe3ec, metalness: 1, roughness: 0.2, clearcoat: 0.5 })
  const glass = (tint) => new THREE.MeshPhysicalMaterial({
    color: tint, metalness: 0, roughness: 0.06, transmission: 1, thickness: 1.2, ior: 1.45,
    clearcoat: 1, clearcoatRoughness: 0.05, attenuationColor: new THREE.Color(tint), attenuationDistance: 2.4
  })
  const blueMetal = new THREE.MeshPhysicalMaterial({ color: 0x3d5afe, metalness: 0.55, roughness: 0.25, clearcoat: 1, clearcoatRoughness: 0.1 })

  function faceTexture(symbol, from, to, ink) {
    const s = 512
    const c = document.createElement('canvas')
    c.width = c.height = s
    const g = c.getContext('2d')
    const grad = g.createRadialGradient(s * 0.38, s * 0.32, s * 0.05, s / 2, s / 2, s * 0.55)
    grad.addColorStop(0, from)
    grad.addColorStop(1, to)
    g.fillStyle = grad
    g.fillRect(0, 0, s, s)
    g.strokeStyle = ink
    g.globalAlpha = 0.55
    g.lineWidth = 10
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.4, 0, Math.PI * 2); g.stroke()
    g.lineWidth = 3
    g.beginPath(); g.arc(s / 2, s / 2, s * 0.355, 0, Math.PI * 2); g.stroke()
    g.globalAlpha = 1
    g.fillStyle = ink
    g.font = `600 ${s * 0.42}px "Inter Tight", Inter, system-ui, sans-serif`
    g.textAlign = 'center'
    g.textBaseline = 'middle'
    g.shadowColor = 'rgba(255,255,255,.55)'
    g.shadowOffsetY = 4
    g.fillText(symbol, s / 2, s / 2 + s * 0.02)
    const tex = new THREE.CanvasTexture(c)
    tex.colorSpace = THREE.SRGBColorSpace
    tex.anisotropy = 8
    return tex
  }

  /* ---------- объекты ---------- */
  const objects = []
  const disposables = [envTex, pmrem]

  function coin(symbol, base, face) {
    const geo = new THREE.CylinderGeometry(1, 1, 0.18, 96, 1)
    const tex = faceTexture(symbol, ...face)
    const faceMat = new THREE.MeshPhysicalMaterial({ map: tex, metalness: 1, roughness: 0.28, clearcoat: 0.6 })
    const mesh = new THREE.Mesh(geo, [base, faceMat, faceMat])
    mesh.rotation.x = Math.PI / 2
    const g = new THREE.Group()
    g.add(mesh)
    disposables.push(geo, tex, faceMat)
    return g
  }
  function bar() {
    const shape = new THREE.Shape()
    shape.moveTo(-1.1, -0.35); shape.lineTo(1.1, -0.35); shape.lineTo(0.85, 0.35); shape.lineTo(-0.85, 0.35); shape.closePath()
    const geo = new THREE.ExtrudeGeometry(shape, { depth: 0.8, bevelEnabled: true, bevelSize: 0.06, bevelThickness: 0.06, bevelSegments: 4 })
    geo.center()
    disposables.push(geo)
    const g = new THREE.Group()
    const m = new THREE.Mesh(geo, gold)
    m.rotation.x = 0.5
    g.add(m)
    g.scale.setScalar(0.8)
    return g
  }
  function house() {
    const s = new THREE.Shape()
    s.moveTo(-0.8, -0.8); s.lineTo(0.8, -0.8); s.lineTo(0.8, 0.2); s.lineTo(0, 0.95); s.lineTo(-0.8, 0.2); s.closePath()
    const geo = new THREE.ExtrudeGeometry(s, { depth: 0.8, bevelEnabled: true, bevelSize: 0.08, bevelThickness: 0.08, bevelSegments: 5 })
    geo.center()
    const mat = glass(0xb9a8ff)
    disposables.push(geo, mat)
    const g = new THREE.Group()
    g.add(new THREE.Mesh(geo, mat))
    return g
  }
  function candles() {
    const g = new THREE.Group()
    ;[0.9, 1.5, 2.1].forEach((h, i) => {
      const geo = new RoundedBoxGeometry(0.42, h, 0.42, 4, 0.08)
      const m = new THREE.Mesh(geo, i === 1 ? glass(0x9fb0ff) : blueMetal)
      m.position.set((i - 1) * 0.6, h / 2 - 1, 0)
      g.add(m)
      disposables.push(geo)
    })
    return g
  }
  function orb() {
    const geo = new THREE.IcosahedronGeometry(0.85, 0)
    const mat = glass(0x9be7ff)
    disposables.push(geo, mat)
    const g = new THREE.Group()
    g.add(new THREE.Mesh(geo, mat))
    return g
  }

  const items = [
    coin('₽', silver, ['#f4f6fb', '#9aa3b5', '#2b3242']),
    bar(),
    coin('$', gold, ['#ffe7a8', '#c48a2c', '#5a3a07']),
    candles(),
    coin('₿', gold, ['#ffc58a', '#d46a1c', '#5b2604']),
    house(),
    coin('€', silver, ['#eef1ff', '#8c96c9', '#262c52']),
    bar(),
    orb()
  ]

  // детерминированный «хаос»
  let seed = 7
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
  const ring = new THREE.Group()
  scene.add(ring)
  items.forEach((g, i) => {
    const a = (i / items.length) * Math.PI * 2
    g.userData = {
      a,
      from: (() => {
        // держим «хаос» подальше от заголовка вверху по центру
        const v = new THREE.Vector3((rnd() - 0.5) * 20, (rnd() - 0.5) * 10, (rnd() - 0.5) * 8 - 1)
        if (v.y > -0.5 && Math.abs(v.x) < 5.5) v.x = Math.sign(v.x || 1) * (5.5 + rnd() * 3)
        return v
      })(),
      rotFrom: new THREE.Euler(rnd() * 6, rnd() * 6, rnd() * 6),
      phase: rnd() * Math.PI * 2,
      delay: (i % 4) * 0.06
    }
    ring.add(g)
    objects.push(g)
  })

  // светящееся ядро в центре кольца
  const glowTex = (() => {
    const c = document.createElement('canvas')
    c.width = c.height = 256
    const g = c.getContext('2d')
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128)
    gr.addColorStop(0, 'rgba(190,200,255,1)')
    gr.addColorStop(0.25, 'rgba(110,130,255,.55)')
    gr.addColorStop(1, 'rgba(80,90,255,0)')
    g.fillStyle = gr
    g.fillRect(0, 0, 256, 256)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    return t
  })()
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }))
  glow.scale.setScalar(5)
  scene.add(glow)
  disposables.push(glowTex, glow.material)

  /* ---------- цикл ---------- */
  const state = { target: reduced ? 1 : 0, p: reduced ? 1 : 0, mx: 0, my: 0, tx: 0, ty: 0 }
  let last = performance.now()
  let elapsed = 0
  const tmp = new THREE.Vector3()
  const ease = (t) => (t < 0 ? 0 : t > 1 ? 1 : t * t * (3 - 2 * t))
  let spin = 0
  let running = false
  let raf = 0
  const ringCenter = new THREE.Vector3(0, -1.5, 0)

  function resize() {
    const { clientWidth: w, clientHeight: h } = stage.value
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.position.z = camera.aspect < 1.4 ? 15 * Math.pow(1.4 / camera.aspect, 0.85) : 15
    camera.updateProjectionMatrix()
  }

  function frame() {
    if (!running) return
    raf = requestAnimationFrame(frame)
    const now = performance.now()
    const dt = Math.min((now - last) / 1000, 0.05)
    last = now
    elapsed += dt
    const t = elapsed
    state.p += (state.target - state.p) * Math.min(1, dt * 4)
    state.mx += (state.tx - state.mx) * Math.min(1, dt * 3)
    state.my += (state.ty - state.my) * Math.min(1, dt * 3)
    const p = state.p

    spin += dt * (0.06 + 0.22 * ease((p - 0.5) / 0.5))
    const R = 4.2
    objects.forEach((g) => {
      const u = g.userData
      const k = ease((p - 0.12 - u.delay) / 0.55)
      const ang = u.a + spin
      tmp.set(Math.sin(ang) * R, Math.sin(ang * 2 + t * 0.4) * 0.12, Math.cos(ang) * R).add(ringCenter)
      const fx = u.from.x + Math.sin(t * 0.35 + u.phase) * 0.35
      const fy = u.from.y + Math.cos(t * 0.3 + u.phase) * 0.35
      g.position.set(
        fx + (tmp.x - fx) * k,
        fy + (tmp.y - fy) * k,
        u.from.z + (tmp.z - u.from.z) * k
      )
      const idle = t * 0.25 + u.phase
      g.rotation.set(
        u.rotFrom.x * (1 - k) + Math.sin(t * 0.5 + u.phase) * 0.12 * k,
        u.rotFrom.y * (1 - k) + (idle * (1 - k)) + (Math.sin(t * 0.6 + u.phase) * 0.35 - ang * 0.15) * k,
        u.rotFrom.z * (1 - k)
      )
      g.scale.setScalar((g.userData.base ??= g.scale.x) * (0.9 + 0.1 * k))
    })
    ring.rotation.x = 0.28 * ease(p / 0.7)
    ring.position.set(state.mx * 0.5, state.my * 0.3, 0)
    camera.position.x = state.mx * 0.8
    camera.position.y = 0.6 - state.my * 0.4
    camera.lookAt(0, -0.6, 0)

    const gk = ease((p - 0.45) / 0.45)
    glow.position.copy(ringCenter)
    glow.material.opacity = gk * (0.85 + Math.sin(t * 1.4) * 0.1)
    glow.scale.setScalar(3 + gk * 3)
    core.position.copy(ringCenter)
    core.intensity = 4 + gk * 40
    renderer.render(scene, camera)
  }

  resize()
  return {
    state,
    resize,
    start() { if (!running) { running = true; last = performance.now(); frame() } },
    stop() { running = false; cancelAnimationFrame(raf) },
    renderOnce() { running = true; frame(); running = false; cancelAnimationFrame(raf) },
    dispose() {
      running = false
      cancelAnimationFrame(raf)
      disposables.forEach((d) => d.dispose?.())
      ;[gold, silver, blueMetal].forEach((m) => m.dispose())
      scene.traverse((o) => { if (o.material && !Array.isArray(o.material)) o.material.dispose?.() })
      renderer.dispose()
    }
  }
}

function onMove(e) {
  if (!three) return
  const r = stage.value.getBoundingClientRect()
  three.state.tx = ((e.clientX - r.left) / r.width - 0.5) * 2
  three.state.ty = ((e.clientY - r.top) / r.height - 0.5) * 2
}
function onLeave() {
  if (!three) return
  three.state.tx = 0
  three.state.ty = 0
}
function onResize() { three?.resize() }

onMounted(() => {
  const reduced = prefersReducedMotion()
  let progress = reduced ? 1 : 0

  ctx = gsap.context(() => {
    if (reduced) return
    const tl = gsap.timeline({ defaults: { ease: 'none' } })
    tl.to('.la-phase--1', { opacity: 0, y: -40, filter: 'blur(8px)', duration: 0.2 }, 0.22)
      .fromTo('.la-phase--2', { opacity: 0, y: 40, filter: 'blur(8px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.18 }, 0.3)
      .to('.la-phase--2', { opacity: 0, y: -40, filter: 'blur(8px)', duration: 0.18 }, 0.58)
      .fromTo('.la-phase--3', { opacity: 0, y: 40, filter: 'blur(8px)' }, { opacity: 1, y: 0, filter: 'blur(0px)', duration: 0.18 }, 0.66)
      .from('.la-chip', { opacity: 0, y: 16, stagger: 0.012, duration: 0.1 }, 0.74)
      .to('.la-progress i', { scaleX: 1, duration: 1 }, 0)

    ScrollTrigger.create({
      trigger: root.value,
      start: 'top top',
      end: '+=220%',
      pin: true,
      scrub: 0.6,
      animation: tl,
      onUpdate(self) {
        progress = self.progress
        if (three) three.state.target = progress
      }
    })
  }, root.value)

  window.addEventListener('resize', onResize)
  io = new IntersectionObserver(async ([en]) => {
    if (en.isIntersecting && !three) {
      try {
        three = await initScene(reduced)
        if (three) three.state.target = three.state.p = progress
      } catch (err) { console.error('[LandingAssets3D]', err); three = null }
    }
    if (!three) return
    if (en.isIntersecting) three.start()
    else three.stop()
  }, { rootMargin: '200px 0px' })
  io.observe(root.value)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  io?.disconnect()
  ctx?.revert()
  three?.dispose()
})
</script>

<template>
  <section ref="root" class="la" aria-label="Любые активы в одном портфеле">
    <div ref="stage" class="la-stage" @pointermove="onMove" @pointerleave="onLeave">
      <canvas ref="canvas" class="la-canvas" aria-hidden="true" />
      <div class="la-noise" aria-hidden="true" />

      <div class="la-copy">
        <div class="la-phase la-phase--1">
          <span class="lp-eyebrow lp-eyebrow--dark">Любые активы</span>
          <h2 class="la-title">Акции в&nbsp;одном приложении. Золото&nbsp;— в&nbsp;другом. <span class="la-dim">Крипта&nbsp;— где-то ещё.</span></h2>
        </div>
        <div class="la-phase la-phase--2">
          <span class="lp-eyebrow lp-eyebrow--dark">Единая модель</span>
          <h2 class="la-title">CapitalView собирает их <span class="la-grad">в&nbsp;одну систему</span></h2>
          <p class="la-sub">Биржевые бумаги, вклады, металлы, валюта, крипта и&nbsp;недвижимость с&nbsp;единой доходностью и&nbsp;валютой отчёта.</p>
        </div>
        <div class="la-phase la-phase--3">
          <span class="lp-eyebrow lp-eyebrow--dark">Итог</span>
          <h2 class="la-title">Один капитал. <span class="la-grad">Одна цифра.</span></h2>
          <ul class="la-chips">
            <li v-for="c in CHIPS" :key="c.k" class="la-chip"><i :style="{ background: c.c, boxShadow: `0 0 12px ${c.c}` }" />{{ c.k }}</li>
          </ul>
        </div>
      </div>

      <div class="la-progress" aria-hidden="true"><i /></div>
    </div>
  </section>
</template>

<style scoped>
.la { position: relative; height: 100vh; height: 100svh; padding: 12px; background: var(--lp-bg); }
.la-stage {
  position: relative; height: 100%; border-radius: clamp(24px, 3vw, 40px); overflow: hidden; isolation: isolate;
  background:
    radial-gradient(60% 50% at 50% 72%, rgba(61,90,254,.22), transparent 70%),
    radial-gradient(40% 40% at 85% 10%, rgba(139,92,246,.14), transparent 70%),
    linear-gradient(180deg, #07080d, #0b0d16 60%, #07080d);
  box-shadow: inset 0 1px 0 rgba(255,255,255,.08), inset 0 0 0 1px rgba(255,255,255,.05);
}
.la-canvas { position: absolute; inset: 0; width: 100%; height: 100%; z-index: 0; }
.la-noise {
  position: absolute; inset: 0; z-index: 1; pointer-events: none; opacity: .07; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
.la-copy { position: absolute; left: 0; right: 0; top: clamp(56px, 11vh, 120px); z-index: 2; display: grid; pointer-events: none; padding: 0 var(--lp-pad); }
.la-phase { grid-area: 1 / 1; display: flex; flex-direction: column; align-items: center; text-align: center; }
.la-phase--2, .la-phase--3 { opacity: 0; }
.la-title {
  margin-top: 18px; max-width: 980px;
  font-family: var(--lp-display); font-weight: 600; font-size: clamp(34px, 5vw, 72px); line-height: 1.02; letter-spacing: -0.045em; color: #fff;
  text-wrap: balance;
}
.la-dim { color: rgba(255,255,255,.4); }
.la-grad {
  background: linear-gradient(90deg, #a5b4ff, #c4b5fd 50%, #7dd3fc); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.la-sub { margin-top: 18px; max-width: 560px; font-size: clamp(15px, 1.25vw, 18px); line-height: 1.55; color: rgba(255,255,255,.6); }
.la-chips { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; max-width: 720px; margin: 26px 0 0; padding: 0; list-style: none; }
.la-chip {
  display: flex; align-items: center; gap: 8px; padding: 7px 14px; border-radius: 99px;
  font-size: 13.5px; color: rgba(255,255,255,.85);
  background: rgba(255,255,255,.06); box-shadow: inset 0 1px 0 rgba(255,255,255,.08), inset 0 0 0 1px rgba(255,255,255,.08);
  backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
}
.la-chip i { width: 7px; height: 7px; border-radius: 50%; }
.la-progress { position: absolute; left: 50%; bottom: 28px; width: 120px; height: 2px; translate: -50% 0; z-index: 2; border-radius: 2px; background: rgba(255,255,255,.12); overflow: hidden; }
.la-progress i { display: block; height: 100%; background: linear-gradient(90deg, #3d5afe, #8b5cf6); transform: scaleX(0); transform-origin: left; }

@media (max-width: 640px) {
  .la { padding: 8px; }
  .la-copy { top: 72px; }
  .la-chip { font-size: 12.5px; padding: 6px 11px; }
}
@media (prefers-reduced-motion: reduce) {
  .la-phase--1, .la-phase--2 { display: none; }
  .la-phase--3 { opacity: 1; }
}
</style>
