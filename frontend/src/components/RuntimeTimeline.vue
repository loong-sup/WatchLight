<template>
  <section class="timeline">
    <div class="section-head">
      <div>
        <p class="eyebrow">LIVE TRACE</p>
        <h3>{{ runtime.activeRun?.title || '暂无运行' }}</h3>
      </div>
      <div class="trace-summary">
        <span v-if="runtime.activeRun" :class="['run-badge', runtime.activeRun.status]">
          {{ statusLabel(runtime.activeRun.status) }}
        </span>
        <span class="session-key">{{ runtime.activeRun?.sessionKey || '-' }}</span>
      </div>
    </div>

    <div v-if="runtime.activeRun" class="conversation">
      <article class="bubble user">
        <div class="bubble-label"><span>01</span> 用户输入</div>
        <p>{{ runtime.activeRun.input || '等待消息进入。' }}</p>
      </article>

      <div v-if="runtime.activeRun.tools.length" class="tool-strip">
        <article v-for="tool in runtime.activeRun.tools" :key="tool.id" class="tool-card">
          <div class="tool-top">
            <span :class="['tool-dot', tool.status]"></span>
            <strong>{{ tool.name }}</strong>
            <em>{{ toolStatus(tool.status) }}</em>
          </div>
          <p>{{ toolBrief(tool.result, tool.params) }}</p>
          <a v-if="toolUrl(tool.result)" :href="toolUrl(tool.result)" target="_blank" rel="noreferrer">
            打开文档链接
          </a>
        </article>
      </div>

      <article class="bubble assistant">
        <div class="bubble-label"><span>02</span> 模型输出 · 流式</div>
        <MarkdownContent :content="runtime.activeRun.output || '等待模型输出。'" />
      </article>
      <article v-if="runtime.activeRun.replyText" class="bubble reply">
        <div class="bubble-label"><span>03</span> 通道回写</div>
        <MarkdownContent :content="runtime.activeRun.replyText" />
      </article>
    </div>

    <div class="event-heading">
      <div><span class="pulse-icon" aria-hidden="true"></span><strong>底层事件</strong></div>
      <span>{{ runtime.activeEvents.length }} EVENTS</span>
    </div>
    <div class="event-list">
      <article
        v-for="(event, index) in runtime.activeEvents"
        :key="eventKey(event, index)"
        :class="['event-row', event.status]"
      >
        <div class="event-marker">
          <i aria-hidden="true"></i>
          <span>{{ event.layer }}</span>
        </div>
        <div class="event-body">
          <div class="event-top">
            <strong>{{ eventTitle(event) }}</strong>
            <time>{{ formatTime(event.ts) }}</time>
          </div>
          <p v-if="eventDetail(event)">{{ eventDetail(event) }}</p>
        </div>
      </article>
    </div>

    <div v-if="!runtime.activeEvents.length" class="empty">暂无事件。</div>
  </section>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'
import MarkdownContent from '@/components/MarkdownContent.vue'
import type { RuntimeEventPayload, RuntimeStatus } from '@/api/types'

const runtime = useRuntimeStore()

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}

function eventTitle(event: RuntimeEventPayload) {
  const labels: Record<string, string> = {
    'runtime.channel.inbound': '收到消息',
    'runtime.session.loaded': '读取会话',
    'runtime.run.started': '开始运行',
    'runtime.messages.initial': '组装初始上下文',
    'runtime.model.streaming': '模型流式输出',
    'runtime.usage': 'Token 用量',
    'runtime.tool.started': '开始调用工具',
    'runtime.tool.finished': '工具返回结果',
    'runtime.run.completed': '运行完成',
    'runtime.run.failed': '运行失败',
    'runtime.channel.reply_sent': '回复已发送',
    'runtime.channel.reply_failed': '回复发送失败',
  }
  return labels[event.type] || event.title
}

function eventDetail(event: RuntimeEventPayload) {
  if (event.type === 'runtime.model.streaming') {
    const chars = String(event.detail || '').length
    return chars ? `已输出 ${chars} 个字符，可见回复在上方持续更新。` : ''
  }
  if (event.type === 'runtime.tool.started') {
    const params = asRecord(event.data?.params)
    const title = typeof params?.title === 'string' ? `，标题《${params.title}》` : ''
    return `${event.detail || event.data?.tool || '工具'} 已开始${title}。`
  }
  if (event.type === 'runtime.tool.finished') {
    return toolBrief(event.data?.result, event.data?.params)
  }
  return event.detail || ''
}

function eventKey(event: RuntimeEventPayload, index: number) {
  if (event.type === 'runtime.model.streaming') {
    return `${event.runId || event.sessionKey}:model-stream`
  }
  return `${event.ts}-${event.type}-${event.layer}-${index}`
}

function toolStatus(status: RuntimeStatus) {
  const labels: Record<RuntimeStatus, string> = {
    idle: '等待',
    active: '调用中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function statusLabel(status: RuntimeStatus) {
  const labels: Record<RuntimeStatus, string> = {
    idle: '等待',
    active: '运行中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status]
}

function parseJsonish(value: unknown): unknown {
  if (typeof value !== 'string') return value
  const trimmed = value.trim()
  if (!trimmed) return ''
  try {
    return JSON.parse(trimmed)
  } catch {
    return value
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function toolBrief(result: unknown, params: unknown) {
  const parsed = asRecord(parseJsonish(result))
  if (parsed) {
    const title = typeof parsed.title === 'string' ? `《${parsed.title}》` : ''
    const blocks = typeof parsed.blocks_created === 'number' ? `，写入 ${parsed.blocks_created} 个块` : ''
    const reply = typeof parsed.reply_text === 'string' ? parsed.reply_text.split('\n')[0] : ''
    return reply || `工具已返回${title}${blocks}。`
  }
  const parsedParams = asRecord(params)
  if (parsedParams && typeof parsedParams.title === 'string') {
    return `准备处理《${parsedParams.title}》。`
  }
  return result ? '工具已返回结果。' : '等待工具结果。'
}

function toolUrl(result: unknown) {
  const parsed = asRecord(parseJsonish(result))
  if (parsed && typeof parsed.url === 'string') return parsed.url
  if (typeof result !== 'string') return ''
  return result.match(/https?:\/\/\S+/)?.[0] || ''
}
</script>

<style scoped>
.timeline {
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: end;
  gap: 18px;
  padding: 19px 20px 16px;
  border-bottom: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.86);
}
.eyebrow {
  margin: 0 0 7px;
  font: 750 9px/1 var(--mono);
  letter-spacing: 0.08em;
  color: var(--accent);
}
h3 {
  max-width: 640px;
  margin: 0;
  overflow: hidden;
  color: var(--text-strong);
  font-size: 18px;
  font-weight: 680;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.trace-summary { min-width: 0; display: flex; align-items: center; gap: 9px; }
.run-badge { padding: 5px 8px; border-radius: 99px; color: var(--muted); background: var(--bg-subtle); font: 700 9px/1 var(--mono); white-space: nowrap; }
.run-badge.active { color: var(--accent); background: var(--accent-soft); }
.run-badge.done { color: var(--green); background: var(--green-soft); }
.run-badge.failed { color: var(--red); background: var(--red-soft); }
.session-key {
  color: var(--muted);
  font: 600 11px/1.4 var(--mono);
  max-width: 42%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-list {
  padding: 0 20px 24px;
}
.conversation {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 12px;
  padding: 18px 20px 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
}
.bubble {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  padding: 13px 14px;
  box-shadow: var(--shadow-sm);
}
.bubble.user {
  border-left: 3px solid #8992a8;
}
.bubble.assistant {
  border-left: 3px solid var(--accent);
}
.bubble.reply {
  border-left: 3px solid var(--green);
}
.tool-strip {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.tool-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #f9faff, #fff);
  padding: 12px 13px;
  box-shadow: var(--shadow-sm);
}
.tool-top {
  display: grid;
  grid-template-columns: 8px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}
.tool-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--muted);
}
.tool-dot.active {
  background: var(--accent);
}
.tool-dot.done {
  background: var(--green);
}
.tool-dot.failed {
  background: var(--red);
}
.tool-top strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}
.tool-top em {
  color: var(--muted);
  font: normal 700 10px/1 var(--mono);
}
.tool-card p {
  margin: 8px 0 0;
  color: #374151;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.tool-card a {
  display: inline-block;
  margin-top: 8px;
  color: var(--accent);
  font-size: 12px;
  text-decoration: none;
  border-bottom: 1px solid currentColor;
}
.bubble-label {
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  margin-bottom: 9px;
  letter-spacing: 0.03em;
}
.bubble-label span { display: inline-grid; place-items: center; width: 19px; height: 19px; margin-right: 6px; border-radius: 6px; color: var(--accent); background: var(--accent-soft); }
.bubble.user > p {
  margin: 0;
  color: #111827;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.event-row {
  display: grid;
  grid-template-columns: 96px minmax(0, 1fr);
  gap: 12px;
  padding: 0;
  position: relative;
}
.event-heading { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px 13px; color: var(--muted); font: 700 9px/1 var(--mono); }
.event-heading > div { display: flex; align-items: center; gap: 8px; }
.event-heading strong { color: var(--text); font-size: 11px; }
.pulse-icon { width: 7px; height: 7px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 4px var(--accent-soft); }
.event-marker { position: relative; min-height: 64px; padding-top: 12px; padding-left: 20px; }
.event-marker::before { content: ''; position: absolute; top: 0; bottom: 0; left: 5px; width: 1px; background: var(--border); }
.event-row:first-child .event-marker::before { top: 19px; }
.event-row:last-child .event-marker::before { bottom: calc(100% - 20px); }
.event-marker i { position: absolute; z-index: 1; top: 17px; left: 1px; width: 9px; height: 9px; border: 2px solid var(--surface); border-radius: 50%; background: var(--muted-soft); box-shadow: 0 0 0 1px var(--border-strong); }
.event-marker span {
  display: inline-block;
  width: auto;
  padding: 4px 7px;
  border: 0;
  border-radius: 5px;
  background: var(--bg-subtle);
  font: 700 9px/1 var(--mono);
  color: var(--muted);
}
.event-row.active .event-marker span {
  color: var(--accent);
  background: var(--accent-soft);
}
.event-row.active .event-marker i { background: var(--accent); box-shadow: 0 0 0 1px var(--accent), 0 0 0 5px var(--accent-soft); }
.event-row.done .event-marker span {
  color: var(--green);
  background: var(--green-soft);
}
.event-row.done .event-marker i { background: var(--green); }
.event-row.failed .event-marker span {
  color: var(--red);
  background: var(--red-soft);
}
.event-row.failed .event-marker i { background: var(--red); }
.event-body { min-width: 0; min-height: 64px; padding: 12px 0; border-bottom: 1px solid var(--border); }
.event-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
}
.event-top strong {
  color: var(--text-strong);
  font-size: 12px;
}
.event-top time {
  color: var(--muted);
  font: 600 10px/1 var(--mono);
}
p {
  margin-top: 6px;
  color: #4b5563;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
.empty {
  margin: 18px 20px 24px;
  padding: 28px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  color: var(--muted);
  text-align: center;
}
@media (max-width: 640px) {
  .section-head { align-items: flex-start; flex-direction: column; }
  .trace-summary { width: 100%; }
  .session-key { max-width: none; }
  .event-row { grid-template-columns: 82px minmax(0, 1fr); }
}
</style>
