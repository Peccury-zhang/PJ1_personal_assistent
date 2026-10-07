import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { title: '登录' }
  },
  {
    path: '/',
    component: MainLayout,
    children: [
      { path: '', name: 'calendar', component: () => import('@/views/CalendarView.vue'), meta: { title: '日历与任务' } },
      { path: 'profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { title: '个人中心' } },
      { path: 'report', name: 'report', component: () => import('@/views/ReportView.vue'), meta: { title: 'AI 周报' } },
      { path: 'assistant', name: 'assistant', component: () => import('@/views/AssistantView.vue'), meta: { title: 'AI 助手' } },
      { path: 'weather', name: 'weather', component: () => import('@/views/WeatherView.vue'), meta: { title: '天气' } },
      { path: 'butler', name: 'butler', component: () => import('@/views/ButlerView.vue'), meta: { title: '工具箱' } },
      { path: 'users', name: 'users', component: () => import('@/views/UsersView.vue'), meta: { title: '账户管理', requiresAdmin: true } }
    ]
  }
]

// 用 hash 模式：静态托管（FastAPI StaticFiles）下无需服务端路由回退配置
const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局鉴权守卫：未登录跳登录页；管理员页面校验等级
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.name === 'login') {
    if (auth.token && !auth.user) await auth.refresh()
    return auth.isAuthed ? { path: '/' } : true
  }
  if (!auth.token) return { name: 'login' }
  if (!auth.user) {
    const u = await auth.refresh()
    if (!u) return { name: 'login' }
  }
  if (to.meta?.requiresAdmin && !auth.isAdmin) return { path: '/' }
  return true
})

export default router
