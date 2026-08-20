/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it } from 'vitest'

import { useAuthStore } from './authStore'


describe('authStore', () => {
  beforeEach(() => {
    useAuthStore.getState().logout()
  })

  it('keeps authentication in memory and clears it on logout', () => {
    const user = {
      id: 'reviewer-123',
      email: 'reviewer@example.com',
      role: 'reviewer' as const,
    }

    useAuthStore.getState().login('test-token', user)

    expect(useAuthStore.getState()).toMatchObject({
      token: 'test-token',
      user,
    })
    expect(sessionStorage.getItem('auth_token')).toBeNull()
    expect(sessionStorage.getItem('auth_user')).toBeNull()

    useAuthStore.getState().logout()

    expect(useAuthStore.getState()).toMatchObject({
      token: null,
      user: null,
    })
    expect(sessionStorage.getItem('auth_token')).toBeNull()
    expect(sessionStorage.getItem('auth_user')).toBeNull()
  })
})
