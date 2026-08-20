import { create } from 'zustand'

interface AuthUser {
  id: string
  email: string
  role: 'admin' | 'operator' | 'reviewer'
}

interface AuthState {
  user: AuthUser | null
  token: string | null
  login: (token: string, user: AuthUser) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>((set) => ({
  user: (() => {
    const stored = sessionStorage.getItem('auth_user')
    return stored ? JSON.parse(stored) : null
  })(),
  token: sessionStorage.getItem('auth_token'),
  login: (token, user) => {
    sessionStorage.setItem('auth_token', token)
    sessionStorage.setItem('auth_user', JSON.stringify(user))
    set({ token, user })
  },
  logout: () => {
    sessionStorage.removeItem('auth_token')
    sessionStorage.removeItem('auth_user')
    set({ token: null, user: null })
  },
}))
