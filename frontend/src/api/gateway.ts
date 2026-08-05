export interface GatewayFrame {
  type: 'req' | 'res' | 'event'
  id?: string
  method?: string
  params?: any
  ok?: boolean
  payload?: any
  error?: any
  event?: string
  seq?: number
}

export class GatewayClient {
  private ws: WebSocket | null = null
  private connectPromise: Promise<any> | null = null
  private requestId = 0
  private pending = new Map<string, { resolve: (v: any) => void; reject: (e: any) => void }>()
  private eventHandlers = new Map<string, ((payload: any) => void)[]>()
  private statusHandlers: ((status: string) => void)[] = []

  connect(url = `ws://${location.host}/ws`): Promise<any> {
    if (this.ws?.readyState === WebSocket.OPEN) return Promise.resolve(true)
    if (this.connectPromise) return this.connectPromise

    this.connectPromise = new Promise((resolve, reject) => {
      this.ws = new WebSocket(url)
      this.ws.onopen = () => {
        this.emitStatus('handshake')
        this.send('connect', {
          minProtocol: 1, maxProtocol: 3,
          client: { id: 'web-admin', version: '0.1.0', platform: 'browser', mode: 'local' }
        }).then((payload) => {
          this.emitStatus('connected')
          resolve(payload)
        }).catch(reject)
      }
      this.ws.onmessage = (ev) => this.handleMessage(JSON.parse(ev.data))
      this.ws.onerror = () => {
        this.emitStatus('error')
        reject(new Error('WebSocket error'))
      }
      this.ws.onclose = () => {
        this.ws = null
        this.connectPromise = null
        this.emitStatus('disconnected')
      }
    })

    return this.connectPromise
  }

  async send(method: string, params: any = {}, timeoutMs = 180000): Promise<any> {
    if (!this.ws) throw new Error('Not connected')
    const id = `req-${++this.requestId}`
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject })
      this.ws!.send(JSON.stringify({ type: 'req', id, method, params }))
      setTimeout(() => {
        if (this.pending.has(id)) {
          this.pending.delete(id)
          reject(new Error('Request timeout'))
        }
      }, timeoutMs)
    })
  }

  on(event: string, handler: (payload: any) => void) {
    if (!this.eventHandlers.has(event)) this.eventHandlers.set(event, [])
    this.eventHandlers.get(event)!.push(handler)
  }

  off(event: string, handler: (payload: any) => void) {
    const handlers = this.eventHandlers.get(event) || []
    this.eventHandlers.set(event, handlers.filter((item) => item !== handler))
  }

  onStatus(handler: (status: string) => void) {
    this.statusHandlers.push(handler)
  }

  private handleMessage(frame: GatewayFrame) {
    if (frame.type === 'res' && frame.id) {
      const p = this.pending.get(frame.id)
      if (p) {
        this.pending.delete(frame.id)
        frame.ok ? p.resolve(frame.payload) : p.reject(frame.error)
      }
    } else if (frame.type === 'event' && frame.event) {
      const handlers = this.eventHandlers.get(frame.event) || []
      handlers.forEach(h => h(frame.payload))
    }
  }

  private emitStatus(status: string) {
    this.statusHandlers.forEach((handler) => handler(status))
  }

  disconnect() {
    this.ws?.close()
    this.ws = null
    this.connectPromise = null
  }
}

export const gateway = new GatewayClient()
