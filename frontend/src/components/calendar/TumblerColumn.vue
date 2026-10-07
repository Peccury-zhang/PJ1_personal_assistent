<template>
  <div
    ref="vpRef"
    class="t-vp"
    :style="{ height: rows * itemH + 'px' }"
    @scroll.passive="onScroll"
    @pointerdown="onDown"
  >
    <div class="t-list" :style="{ padding: half * itemH + 'px 0' }">
      <div
        v-for="(o, i) in options"
        :key="o.value"
        :ref="(el) => setItemRef(i, el)"
        class="t-item"
        :style="{ height: itemH + 'px' }"
        @click="clickItem(i)"
      >{{ o.label }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch, nextTick } from 'vue'

export interface TumblerOption { value: number; label: string }

const props = withDefaults(defineProps<{
  options: TumblerOption[]
  modelValue: number
  rows?: number
  itemH?: number
}>(), { rows: 7, itemH: 36 })

const emit = defineEmits<{ (e: 'update:modelValue', v: number): void }>()

const half = computed(() => Math.floor(props.rows / 2))
const vpRef = ref<HTMLElement | null>(null)
const itemEls: (HTMLElement | null)[] = []
function setItemRef(i: number, el: any) { itemEls[i] = el as HTMLElement }

const idx = computed(() => Math.max(0, props.options.findIndex((o) => o.value === props.modelValue)))

let snapTimer = 0
let momentumRaf = 0
let paintRaf = 0
let dragging = false
let moved = false
let momentum = false
let lastY = 0
let lastT = 0
let velocity = 0

const scrollTopFor = (i: number) => i * props.itemH
const clampIdx = (i: number) => Math.min(Math.max(i, 0), props.options.length - 1)

/** 按每项到中心线的距离实时缩放/淡化，形成滚轮弧面感 */
function paint() {
  const vp = vpRef.value
  if (!vp) return
  const center = vp.scrollTop + vp.clientHeight / 2
  const padTop = half.value * props.itemH
  for (let i = 0; i < props.options.length; i++) {
    const el = itemEls[i]
    if (!el) continue
    const itemCenter = padTop + i * props.itemH + props.itemH / 2
    const d = Math.abs((itemCenter - center) / props.itemH)
    el.style.transform = `scale(${Math.max(0.6, 1 - 0.16 * d).toFixed(3)})`
    el.style.opacity = Math.max(0.2, 1 - 0.3 * d).toFixed(2)
    el.classList.toggle('active', d < 0.5)
  }
}

function emitCurrent() {
  const vp = vpRef.value
  if (!vp) return
  const val = props.options[clampIdx(Math.round(vp.scrollTop / props.itemH))]?.value
  if (val !== undefined && val !== props.modelValue) emit('update:modelValue', val)
}

function onScroll() {
  if (!paintRaf) {
    paintRaf = requestAnimationFrame(() => { paintRaf = 0; paint(); emitCurrent() })
  }
  scheduleSnap()
}

function scheduleSnap() {
  if (dragging || momentum) return
  window.clearTimeout(snapTimer)
  snapTimer = window.setTimeout(() => {
    const vp = vpRef.value
    if (vp) snapTo(Math.round(vp.scrollTop / props.itemH))
  }, 110)
}

function snapTo(i: number, smooth = true) {
  const vp = vpRef.value
  if (!vp) return
  const target = scrollTopFor(clampIdx(i))
  if (Math.abs(vp.scrollTop - target) < 0.5) { paint(); return }
  vp.scrollTo({ top: target, behavior: smooth ? 'smooth' : 'auto' })
}

// ---------------- 鼠标/触摸拖拽 + 惯性 ----------------
function onDown(e: PointerEvent) {
  stopMomentum()
  window.clearTimeout(snapTimer)
  dragging = true
  moved = false
  lastY = e.clientY
  lastT = performance.now()
  velocity = 0
  window.addEventListener('pointermove', onMove)
  window.addEventListener('pointerup', onUpOnce)
  window.addEventListener('pointercancel', onUpOnce)
}
function onMove(e: PointerEvent) {
  if (!dragging) return
  const vp = vpRef.value
  if (!vp) return
  const dy = e.clientY - lastY
  if (Math.abs(dy) > 2) moved = true
  const now = performance.now()
  const dt = Math.max(1, now - lastT)
  velocity = dy / dt
  vp.scrollTop -= dy
  lastY = e.clientY
  lastT = now
}
function onUpOnce() {
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUpOnce)
  window.removeEventListener('pointercancel', onUpOnce)
  if (!dragging) return
  dragging = false
  // 松手后按松手速度继续滑行（惯性），衰减后吸附到最近一项
  let v = velocity * 16
  if (Math.abs(v) > 2) {
    momentum = true
    const step = () => {
      const vp = vpRef.value
      if (!vp) { momentum = false; return }
      v *= 0.94
      vp.scrollTop -= v
      if (Math.abs(v) > 0.6) momentumRaf = requestAnimationFrame(step)
      else { momentum = false; snapTo(Math.round(vp.scrollTop / props.itemH)) }
    }
    momentumRaf = requestAnimationFrame(step)
  } else {
    const vp = vpRef.value
    if (vp) snapTo(Math.round(vp.scrollTop / props.itemH))
  }
}
function stopMomentum() {
  if (momentumRaf) cancelAnimationFrame(momentumRaf)
  momentumRaf = 0
  momentum = false
}

function clickItem(i: number) {
  if (moved) { moved = false; return }
  stopMomentum()
  snapTo(i)   // 平滑滚动到被点击项，产生滑动动画
}

// 外部修改 modelValue（如打开弹窗定位到当年当月）时同步滚动位置
watch(() => props.modelValue, () => {
  if (dragging || momentum) return
  const vp = vpRef.value
  if (!vp) return
  if (Math.round(vp.scrollTop / props.itemH) !== idx.value) snapTo(idx.value, false)
  else paint()
})
watch(() => props.options.length, () => nextTick(() => { snapTo(idx.value, false); paint() }))

onMounted(() => nextTick(() => { snapTo(idx.value, false); paint() }))
onBeforeUnmount(() => {
  stopMomentum()
  window.clearTimeout(snapTimer)
  if (paintRaf) cancelAnimationFrame(paintRaf)
  window.removeEventListener('pointermove', onMove)
  window.removeEventListener('pointerup', onUpOnce)
  window.removeEventListener('pointercancel', onUpOnce)
})
</script>

<style scoped>
.t-vp {
  overflow-y: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  cursor: grab;
  user-select: none;
  touch-action: none;
}
.t-vp::-webkit-scrollbar { display: none; }
.t-vp:active { cursor: grabbing; }
.t-list { display: flex; flex-direction: column; align-items: center; }
.t-item {
  display: flex; align-items: center; justify-content: center;
  width: 100%; border-radius: 8px;
  font-size: 18px; font-weight: 600;
  color: var(--color-text-secondary);
  cursor: pointer;
  will-change: transform, opacity;
  transition: color .15s ease, background .15s ease;
}
/* 中心选中项：最大最亮 + 高亮底 */
.t-item.active {
  color: var(--color-primary);
  font-weight: 800;
  background: rgba(59,130,246,.14);
}
</style>
