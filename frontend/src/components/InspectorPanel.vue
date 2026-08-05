<template>
  <aside class="inspector">
    <div class="summary">
      <div class="summary-top">
        <div>
          <p class="eyebrow">INSPECTOR</p>
          <h2>运行检查器</h2>
        </div>
        <span :class="['status-badge', runtime.activeRun?.status || 'idle']">
          <i aria-hidden="true"></i>{{ statusLabel(runtime.activeRun?.status || 'idle') }}
        </span>
      </div>
      <div class="facts">
        <span><small>Provider</small><strong>{{ runtime.activeRun?.provider || '-' }}</strong></span>
        <span><small>Model</small><strong>{{ runtime.activeRun?.model || '-' }}</strong></span>
      </div>
    </div>

    <div class="output">
      <div class="output-head">
        <span>最终回复</span>
        <strong>{{ runtime.activeRun?.output.length || 0 }} 字符</strong>
      </div>
      <pre :class="{ placeholder: !runtime.activeRun?.output }">{{ runtime.activeRun?.output || '模型的可见输出会显示在这里。' }}</pre>
    </div>

    <ToolCallPanel />
    <MessageContextPanel />
  </aside>
</template>

<script setup lang="ts">
import MessageContextPanel from '@/components/MessageContextPanel.vue'
import ToolCallPanel from '@/components/ToolCallPanel.vue'
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    idle: '空闲',
    active: '运行中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status] || status
}
</script>

<style scoped>
.inspector {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: var(--surface-raised);
  box-shadow: var(--shadow-sm);
  min-width: 0;
  height: 100%;
  max-height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}
.summary {
  padding: 18px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(145deg, #fff, var(--surface-tint));
}
.summary-top { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.eyebrow {
  margin: 0 0 7px;
  font: 750 9px/1 var(--mono);
  letter-spacing: 0.08em;
  color: var(--accent);
}
h2 {
  margin: 0;
  color: var(--text-strong);
  font-size: 18px;
  font-weight: 680;
  letter-spacing: -0.02em;
}
.status-badge { display: inline-flex; align-items: center; gap: 6px; padding: 6px 8px; border-radius: 99px; color: var(--muted); background: var(--bg-subtle); font: 700 9px/1 var(--mono); white-space: nowrap; }
.status-badge i { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }
.status-badge.active { color: var(--accent); background: var(--accent-soft); }
.status-badge.done { color: var(--green); background: var(--green-soft); }
.status-badge.failed { color: var(--red); background: var(--red-soft); }
.facts {
  margin-top: 14px;
  display: grid;
  grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr);
  gap: 7px;
}
.facts span {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 9px;
  min-width: 0;
  background: rgba(255, 255, 255, 0.76);
}
.facts small, .facts strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.facts small { margin-bottom: 5px; color: var(--muted); font: 650 8px/1 var(--mono); text-transform: uppercase; }
.facts strong { color: var(--text); font-size: 10px; }
.output {
  margin: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
.output-head {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
}
.output-head span { color: var(--text); }
.output-head strong { padding: 3px 6px; border-radius: 5px; color: var(--accent); background: var(--accent-soft); }
pre {
  margin: 0;
  max-height: 240px;
  padding: 14px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 500 12px/1.6 var(--mono);
  color: var(--text);
  background: var(--surface);
}
.placeholder { color: var(--muted-soft); font-family: var(--sans); }
@media (max-width: 960px) {
  .inspector {
    min-width: 0;
    border-left: 0;
    border-top: 1px solid var(--border);
  }
}
</style>
