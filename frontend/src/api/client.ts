import axios from 'axios'
import { ElMessage } from 'element-plus'

export const TOKEN_KEY = 'pa_token'

// 开发态经 vite 代理到 8765；生产态与后端同源，直接用相对 /api
const client = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求携带 Bearer Token
client.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (resp) => resp,
  (error) => {
    const status = error?.response?.status
    const url: string = error?.config?.url || ''
    // 登录接口自身的 401 是“密码错误”，不跳转；其余 401 视为会话失效
    if (status === 401 && !url.includes('/auth/login')) {
      localStorage.removeItem(TOKEN_KEY)
      if (!location.hash.startsWith('#/login')) location.hash = '#/login'
    }
    const detail = error?.response?.data?.detail
    let msg = '请求失败'
    if (typeof detail === 'string') msg = detail
    else if (Array.isArray(detail)) msg = detail.map((d: any) => d.msg).join('; ')
    else if (detail) msg = JSON.stringify(detail)
    else if (error.message) msg = error.message
    if (status !== 409) {
      ElMessage.error(msg)
    }
    return Promise.reject(new Error(msg))
  }
)

export default client
