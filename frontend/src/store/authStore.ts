import { create } from 'zustand'
import { IS_PUBLIC_SITE } from '@/lib/publicSite'

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

const PUBLIC_USER: AuthUser = {
  id: 'synthetic-reviewer',
  email: 'synthetic-reviewer@safetyagent.example',
  role: 'reviewer',
}

export const useAuthStore = create<AuthState>((set) => ({
  user: IS_PUBLIC_SITE ? PUBLIC_USER : null,
  token: IS_PUBLIC_SITE ? 'synthetic-public-demo' : null,
  login: (token, user) => set({ token, user }),
  logout: () => set(
    IS_PUBLIC_SITE
      ? { token: 'synthetic-public-demo', user: PUBLIC_USER }
      : { token: null, user: null },
  ),
}))
