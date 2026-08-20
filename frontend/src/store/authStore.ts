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
  user: null,
  token: null,
  login: (token, user) => set({ token, user }),
  logout: () => set({ token: null, user: null }),
}))
