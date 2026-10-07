<template>
  <div class="login-page">
    <div class="login-card pa-card">
      <div class="login-brand">
        <div class="login-logo">PA</div>
        <div class="login-title">个人全能助手</div>
        <div class="login-sub pa-muted">Personal Assistant · 请登录</div>
      </div>

      <el-form :model="form" @submit.prevent="submit">
        <el-form-item>
          <el-input
            v-model="form.username"
            size="large"
            placeholder="用户名"
            :prefix-icon="User"
            maxlength="30"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            placeholder="密码"
            show-password
            :prefix-icon="Lock"
            maxlength="64"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="submit"
        >
          登 录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.username.trim()) { ElMessage.warning('请输入用户名'); return }
  if (!form.password) { ElMessage.warning('请输入密码'); return }
  loading.value = true
  try {
    const user = await auth.login(form.username.trim(), form.password)
    ElMessage.success(`欢迎回来，${user.username}`)
    router.push('/')
  } catch { /* 错误提示由拦截器统一弹出 */ } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  background:
    radial-gradient(1000px 500px at 15% 10%, rgba(245, 158, 11, .12), transparent 60%),
    radial-gradient(900px 500px at 85% 90%, rgba(139, 92, 246, .12), transparent 60%),
    var(--color-bg-primary);
}
.login-card {
  width: 380px; padding: 34px 32px 28px;
  border-radius: var(--radius-lg);
}
.login-brand { text-align: center; margin-bottom: 24px; }
.login-logo {
  width: 56px; height: 56px; margin: 0 auto 12px;
  border-radius: 16px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206; font-weight: 800; font-size: 20px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 6px 20px rgba(245, 158, 11, .35);
}
.login-title { font-size: 20px; font-weight: 800; color: var(--color-text-primary); }
.login-sub { font-size: 12px; margin-top: 5px; }
.login-btn { width: 100%; }
</style>
