<template>
  <aside class="run-list">
    <div class="panel-head">
      <div>
        <p class="eyebrow">LIVE SESSIONS</p>
        <h2>运行会话</h2>
      </div>
      <button class="refresh-btn" type="button" aria-label="刷新会话快照" @click="runtime.loadSnapshot">
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M20 11a8 8 0 1 0-2.35 5.65"></path>
          <path d="M20 5v6h-6"></path>
        </svg>
      </button>
    </div>

    <div class="meta-grid">
      <div>
        <span :class="['mini-orb', runtime.wsStatus]" aria-hidden="true"></span>
        <span class="meta-copy">
          <span class="meta-label">实时连接</span>
          <strong :class="['status-text', runtime.wsStatus]">{{ connectionLabel(runtime.wsStatus) }}</strong>
        </span>
      </div>
      <div>
        <span class="meta-number">{{ runtime.channels.length }}</span>
        <span class="meta-copy">
          <span class="meta-label">可用通道</span>
          <strong>{{ runtime.channels.length ? '服务就绪' : '等待加载' }}</strong>
        </span>
      </div>
    </div>

    <div class="list-label">
      <span>最近运行</span>
      <strong>{{ runtime.runs.length }}</strong>
    </div>

    <div class="runs">
      <button
        v-for="run in runtime.runs"
        :key="run.id"
        :class="['run-row', { active: run.id === runtime.activeRunId }]"
        @click="runtime.selectRun(run.id)"
      >
        <span :class="['run-icon', run.status]">
          <svg v-if="run.status === 'done'" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 8 2.4 2.4L12 5"></path></svg>
          <svg v-else-if="run.status === 'failed'" viewBox="0 0 16 16" aria-hidden="true"><path d="M5 5l6 6M11 5l-6 6"></path></svg>
          <span v-else></span>
        </span>
        <span class="run-main">
          <span class="run-title">{{ run.title || run.sessionKey }}</span>
          <span class="run-sub">
            <span>{{ run.channel || 'WebChat' }}</span>
            <i></i>
            <span>{{ run.model || '等待模型' }}</span>
          </span>
        </span>
        <span class="run-time">{{ formatTime(run.updatedAt) }}</span>
      </button>
    </div>

    <div v-if="!runtime.runs.length" class="empty">
      <span class="empty-beam" aria-hidden="true"></span>
      <strong>等待第一条消息</strong>
      <p>运行事件到达后，会话会出现在这里。</p>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()

function connectionLabel(status: string) {
  const labels: Record<string, string> = {
    connected: '已连接',
    handshake: '握手中',
    disconnected: '未连接',
    error: '异常',
  }
  return labels[status] || status
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}
</script>

<style scoped>
.run-list {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-raised);
  box-shadow: var(--shadow-sm);
  min-width: 0;
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
  display: flex;
  flex-direction: column;
}
.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  padding: 18px;
  border-bottom: 1px solid var(--border);
}
.eyebrow {
  font: 750 9px/1 var(--mono);
  letter-spacing: 0.08em;
  color: var(--accent);
  margin: 0 0 7px;
}
h2 {
  margin: 0;
  color: var(--text-strong);
  font-size: 18px;
  font-weight: 680;
  letter-spacing: -0.02em;
}
.refresh-btn {
  width: 34px;
  height: 34px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--muted);
  cursor: pointer;
}
.refresh-btn:hover {
  border-color: #cdd3ff;
  background: var(--accent-soft);
  color: var(--accent);
}
.refresh-btn svg {
  width: 16px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.meta-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
}
.meta-grid > div {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 13px 14px;
}
.meta-grid > div + div {
  border-left: 1px solid var(--border);
}
.mini-orb,
.meta-number {
  flex: 0 0 auto;
}
.mini-orb {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 3px var(--red-soft);
}
.mini-orb.connected,
.mini-orb.handshake {
  background: var(--green);
  box-shadow: 0 0 0 3px var(--green-soft);
}
.meta-number {
  color: var(--accent);
  font: 750 18px/1 var(--mono);
}
.meta-copy { min-width: 0; }
.meta-label {
  display: block;
  color: var(--muted);
  font: 650 9px/1 var(--mono);
  margin-bottom: 5px;
}
.meta-copy strong { font-size: 11px; white-space: nowrap; }
.status-text.connected,
.status-text.handshake {
  color: var(--green);
}
.status-text.error,
.status-text.disconnected {
  color: var(--red);
}
.list-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px 16px 7px;
  color: var(--muted);
  font-size: 10px;
  font-weight: 700;
}
.list-label strong {
  min-width: 22px;
  padding: 3px 6px;
  border-radius: 99px;
  color: var(--accent);
  background: var(--accent-soft);
  text-align: center;
  font: 700 9px/1 var(--mono);
}
.runs {
  min-height: 0;
  overflow: visible;
  padding: 4px 8px 12px;
}
.run-row {
  width: 100%;
  display: grid;
  grid-template-columns: 28px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 11px 10px;
  border: 1px solid transparent;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  color: var(--text);
  cursor: pointer;
}
.run-row:hover,
.run-row.active {
  background: var(--surface);
  border-color: var(--border);
  box-shadow: var(--shadow-sm);
}
.run-row.active {
  border-color: #d8ddff;
  background: linear-gradient(100deg, var(--accent-soft), #fff 70%);
}
.run-icon {
  width: 27px;
  height: 27px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border);
  border-radius: 9px;
  color: var(--muted);
  background: var(--bg-subtle);
}
.run-icon > span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}
.run-icon svg {
  width: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.run-icon.active { border-color: #cdd3ff; color: var(--accent); background: var(--accent-soft); }
.run-icon.done { border-color: #bfe9d7; color: var(--green); background: var(--green-soft); }
.run-icon.failed { border-color: #f4c9d1; color: var(--red); background: var(--red-soft); }
.run-main {
  min-width: 0;
}
.run-title,
.run-sub {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.run-title {
  color: var(--text-strong);
  font-size: 12px;
  font-weight: 680;
}
.run-sub,
.run-time {
  color: var(--muted);
  font: 550 9px/1.4 var(--mono);
}
.run-sub { display: flex; align-items: center; gap: 5px; margin-top: 4px; }
.run-sub i { width: 3px; height: 3px; border-radius: 50%; background: var(--border-strong); }
.run-time { align-self: start; margin-top: 2px; }
.empty {
  margin: auto 14px;
  padding: 28px 16px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-md);
  color: var(--muted);
  background: var(--bg-subtle);
  text-align: center;
}
.empty-beam { display: block; width: 40px; height: 3px; margin: 0 auto 16px; border-radius: 99px; background: linear-gradient(90deg, transparent, var(--beam), transparent); }
.empty strong { display: block; color: var(--text); font-size: 13px; }
.empty p { margin: 7px 0 0; font-size: 11px; line-height: 1.5; }
</style>
