import api from './api'
import type { AuthResponse, LoginRequest, RegisterRequest, User } from '../types/auth'

export const authService = {
  async register(req: RegisterRequest): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/api/v1/auth/register', req)
    return data
  },

  async login(req: LoginRequest): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/api/v1/auth/login', req)
    return data
  },

  async logout(refreshToken: string): Promise<void> {
    await api.post('/api/v1/auth/logout', { refresh_token: refreshToken })
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>('/api/v1/auth/me')
    return data
  },
}
