import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api, TOKEN_KEY } from '@/api'
import type { AuthUser } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) || '')
  const user = ref<AuthUser | null>(null)

  const isAdmin = computed(() => user.value?.level === 'admin')
  const isAuthed = computed(() => !!token.value && !!user.value)

  async function login(username: string, password: string): Promise<AuthUser> {
    const r = await api.login(username, password)
    token.value = r.token
    localStorage.setItem(TOKEN_KEY, r.token)
    user.value = r.user
    return r.user
  }

  /** 启动时用已有 token 拉取当前用户；失败则清空会话 */
  async function refresh(): Promise<AuthUser | null> {
    if (!token.value) {
      user.value = null
      return null
    }
    try {
      user.value = await api.me()
      return user.value
    } catch {
      clear()
      return null
    }
  }

  function clear() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
  }

  async function logout() {
    try { await api.logout() } catch { /* 忽略 */ }
    clear()
  }

  /** 保存头像并同步到当前会话用户 */
  async function setAvatar(avatar: string): Promise<AuthUser | null> {
    if (!user.value) return null
    const updated = await api.setAvatar(user.value.id, avatar)
    user.value = updated
    return updated
  }

  return { token, user, isAdmin, isAuthed, login, refresh, logout, clear, setAvatar }
})
