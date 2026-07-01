import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000',
  timeout: 120_000,
  headers: { 'Content-Type': 'application/json' },
})

// Unwrap FastAPI's { detail: "..." } error messages
api.interceptors.response.use(
  (res) => res,
  (error) => {
    const detail = error.response?.data?.detail
    const message =
      typeof detail === 'string'
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg: string }) => d.msg).join('; ')
          : error.message ?? 'Unknown error'
    return Promise.reject(new Error(message))
  },
)

export default api
