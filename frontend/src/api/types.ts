export interface SessionEntry {
  key: string
  sessionId?: string
  updatedAt: number
  channel?: string
  status?: string
  model?: string
  label?: string
  inputTokens?: number
  outputTokens?: number
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  ts?: number
}

export interface ChannelStatus {
  channel: string
  label: string
  chatTypes: string[]
}

export type LayerId =
  | 'channel'
  | 'gateway'
  | 'session'
  | 'runtime'
  | 'provider'
  | 'tools'
  | 'reply'

export type RuntimeStatus = 'idle' | 'active' | 'done' | 'failed'

export interface RuntimeMessage {
  role: string
  content?: string
  name?: string
  tool_call?: {
    name?: string
    params?: unknown
  }
  tool_calls?: unknown
  ts?: number
  [key: string]: unknown
}

export interface RuntimeEventPayload {
  type: string
  layer: LayerId
  status: RuntimeStatus
  title: string
  detail?: string
  sessionKey: string
  runId?: string | null
  ts: number
  data?: Record<string, unknown>
}

export interface ToolCallTrace {
  id: string
  name: string
  status: RuntimeStatus
  params?: unknown
  result?: unknown
  startedAt?: number
  finishedAt?: number
}

export interface RunTrace {
  id: string
  sessionKey: string
  channel?: string
  title: string
  status: RuntimeStatus
  startedAt: number
  updatedAt: number
  provider?: string
  model?: string
  input?: string
  output: string
  replyText?: string
  initialMessages: RuntimeMessage[]
  currentMessages: RuntimeMessage[]
  tools: ToolCallTrace[]
  events: RuntimeEventPayload[]
  layerStatus: Record<LayerId, RuntimeStatus>
}

export interface ModelInfo {
  id?: string
  model?: string
  provider?: string
  [key: string]: unknown
}
