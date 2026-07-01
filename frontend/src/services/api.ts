import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE,
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request: attach Bearer token ───────────────────────────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// ── 401 refresh queue (prevents simultaneous refresh races) ───────────────────
type QueueEntry = { resolve: (token: string) => void; reject: (err: Error) => void }
let isRefreshing = false
let failedQueue: QueueEntry[] = []

function flushQueue(token: string | null, err: Error | null) {
  failedQueue.forEach((entry) => (token ? entry.resolve(token) : entry.reject(err!)))
  failedQueue = []
}

function clearSession() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user')
}

// ── Response: unwrap SuccessResponse envelope + 401 auto-refresh ───────────────
api.interceptors.response.use(
  (res) => {
    // Transparent unwrap: { success: true, data: T } → T
    if (res.data && typeof res.data === 'object' && res.data.success === true) {
      res.data = res.data.data
    }
    return res
  },
  async (error) => {
    const original = error.config

    // 401 handling — try refresh once per request
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (!refreshToken) {
        clearSession()
        window.location.href = '/login'
        return Promise.reject(new Error('Session expired. Please log in.'))
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then((newToken) => {
          original.headers.Authorization = `Bearer ${newToken}`
          return api(original)
        })
      }

      isRefreshing = true
      try {
        const { data } = await axios.post(`${BASE}/api/v1/auth/refresh`, {
          refresh_token: refreshToken,
        })
        // Response comes back as SuccessResponse — data.data is TokenPair
        const tokens = data?.data ?? data
        const newAccess: string = tokens.access_token
        const newRefresh: string = tokens.refresh_token
        localStorage.setItem('access_token', newAccess)
        localStorage.setItem('refresh_token', newRefresh)
        original.headers.Authorization = `Bearer ${newAccess}`
        flushQueue(newAccess, null)
        return api(original)
      } catch {
        flushQueue(null, new Error('Session expired'))
        clearSession()
        window.location.href = '/login'
        return Promise.reject(new Error('Session expired. Please log in again.'))
      } finally {
        isRefreshing = false
      }
    }

    // Extract message from our ErrorResponse or legacy FastAPI detail
    const resData = error.response?.data
    const message =
      resData?.message ??
      (typeof resData?.detail === 'string'
        ? resData.detail
        : Array.isArray(resData?.detail)
          ? resData.detail.map((d: { msg: string }) => d.msg).join('; ')
          : null) ??
      error.message ??
      'Unknown error'

    return Promise.reject(new Error(message))
  },
)

export default api
