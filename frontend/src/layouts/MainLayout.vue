<template>
  <div class="layout">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-logo">PA</div>
        <div class="brand-text">
          <div class="brand-title">个人全能助手</div>
          <div class="brand-sub">Personal Assistant</div>
        </div>
      </div>

      <nav class="nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon :size="19"><component :is="item.icon" /></el-icon>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <el-dropdown trigger="click" placement="top-start" @command="onUserCommand">
          <div class="user-chip">
            <div class="user-avatar">
              <img v-if="auth.user?.avatar" :src="auth.user.avatar" class="user-avatar-img" alt="" />
              <el-icon v-else :size="17"><User /></el-icon>
            </div>
            <span class="user-name">{{ auth.user?.username || '未登录' }}</span>
            <el-icon class="user-caret" :size="13"><ArrowUp /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>用户
              </el-dropdown-item>
              <el-dropdown-item v-if="auth.isAdmin" command="users">
                <el-icon><UserFilled /></el-icon>账户管理
              </el-dropdown-item>
              <el-dropdown-item command="settings"><el-icon><Setting /></el-icon>设置</el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <div class="main">
      <main class="content pa-scroll">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" @open-settings="showSettings = true" />
          </transition>
        </router-view>
      </main>
    </div>

    <SettingsDialog v-model="showSettings" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SettingsDialog from '@/components/SettingsDialog.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const showSettings = ref(false)

const baseNav = [
  { path: '/', label: '任务管理', icon: 'Calendar', title: '任务管理' },
  { path: '/report', label: '周报', icon: 'Document', title: '周报' },
  { path: '/weather', label: '天气', icon: 'Sunny', title: '天气' },
  { path: '/butler', label: '智能助手', icon: 'MagicStick', title: '智能助手' }
]
// 管理员额外显示「账户管理」
const navItems = computed(() =>
  auth.isAdmin ? [...baseNav, { path: '/users', label: '账户管理', icon: 'UserFilled', title: '账户管理' }] : baseNav
)

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

async function onUserCommand(cmd: string) {
  if (cmd === 'profile') {
    router.push('/profile')
  } else if (cmd === 'users') {
    router.push('/users')
  } else if (cmd === 'settings') {
    showSettings.value = true
  } else if (cmd === 'logout') {
    await auth.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.layout { display: flex; width: 100%; height: 100%; overflow: hidden; }

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  padding: 18px 18px 16px;
  border-bottom: 1px solid var(--color-border);
}
.brand-logo {
  width: 38px; height: 38px; flex-shrink: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206; font-weight: 800; font-size: 15px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 14px rgba(245, 158, 11, .35);
}
.brand-title { font-size: 15px; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; }
.brand-sub { font-size: 10.5px; color: var(--color-text-muted); margin-top: 3px; letter-spacing: .3px; }

.nav { flex: 1; padding: 12px 10px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 14px; border-radius: var(--radius-sm);
  color: var(--color-text-secondary); text-decoration: none;
  font-size: 14px; font-weight: 500;
  transition: all var(--transition-fast);
  position: relative;
}
.nav-item:hover { background: var(--color-surface-hover); color: var(--color-text-primary); }
.nav-item.active {
  background: linear-gradient(90deg, rgba(245,158,11,.16), rgba(245,158,11,.04));
  color: var(--color-primary-light);
}
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 20px; border-radius: 0 3px 3px 0; background: var(--color-primary);
}

.sidebar-foot { padding: 10px 12px; border-top: 1px solid var(--color-border); }
.user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--transition-fast);
}
.user-chip:hover { background: var(--color-surface-hover); }
.user-avatar {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: 50%;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206; display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.user-avatar-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.user-name {
  flex: 1; min-width: 0; font-size: 13.5px; font-weight: 600;
  line-height: 1.6;
  color: var(--color-text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.user-caret { color: var(--color-text-muted); flex-shrink: 0; }

.main { flex: 1; display: flex; flex-direction: column; min-width: 0; }

.content { flex: 1; overflow-y: auto; padding: 20px; }

.fade-enter-active, .fade-leave-active { transition: opacity .18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
