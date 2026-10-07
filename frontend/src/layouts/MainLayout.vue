<template>
  <div class="layout" :class="{ collapsed }">
    <!-- 左侧边栏：可折叠，折叠后仅显示图标 -->
    <aside class="sidebar" :class="{ collapsed: collapsed }">
      <div class="brand">
        <div class="brand-logo">PA</div>
        <div v-show="!collapsed" class="brand-text">
          <div class="brand-title">个人全能助手</div>
          <div class="brand-sub">Personal Assistant</div>
        </div>
      </div>

      <nav class="nav">
        <el-tooltip
          v-for="item in navItems"
          :key="item.path"
          :content="item.title"
          placement="right"
          :disabled="!collapsed"
        >
          <router-link
            :to="item.path"
            class="nav-item"
            :class="{ active: isActive(item.path) }"
          >
            <el-icon :size="19"><component :is="item.icon" /></el-icon>
            <span v-show="!collapsed" class="nav-label">{{ item.label }}</span>
          </router-link>
        </el-tooltip>
      </nav>

      <div class="sidebar-foot">
        <el-dropdown trigger="click" placement="top-start" @command="onUserCommand">
          <div class="user-chip">
            <div class="user-avatar">
              <img v-if="auth.user?.avatar" :src="auth.user.avatar" class="user-avatar-img" alt="" />
              <el-icon v-else :size="17"><User /></el-icon>
            </div>
            <span v-show="!collapsed" class="user-name">{{ auth.user?.username || '未登录' }}</span>
            <el-icon v-show="!collapsed" class="user-caret" :size="13"><ArrowUp /></el-icon>
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

      <!-- 拉手式折叠开关：锚定侧边栏右缘，宽度过渡时随右缘同步移动，两态相对位置恒定不跳变 -->
      <div
        class="collapse-handle"
        :title="collapsed ? '展开菜单' : '折叠菜单'"
        @click="toggleCollapse"
      >
        <el-icon :size="13"><component :is="collapsed ? 'Right' : 'Left'" /></el-icon>
      </div>
    </aside>

    <!-- 右侧主区 -->
    <div class="main">
      <main class="content pa-scroll">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" @open-settings="onOpenSettings" />
          </transition>
        </router-view>
      </main>
    </div>

    <SettingsDialog v-model="showSettings" :focus-tab="settingsFocusTab" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SettingsDialog from '@/components/SettingsDialog.vue'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const showSettings = ref(false)
const settingsFocusTab = ref('')
// 侧边栏折叠状态（localStorage 记忆）
const collapsed = ref(localStorage.getItem('sidebar_collapsed') === '1')
function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('sidebar_collapsed', collapsed.value ? '1' : '0')
}

function onOpenSettings(tab?: string) {
  settingsFocusTab.value = tab || ''
  showSettings.value = true
}

const navItems = [
  { path: '/', label: '日历与任务', icon: 'Calendar', title: '日历与任务' },
  { path: '/report', label: 'AI 周报', icon: 'Document', title: 'AI 周报' },
  { path: '/assistant', label: 'AI 助手', icon: 'ChatDotRound', title: 'AI 助手' },
  { path: '/weather', label: '天气', icon: 'Sunny', title: '天气' },
  { path: '/butler', label: '工具箱', icon: 'Tools', title: '工具箱' }
]

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
.layout { display: flex; width: 100%; height: 100%; overflow: hidden; position: relative; }

.sidebar {
  width: var(--sidebar-width);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  transition: width .25s ease;
  position: relative;
}
.sidebar.collapsed { width: 64px; }

.brand {
  display: flex;
  align-items: center;
  gap: 11px;
  /* 左内衬 13 使 logo 中心 x=32，与导航图标/用户头像中心线对齐，两态位置恒定 */
  padding: 18px 18px 16px 13px;
  border-bottom: 1px solid var(--color-border);
  /* 固定高度+裁剪：折叠过渡中标题不换行、不撑高，杜绝高度跳变 */
  height: 72px; box-sizing: border-box; overflow: hidden;
}
.brand-logo {
  width: 38px; height: 38px; flex-shrink: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-dark));
  color: #1a1206; font-weight: 800; font-size: 15px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 14px rgba(245, 158, 11, .35);
}
.brand-title { font-size: 15px; font-weight: 700; color: var(--color-text-primary); line-height: 1.2; white-space: nowrap; }
.brand-sub { font-size: 10.5px; color: var(--color-text-muted); margin-top: 3px; letter-spacing: .3px; white-space: nowrap; }
/* 拉手式折叠开关：贴侧边栏右缘垂直居中，外侧圆角；
   以 right:0 锚定右缘，宽度过渡时自然随右缘同步移动，展开/折叠两态相对边缘位置恒定，无跳变 */
.collapse-handle {
  position: absolute; top: 50%; right: 0; transform: translateY(-50%);
  width: 18px; height: 56px; z-index: 5;
  display: flex; align-items: center; justify-content: center;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border); border-right: none;
  border-radius: 8px 0 0 8px;
  color: var(--color-text-muted); cursor: pointer;
  transition: color .15s, background .15s;
}
.collapse-handle:hover { color: var(--color-text-primary); background: var(--color-surface-hover); }
/* 折叠态：品牌区纵排居中仅留 logo；logo 中心仍为 x=32、垂直居中，与展开态同位 */
.sidebar.collapsed .brand { flex-direction: column; justify-content: center; gap: 0; padding: 0; }

/* 两态共用内衬 8 + 条目内衬 14：图标中心 x≈32 恒定，折叠时不换位置 */
.nav { flex: 1; padding: 12px 8px; display: flex; flex-direction: column; gap: 4px; overflow-y: auto; }
.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 14px; border-radius: var(--radius-sm);
  color: var(--color-text-secondary); text-decoration: none;
  font-size: 14px; font-weight: 500;
  transition: all var(--transition-fast);
  position: relative;
  /* 折叠过渡中裁剪而非换行：条目高度恒定不跳跃 */
  overflow: hidden;
}
/* 导航文字禁止换行：过渡中间宽度下横向裁剪，不竖排撑高 */
.nav-label { white-space: nowrap; }
.nav-item:hover { background: var(--color-surface-hover); color: var(--color-text-primary); }
.nav-item.active {
  background: linear-gradient(90deg, rgba(245,158,11,.16), rgba(245,158,11,.04));
  color: var(--color-primary-light);
}
.nav-item.active::before {
  content: ''; position: absolute; left: 0; top: 50%; transform: translateY(-50%);
  width: 3px; height: 20px; border-radius: 0 3px 3px 0; background: var(--color-primary);
}

/* 头像中心 x=32 两态恒定（8+8+16），折叠时不换位置 */
.sidebar-foot { padding: 10px 8px; border-top: 1px solid var(--color-border); }
.user-chip {
  display: flex; align-items: center; gap: 10px;
  padding: 8px; border-radius: var(--radius-sm);
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
