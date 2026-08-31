/** @vitest-environment jsdom */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, waitFor } from '@testing-library/react'

import App from './App'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/services/mockData', () => ({
  mockLogin: vi.fn(),
}))

describe('production authentication boundary', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
    window.history.replaceState({}, '', '/app')
  })

  afterEach(() => {
    cleanup()
    window.history.replaceState({}, '', '/')
  })

  it('redirects an unauthenticated dashboard request to sign in', async () => {
    render(<App />)

    await waitFor(() => {
      expect(window.location.pathname).toBe('/login')
    })
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeTruthy()
    expect(useAuthStore.getState().token).toBeNull()
    expect(useAuthStore.getState().user).toBeNull()
  })
})
