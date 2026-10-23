<script setup>
/** Заглушка главной на время загрузки — повторяет раскладку по умолчанию. */
const CARDS = [
  { span: 'l', h: 470, kind: 'chart' },
  { span: 's', h: 470, kind: 'list' },
  { span: 'xl', h: 210, kind: 'cols' },
  { span: 'm', h: 400, kind: 'block' },
  { span: 'm', h: 400, kind: 'list' },
]
</script>

<template>
  <div class="dsk" aria-busy="true" aria-label="Загружаем главную">
    <div class="dsk__head">
      <div class="cv-skel" style="width: 140px; height: 11px" />
      <div class="cv-skel" style="width: 280px; height: 30px; margin-top: 12px" />
      <div class="cv-skel" style="width: 180px; height: 14px; margin-top: 10px" />
    </div>
    <div class="dsk__grid">
      <div v-for="(c, i) in CARDS" :key="i" class="dsk__card cv-card" :class="`is-${c.span}`" :style="{ minHeight: `${c.h}px` }">
        <div class="cv-skel" style="width: 38%; height: 14px" />
        <template v-if="c.kind === 'chart'">
          <div class="cv-skel" style="width: 46%; height: 40px; margin-top: 18px" />
          <div class="cv-skel dsk__fill" style="margin-top: 22px" />
        </template>
        <template v-else-if="c.kind === 'bars'">
          <div class="dsk__bars">
            <div v-for="n in 12" :key="n" class="cv-skel" :style="{ height: `${30 + ((n * 37) % 60)}%` }" />
          </div>
        </template>
        <div v-else-if="c.kind === 'cols'" class="dsk__cols">
          <div v-for="n in 4" :key="n">
            <div class="cv-skel" style="width: 40%; height: 12px" />
            <div class="cv-skel" style="height: 14px; margin-top: 14px" />
            <div class="cv-skel" style="width: 70%; height: 14px; margin-top: 8px" />
            <div class="cv-skel" style="height: 24px; margin-top: 22px" />
          </div>
        </div>
        <template v-else-if="c.kind === 'block'">
          <div class="cv-skel dsk__fill" style="margin-top: 18px" />
        </template>
        <template v-else>
          <div class="cv-skel" style="width: 60%; height: 32px; margin-top: 18px" />
          <div v-for="n in 4" :key="n" class="cv-skel" style="height: 14px; margin-top: 18px" :style="{ width: `${90 - n * 12}%` }" />
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dsk__head { padding: 26px 0 30px; }
.dsk__grid { display: grid; grid-template-columns: repeat(12, minmax(0, 1fr)); gap: var(--cv-gap); }
.dsk__card { display: flex; flex-direction: column; padding: 22px 24px 24px; }
.dsk__card.is-xl { grid-column: span 12; }
.dsk__cols { flex: 1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 48px; margin-top: 30px; }
.dsk__card.is-s { grid-column: span 4; }
.dsk__card.is-m { grid-column: span 6; }
.dsk__card.is-l { grid-column: span 8; }
.dsk__fill { flex: 1; border-radius: 12px; }
.dsk__bars { flex: 1; display: flex; align-items: flex-end; gap: 8px; margin-top: 22px; }
.dsk__bars > * { flex: 1; border-radius: 6px 6px 2px 2px; }

@media (max-width: 1200px) {
  .dsk__grid { grid-auto-flow: row dense; }
  .dsk__card.is-s, .dsk__card.is-m { grid-column: span 6; }
  .dsk__card.is-l { grid-column: span 12; }
}
@media (max-width: 768px) {
  .dsk__grid { gap: 12px; }
  .dsk__cols { grid-template-columns: minmax(0, 1fr); gap: 28px; }
  .dsk__card { grid-column: span 12 !important; }
}
</style>
