<template>
  <div class="profile-view">
    <div class="pv-card pa-card">
      <div class="pv-title">个人中心</div>

      <!-- 头像 -->
      <div class="pv-avatar-wrap" title="点击更换头像" @click="pickFile">
        <img v-if="auth.user?.avatar" :src="auth.user.avatar" class="pv-avatar" alt="头像" />
        <div v-else class="pv-avatar pv-avatar-fallback">
          <el-icon :size="40"><User /></el-icon>
        </div>
        <div class="pv-avatar-mask">
          <el-icon :size="18"><Camera /></el-icon>
          <span>更换</span>
        </div>
      </div>
      <input ref="fileInput" type="file" accept="image/jpeg,image/png,image/webp" hidden @change="onFile" />

      <!-- 基本信息 -->
      <div class="pv-rows">
        <div class="pv-row">
          <span class="pv-label pa-muted">账户ID</span>
          <span class="pv-value">{{ auth.user?.id ?? '-' }}</span>
        </div>
        <div class="pv-row">
          <span class="pv-label pa-muted">用户名</span>
          <span class="pv-value">{{ auth.user?.username || '-' }}</span>
        </div>
        <div class="pv-row">
          <span class="pv-label pa-muted">用户等级</span>
          <el-tag :type="auth.isAdmin ? 'warning' : 'info'" effect="light" size="small">
            {{ auth.isAdmin ? '管理员' : '普通' }}
          </el-tag>
        </div>
        <div class="pv-row">
          <span class="pv-label pa-muted">账户年龄</span>
          <span class="pv-value">{{ accountAge }}</span>
        </div>
      </div>

      <!-- 主题 -->
      <div class="pv-theme">
        <span class="pv-label pa-muted">主题设置</span>
        <el-radio-group :model-value="settings.theme" @update:model-value="onTheme">
          <el-radio-button value="dark">暗色</el-radio-button>
          <el-radio-button value="light">亮色</el-radio-button>
        </el-radio-group>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'

const auth = useAuthStore()
const settings = useSettingsStore()
const fileInput = ref<HTMLInputElement | null>(null)

const ACCEPT = ['image/jpeg', 'image/png', 'image/webp']

/** 账户年龄：自创建起按月计算 */
const accountAge = computed(() => {
  const created = auth.user?.created_at
  if (!created) return '-'
  const months = dayjs().diff(dayjs(created), 'month')
  return months < 1 ? '不足 1 个月' : `${months} 个月`
})

function pickFile() {
  fileInput.value?.click()
}

/** 读取并压缩为 256x256 的 data URL 后上传 */
async function onFile(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  if (!ACCEPT.includes(file.type)) {
    ElMessage.warning('仅支持 jpg / png / webp 格式图像')
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    ElMessage.warning('图片过大（<=8MB）')
    return
  }
  try {
    const dataUrl = await toSquareDataUrl(file)
    await auth.setAvatar(dataUrl)
    ElMessage.success('头像已更新')
  } catch {
    ElMessage.error('头像处理失败，请换一张图片')
  }
}

/** 居中裁切为正方形并缩放到 256px，输出 webp 以控制体积 */
async function toSquareDataUrl(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file)
  const size = 256
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas unavailable')
  const side = Math.min(bitmap.width, bitmap.height)
  const sx = (bitmap.width - side) / 2
  const sy = (bitmap.height - side) / 2
  ctx.drawImage(bitmap, sx, sy, side, side, 0, 0, size, size)
  bitmap.close?.()
  return canvas.toDataURL('image/webp', 0.9)
}

function onTheme(v: string | number | boolean) {
  settings.setTheme(v as 'dark' | 'light')
}
</script>

<style scoped>
.profile-view {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 8px;
}
.pv-card {
  width: 460px;
  max-width: 100%;
  padding: 26px 28px;
  border-radius: var(--radius-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.pv-title {
  align-self: flex-start;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.pv-avatar-wrap {
  position: relative;
  width: 104px;
  height: 104px;
  border-radius: 50%;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(0, 0, 0, .25);
}
.pv-avatar { width: 100%; height: 100%; object-fit: cover; display: block; }
.pv-avatar-fallback {
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206;
}
.pv-avatar-mask {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  background: rgba(0, 0, 0, .5); color: #fff; font-size: 12px;
  opacity: 0; transition: opacity var(--transition-fast);
}
.pv-avatar-wrap:hover .pv-avatar-mask { opacity: 1; }

.pv-rows { width: 100%; display: flex; flex-direction: column; gap: 12px; }
.pv-row { display: flex; align-items: center; justify-content: space-between; }
.pv-label { font-size: 13.5px; }
.pv-value { font-size: 14px; font-weight: 600; color: var(--color-text-primary); }

.pv-theme {
  width: 100%;
  display: flex; align-items: center; justify-content: space-between;
  padding-top: 14px;
  border-top: 1px solid var(--color-border);
}
</style>
