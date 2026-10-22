import { Camera, Color, Mesh, PlaneGeometry, Scene, ShaderMaterial, Vector2, WebGLRenderer } from 'three'

/**
 * Светлый «жидкий» градиент на весь экран: несколько мягких пятен цвета,
 * доменное искажение шумом и пятно, которое тянется за курсором.
 */
const vert = /* glsl */ `
varying vec2 vUv;
void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }
`

const frag = /* glsl */ `
precision highp float;
varying vec2 vUv;
uniform float uTime;
uniform vec2 uRes;
uniform vec2 uMouse;
uniform float uMouseAmt;
uniform float uScroll;
uniform vec3 uBase;
uniform vec3 uC1;
uniform vec3 uC2;
uniform vec3 uC3;

vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
vec2 mod289(vec2 x){return x-floor(x*(1./289.))*289.;}
vec3 permute(vec3 x){return mod289(((x*34.)+1.)*x);}
float snoise(vec2 v){
  const vec4 C=vec4(.211324865405187,.366025403784439,-.577350269189626,.024390243902439);
  vec2 i=floor(v+dot(v,C.yy)); vec2 x0=v-i+dot(i,C.xx);
  vec2 i1=(x0.x>x0.y)?vec2(1.,0.):vec2(0.,1.);
  vec4 x12=x0.xyxy+C.xxzz; x12.xy-=i1; i=mod289(i);
  vec3 p=permute(permute(i.y+vec3(0.,i1.y,1.))+i.x+vec3(0.,i1.x,1.));
  vec3 m=max(.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.); m=m*m; m=m*m;
  vec3 x=2.*fract(p*C.www)-1.; vec3 h=abs(x)-.5; vec3 ox=floor(x+.5); vec3 a0=x-ox;
  m*=1.79284291400159-.85373472095314*(a0*a0+h*h);
  vec3 g; g.x=a0.x*x0.x+h.x*x0.y; g.yz=a0.yz*x12.xz+h.yz*x12.yw; return 130.*dot(m,g);
}

float blob(vec2 p, vec2 c, float r){ return smoothstep(r, 0.0, length(p - c)); }

void main(){
  float aspect = uRes.x / uRes.y;
  vec2 p = vUv; p.x *= aspect;
  float t = uTime * 0.06;

  vec2 q = vec2(snoise(p * 1.2 + t), snoise(p * 1.2 - t + 4.0));
  vec2 w = p + q * 0.22;

  vec2 m = uMouse; m.x *= aspect;
  float s = uScroll * 0.6;

  vec2 c1 = vec2(aspect * (0.78 + 0.08 * sin(t * 2.0)), 0.78 + 0.08 * cos(t * 1.6) - s);
  vec2 c2 = vec2(aspect * (0.18 + 0.1 * cos(t * 1.4)), 0.3 + 0.1 * sin(t * 2.2) + s * 0.5);
  vec2 c3 = vec2(aspect * (0.55 + 0.12 * sin(t * 1.1 + 2.0)), 0.12 + 0.08 * cos(t * 1.7));

  vec3 col = uBase;
  col = mix(col, uC1, blob(w, c1, 0.75) * 0.85);
  col = mix(col, uC2, blob(w, c2, 0.7) * 0.75);
  col = mix(col, uC3, blob(w, c3, 0.6) * 0.6);
  col = mix(col, uC1 * 0.92 + 0.06, blob(w, m, 0.38) * 0.55 * uMouseAmt);

  float g = fract(sin(dot(gl_FragCoord.xy + uTime, vec2(12.9898, 78.233))) * 43758.5453);
  col += (g - 0.5) * 0.035;
  gl_FragColor = vec4(col, 1.0);
}
`

export function createFluidBg(canvas) {
  const renderer = new WebGLRenderer({ canvas, antialias: false, alpha: false, powerPreference: 'low-power' })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.25))
  const scene = new Scene()
  const camera = new Camera()
  const uniforms = {
    uTime: { value: 0 },
    uRes: { value: new Vector2(1, 1) },
    uMouse: { value: new Vector2(0.7, 0.6) },
    uMouseAmt: { value: 0 },
    uScroll: { value: 0 },
    uBase: { value: new Color('#f3f0e9') },
    uC1: { value: new Color('#bcd0ff') },
    uC2: { value: new Color('#e3f5b8') },
    uC3: { value: new Color('#ffd8c8') }
  }
  const mesh = new Mesh(
    new PlaneGeometry(2, 2),
    new ShaderMaterial({ vertexShader: vert, fragmentShader: frag, uniforms, depthTest: false })
  )
  scene.add(mesh)

  const target = { x: 0.7, y: 0.6, amt: 0 }
  let raf = 0
  let last = performance.now()

  function resize() {
    const w = window.innerWidth
    const h = window.innerHeight
    renderer.setSize(w, h, false)
    uniforms.uRes.value.set(w, h)
  }

  function frame(now) {
    raf = requestAnimationFrame(frame)
    const dt = Math.min((now - last) / 1000, 0.05)
    last = now
    uniforms.uTime.value += dt
    const k = 1 - Math.pow(0.03, dt)
    uniforms.uMouse.value.x += (target.x - uniforms.uMouse.value.x) * k
    uniforms.uMouse.value.y += (target.y - uniforms.uMouse.value.y) * k
    uniforms.uMouseAmt.value += (target.amt - uniforms.uMouseAmt.value) * k
    renderer.render(scene, camera)
  }

  resize()
  return {
    uniforms,
    resize,
    setPointer(x, y) {
      target.x = x / window.innerWidth
      target.y = 1 - y / window.innerHeight
      target.amt = 1
    },
    clearPointer() { target.amt = 0 },
    start() { if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame) } },
    stop() { cancelAnimationFrame(raf); raf = 0 },
    dispose() {
      cancelAnimationFrame(raf)
      mesh.geometry.dispose()
      mesh.material.dispose()
      renderer.dispose()
    }
  }
}
