/** @vitest-environment jsdom */

import { beforeEach, describe, expect, it, vi } from 'vitest'

import { api } from './api'
import { createWebSocketClient } from './websocketClient'


vi.mock('./api', () => ({
  api: {
    post: vi.fn(),
  },
}))


class FakeWebSocket {
  static instances: FakeWebSocket[] = []

  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  onerror: (() => void) | null = null

  constructor(public url: string) {
    FakeWebSocket.instances.push(this)
  }

  close() {
    this.onclose?.()
  }
}


describe('websocketClient', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
  })

  it('exchanges the REST bearer token for a one-time WebSocket ticket', async () => {
    vi.mocked(api.post).mockResolvedValue({
      ticket: 'one-time-ticket',
      expires_at: 1060,
    })
    const client = createWebSocketClient(
      vi.fn(),
      'wss://socket.example.test/prod',
    )

    await client.connect()

    expect(api.post).toHaveBeenCalledWith('/auth/websocket-ticket', {})
    expect(FakeWebSocket.instances).toHaveLength(1)
    const url = new URL(FakeWebSocket.instances[0].url)
    expect(url.searchParams.get('ticket')).toBe('one-time-ticket')
    expect(url.searchParams.has('token')).toBe(false)

    client.disconnect()
  })
})
