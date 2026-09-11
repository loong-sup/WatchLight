import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { api } from '@/api/http'
import { gateway } from '@/api/gateway'
import type {
  ChannelStatus,
  LayerId,
  ModelInfo,
  RunTrace,
  RuntimeEventPayload,
  RuntimeMessage,
  RuntimeStatus,
  SessionEntry,
  ToolCallTrace,
} from '@/api/types'

export const ARCHITECTURE_LAYERS: { id: LayerId; label: string; detail: string }[] = [
  { id: 'channel', label: '通道层', detail: 'Feishu / WebChat 入口' },
  { id: 'gateway', label: 'Gateway', detail: '路由与运行准备' },
  { id: 'session', label: '会话层', detail: '状态与 transcript' },
  { id: 'runtime', label: 'Runtime', detail: '消息循环' },
  { id: 'provider', label: 'Provider', detail: '模型流式输出' },
  { id: 'tools', label: '工具层', detail: '策略与执行' },
  { id: 'reply', label: '回复层', detail: '通道回写' },
]

const emptyLayerStatus = (): Record<LayerId, RuntimeStatus> => ({
  channel: 'idle',
  gateway: 'idle',
  session: 'idle',
  runtime: 'idle',
  provider: 'idle',
  tools: 'idle',
  reply: 'idle',
})

const fallbackRunId = (event: RuntimeEventPayload) =>
  event.runId || `pending:${event.sessionKey || 'unknown'}`

const eventSummary = (event: RuntimeEventPayload) =>
  event.detail || event.title || event.type.replace(/^runtime\./, '')

const MODEL_STREAM_EVENT = 'runtime.model.streaming'

function getMessages(data: Record<string, unknown> | undefined): RuntimeMessage[] {
  // 并不是每个运行事件都会带 messages 快照；没有快照时直接返回空列表。
  const value = data?.messages
  return Array.isArray(value) ? (value as RuntimeMessage[]) : []
}

function normalizeStatus(status: RuntimeStatus | undefined): RuntimeStatus {
  return status || 'active'
}

function tokenValue(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

function sessionRuntimeStatus(status: string | undefined): RuntimeStatus {
  if (status === 'running') return 'active'
  if (status === 'failed') return 'failed'
  return 'done'
}

function messageText(message: RuntimeMessage | undefined): string {
  return typeof message?.content === 'string' ? message.content : ''
}

function historicalRun(session: SessionEntry, messages: RuntimeMessage[]): RunTrace {
  const lastUser = [...messages].reverse().find((message) => message.role === 'user')
  const lastAssistant = [...messages].reverse().find((message) => message.role === 'assistant')
  const totalTokens = tokenValue(session.totalTokens)
    || tokenValue(session.inputTokens) + tokenValue(session.outputTokens)
  return {
    id: `history:${session.key}`,
    sessionKey: session.key,
    channel: session.channel || session.lastChannel || '',
    title: session.label || messageText(lastUser) || session.key,
    status: sessionRuntimeStatus(session.status),
    startedAt: tokenValue(messages[0]?.ts) || session.updatedAt,
    updatedAt: session.updatedAt,
    model: session.model,
    input: messageText(lastUser),
    output: messageText(lastAssistant),
    inputTokens: tokenValue(session.inputTokens),
    outputTokens: tokenValue(session.outputTokens),
    totalTokens,
    usageScope: 'session',
    archivedAt: session.archivedAt,
    initialMessages: messages,
    currentMessages: messages,
    tools: [],
    events: [],
    layerStatus: emptyLayerStatus(),
  }
}

function parseToolResult(result: unknown): unknown {
  if (typeof result !== 'string') return result
  const trimmed = result.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return result
  }
}

function replyTextFromToolResult(result: unknown) {
  // 工具可通过 reply_text 指定最终可见回复，例如文档工具只展示文档链接。
  const parsed = parseToolResult(result)
  if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) return ''
  const replyText = (parsed as Record<string, unknown>).reply_text
  return typeof replyText === 'string' ? replyText.trim() : ''
}

export const useRuntimeStore = defineStore('runtime', () => {
  const wsStatus = ref('disconnected')
  const sendStatus = ref('')
  const runs = ref<RunTrace[]>([])
  const activeRunId = ref('')
  const sessions = ref<SessionEntry[]>([])
  const channels = ref<ChannelStatus[]>([])
  const models = ref<ModelInfo[]>([])
  const draft = ref('')
  const connectedOnce = ref(false)
  const showArchived = ref(false)

  const activeRun = computed(() => runs.value.find((run) => run.id === activeRunId.value))
  const activeEvents = computed(() => activeRun.value?.events || [])
  const visibleRuns = computed(() => runs.value.filter((run) => (
    showArchived.value ? Boolean(run.archivedAt) : !run.archivedAt
  )))
  const activeMessages = computed(() => {
    const run = activeRun.value
    if (!run) return []
    return run.currentMessages.length ? run.currentMessages : run.initialMessages
  })

  async function connect() {
    if (!connectedOnce.value) {
      gateway.onStatus((status) => {
        wsStatus.value = status
      })
      gateway.on('runtime.event', handleRuntimeEvent)
      gateway.on('agent.event', handleAgentEvent)
      connectedOnce.value = true
    }
    await gateway.connect()
  }

  async function loadSnapshot() {
    // REST 摘要可独立加载；WebSocket 不可用时仍展示会话，只是暂时没有 transcript 内容。
    await connect().catch(() => undefined)
    const [sessionData, channelData, modelData] = await Promise.allSettled([
      api.getSessions(),
      api.getChannelStatus(),
      api.getModels(),
    ])
    if (sessionData.status === 'fulfilled') {
      sessions.value = sessionData.value.sessions || []
      const restored = await Promise.all(
        sessions.value.map(async (session) => {
          try {
            const preview = await gateway.send('sessions.preview', {
              sessionKey: session.key,
              limit: 200,
            })
            const messages = Array.isArray(preview?.messages)
              ? (preview.messages as RuntimeMessage[])
              : []
            return historicalRun(session, messages)
          } catch {
            // 即使单个 transcript 损坏，会话摘要仍然可以出现在列表中。
            return historicalRun(session, [])
          }
        }),
      )
      const liveRuns = runs.value.filter((run) => !run.id.startsWith('history:'))
      const liveSessionKeys = new Set(liveRuns.map((run) => run.sessionKey))
      runs.value = [...liveRuns, ...restored.filter((run) => !liveSessionKeys.has(run.sessionKey))]
        .sort((a, b) => b.updatedAt - a.updatedAt)
        .slice(0, 100)
      if (!visibleRuns.value.some((run) => run.id === activeRunId.value)) {
        activeRunId.value = visibleRuns.value[0]?.id || ''
      }
    }
    if (channelData.status === 'fulfilled') channels.value = channelData.value.channels || []
    if (modelData.status === 'fulfilled') models.value = modelData.value.models || []
  }

  async function sendLocalMessage() {
    const text = draft.value.trim()
    if (!text) return
    await connect()
    sendStatus.value = '发送中'
    draft.value = ''
    try {
      const response = await gateway.send('sessions.send', {
        sessionKey: 'web:local',
        message: text,
      })
      const completedRun = runs.value.find(
        (run) => run.sessionKey === 'web:local' && !run.id.startsWith('history:'),
      )
      if (completedRun) {
        completedRun.inputTokens = tokenValue(response?.inputTokens)
        completedRun.outputTokens = tokenValue(response?.outputTokens)
        completedRun.totalTokens = completedRun.inputTokens + completedRun.outputTokens
      }
      sendStatus.value = '已发送'
      await loadSnapshot()
    } catch (error) {
      sendStatus.value = error instanceof Error ? error.message : '发送失败'
    }
  }

  function handleAgentEvent(payload: any) {
    if (!payload || payload.type !== 'text_delta') return
    const run = activeRun.value
    // 如果后端已经发结构化 runtime.model.delta，就不用再消费旧的 agent.event 文本流。
    if (!run || run.events.some((event) => event.type === MODEL_STREAM_EVENT)) return
    run.output += String(payload.text || '')
    run.updatedAt = Date.now()
  }

  function handleRuntimeEvent(event: RuntimeEventPayload) {
    if (!event || !event.type || !event.sessionKey) return
    const run = ensureRun(event)
    run.updatedAt = event.ts || Date.now()
    run.status = event.type === 'runtime.run.completed' ? event.status : run.status
    run.layerStatus[event.layer] = normalizeStatus(event.status)

    if (event.type !== 'runtime.model.delta') {
      // 模型 delta 很密集，折叠成一条“模型流式输出”事件，避免时间线被刷屏。
      run.events.push(event)
    }

    if (event.type === 'runtime.channel.inbound') {
      run.channel = String(event.data?.channel || run.channel || '')
      run.input = String(event.data?.message || event.detail || '')
      run.title = run.input || run.title
    }

    if (event.type === 'runtime.run.started') {
      run.channel = String(event.data?.channel || run.channel || '')
      run.provider = String(event.data?.provider || '')
      run.model = String(event.data?.model || '')
      run.status = 'active'
      run.layerStatus.gateway = 'done'
      // 入站事件可能先于 run id 到达，需要把 pending 事件合并到真实 run 上。
      mergePendingEvents(run)
    }

    if (event.type === 'runtime.messages.initial') {
      const messages = getMessages(event.data)
      run.initialMessages = messages
      run.currentMessages = messages
      run.layerStatus.runtime = 'active'
    }

    if (event.type === 'runtime.model.delta') {
      const text = String(event.data?.text || event.detail || '')
      run.output += text
      run.layerStatus.provider = 'active'
      upsertModelStreamEvent(run, event)
    }

    if (event.type === 'runtime.usage') {
      run.inputTokens += tokenValue(event.data?.inputTokens)
      run.outputTokens += tokenValue(event.data?.outputTokens)
      run.totalTokens = run.inputTokens + run.outputTokens
    }

    if (event.type === 'runtime.tool.started') {
      const name = String(event.data?.tool || 'tool')
      run.tools.push({
        id: `${event.ts}-${name}`,
        name,
        status: 'active',
        params: event.data?.params,
        startedAt: event.ts,
      })
      run.layerStatus.tools = 'active'
    }

    if (event.type === 'runtime.tool.finished') {
      const name = String(event.data?.tool || 'tool')
      const result = event.data?.result
      const tool = [...run.tools].reverse().find((item) => item.name === name && item.status === 'active')
      if (tool) {
        tool.status = event.status
        tool.result = result
        tool.finishedAt = event.ts
      } else {
        run.tools.push({
          id: `${event.ts}-${name}`,
          name,
          status: event.status,
          result,
          finishedAt: event.ts,
        })
      }
      const preferredReply = replyTextFromToolResult(result)
      if (preferredReply) {
        // 文档工具返回后，工作台展示链接回复，而不是展示整篇文档正文。
        run.output = preferredReply
        run.replyText = preferredReply
      }
      const messages = getMessages(event.data)
      if (messages.length) run.currentMessages = messages
      run.layerStatus.tools = event.status
    }

    if (event.type === 'runtime.run.completed') {
      run.status = event.status
      run.output = String(event.data?.responseText || run.output)
      const messages = getMessages(event.data)
      if (messages.length) run.currentMessages = messages
      run.layerStatus.runtime = event.status
      run.layerStatus.provider = run.layerStatus.provider === 'active' ? 'done' : run.layerStatus.provider
      run.title = run.title || eventSummary(event)
      if (event.data) {
        run.inputTokens = tokenValue(event.data.inputTokens)
        run.outputTokens = tokenValue(event.data.outputTokens)
        run.totalTokens = run.inputTokens + run.outputTokens
      }
    }

    if (event.type === 'runtime.channel.reply_sent') {
      run.replyText = String(event.data?.text || event.detail || '')
      run.layerStatus.reply = 'done'
      run.status = run.status === 'active' ? 'done' : run.status
    }

    if (event.status === 'failed') {
      run.status = 'failed'
      run.layerStatus[event.layer] = 'failed'
    }

    activeRunId.value = run.id
    // 最新运行保持在最上方，同时限制最多 50 条，避免长时间打开页面后内存膨胀。
    runs.value = [
      run,
      ...runs.value.filter(
        (item) => item.id !== run.id
          && !(item.id.startsWith('history:') && item.sessionKey === run.sessionKey),
      ),
    ].slice(0, 100)
  }

  function upsertModelStreamEvent(run: RunTrace, event: RuntimeEventPayload) {
    const existing = run.events.find((item) => item.type === MODEL_STREAM_EVENT)
    const streamEvent = {
      ...event,
      type: MODEL_STREAM_EVENT,
      title: '模型流式输出',
      detail: run.output,
      status: 'active' as RuntimeStatus,
    }
    if (existing) {
      existing.detail = streamEvent.detail
      existing.ts = streamEvent.ts
      existing.status = streamEvent.status
      existing.data = {
        ...(existing.data || {}),
        text: run.output,
      }
    } else {
      run.events.push(streamEvent)
    }
  }

  function ensureRun(event: RuntimeEventPayload): RunTrace {
    const id = fallbackRunId(event)
    const existing = runs.value.find((run) => run.id === id)
    if (existing) return existing
    const run: RunTrace = {
      id,
      sessionKey: event.sessionKey,
      title: event.title || event.type,
      status: event.status === 'failed' ? 'failed' : 'active',
      startedAt: event.ts || Date.now(),
      updatedAt: event.ts || Date.now(),
      output: '',
      inputTokens: 0,
      outputTokens: 0,
      totalTokens: 0,
      usageScope: 'run',
      initialMessages: [],
      currentMessages: [],
      tools: [],
      events: [],
      layerStatus: emptyLayerStatus(),
    }
    runs.value.unshift(run)
    return run
  }

  function mergePendingEvents(run: RunTrace) {
    const pendingId = `pending:${run.sessionKey}`
    if (run.id === pendingId) return
    const pending = runs.value.find((item) => item.id === pendingId)
    if (!pending) return
    // 后端分配真实 run id 后，把之前按 sessionKey 暂存的入站上下文迁移过来。
    run.events = [...pending.events, ...run.events]
    run.input = run.input || pending.input
    run.title = run.input || run.title
    run.layerStatus.channel = pending.layerStatus.channel
    runs.value = runs.value.filter((item) => item.id !== pendingId)
  }

  function selectRun(id: string) {
    activeRunId.value = id
  }

  async function archiveSession(sessionKey: string, archived = true) {
    await connect()
    const result = await gateway.send('sessions.archive', { sessionKey, archived })
    if (!result?.ok) throw new Error(result?.error?.message || '会话归档失败')
    await loadSnapshot()
  }

  async function deleteSession(sessionKey: string) {
    await connect()
    const result = await gateway.send('sessions.delete', { sessionKey })
    if (!result?.ok) throw new Error(result?.error?.message || '会话删除失败')
    runs.value = runs.value.filter((run) => run.sessionKey !== sessionKey)
    sessions.value = sessions.value.filter((session) => session.key !== sessionKey)
    if (!runs.value.some((run) => run.id === activeRunId.value)) {
      activeRunId.value = visibleRuns.value[0]?.id || ''
    }
  }

  return {
    wsStatus,
    sendStatus,
    runs,
    activeRunId,
    activeRun,
    activeEvents,
    activeMessages,
    visibleRuns,
    sessions,
    channels,
    models,
    draft,
    showArchived,
    connect,
    loadSnapshot,
    sendLocalMessage,
    selectRun,
    archiveSession,
    deleteSession,
  }
})
