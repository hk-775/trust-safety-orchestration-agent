import { api } from './api'

type MessageHandler = (data: unknown) => void

const WS_URL = import.meta.env.VITE_WS_URL || ''

export function createWebSocketClient(
  onMessage: MessageHandler,
  webSocketUrl = WS_URL,
) {
  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectDelay = 1000
  let connecting = false
  let stopped = true

  async function connect() {
    stopped = false
    if (!webSocketUrl || ws || connecting) return
    connecting = true

    try {
      const { ticket } = await api.post<{ ticket: string; expires_at: number }>(
        '/auth/websocket-ticket',
        {},
      )
      if (stopped) return

      const url = new URL(webSocketUrl)
      url.searchParams.set('ticket', ticket)
      ws = new WebSocket(url.toString())

      ws.onopen = () => {
        reconnectDelay = 1000
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          onMessage(data)
        } catch {
          // Ignore non-JSON messages.
        }
      }

      ws.onclose = () => {
        ws = null
        if (!stopped) scheduleReconnect()
      }

      ws.onerror = () => {
        ws?.close()
      }
    } catch (error) {
      if (
        typeof error === 'object'
        && error !== null
        && 'status' in error
        && (error.status === 401 || error.status === 403)
      ) {
        stopped = true
        return
      }
      if (!stopped) scheduleReconnect()
    } finally {
      connecting = false
    }
  }

  function scheduleReconnect() {
    if (stopped || reconnectTimer) return
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null
      void connect()
      reconnectDelay = Math.min(reconnectDelay * 2, 30000)
    }, reconnectDelay)
  }

  function disconnect() {
    stopped = true
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    const currentSocket = ws
    ws = null
    currentSocket?.close()
  }

  return { connect, disconnect }
}
