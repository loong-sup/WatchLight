<template>
  <section class="architecture">
    <div class="section-head">
      <div>
        <p class="eyebrow">RUNTIME PATH</p>
        <h3>执行光迹</h3>
      </div>
      <div class="current-layer">
        <span class="live-dot" aria-hidden="true"></span>
        <span>当前位置</span>
        <strong>{{ currentLayerLabel }}</strong>
      </div>
    </div>
    <div class="layers">
      <article
        v-for="layer in layerRows"
        :key="layer.id"
        :class="['layer', statusOf(layer.id)]"
      >
        <span class="trail" aria-hidden="true"><i></i></span>
        <div class="layer-top">
          <span class="step-index">
            <svg v-if="layer.status === 'done'" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 8 2.4 2.4L12 5"></path></svg>
            <svg v-else-if="layer.status === 'failed'" viewBox="0 0 16 16" aria-hidden="true"><path d="M5 5l6 6M11 5l-6 6"></path></svg>
            <span v-else>{{ layer.index }}</span>
          </span>
          <span class="step-status">{{ statusLabel(layer.status) }}</span>
        </div>
        <strong class="layer-id">{{ layer.label }}</strong>
        <span class="layer-detail">{{ layer.detail }}</span>
        <div class="layer-event">
          <span>最新事件</span>
          <strong>{{ eventTitle(layer.latest) }}</strong>
          <time v-if="layer.latest">{{ formatTime(layer.latest.ts) }}</time>
        </div>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ARCHITECTURE_LAYERS, useRuntimeStore } from '@/stores/runtime'
import type { LayerId, RuntimeEventPayload, RuntimeStatus } from '@/api/types'

const runtime = useRuntimeStore()

function statusOf(layer: LayerId) {
  return runtime.activeRun?.layerStatus[layer] || 'idle'
}

const layerRows = computed(() =>
  ARCHITECTURE_LAYERS.map((layer, index) => {
    const events = runtime.activeEvents.filter((event) => event.layer === layer.id)
    return {
      ...layer,
      index: index + 1,
      status: statusOf(layer.id),
      latest: events.at(-1),
    }
  }),
)

const currentLayerLabel = computed(() => {
  const rows = layerRows.value
  const current =
    rows.find((row) => row.status === 'failed') ||
    [...rows].reverse().find((row) => row.status === 'active') ||
    [...rows].reverse().find((row) => row.status === 'done')
  return current ? `${current.index}. ${current.label}` : '等待消息'
})

function statusLabel(status: RuntimeStatus) {
  const labels: Record<RuntimeStatus, string> = {
    idle: '等待',
    active: '进行中',
    done: '完成',
    failed: '失败',
  }
  return labels[status]
}

function formatTime(ts: number) {
  return new Date(ts).toLocaleTimeString([], { hour12: false })
}

function eventTitle(event?: RuntimeEventPayload) {
  if (!event) return '尚未进入'
  const labels: Record<string, string> = {
    'runtime.channel.inbound': '收到消息',
    'runtime.session.loaded': '读取会话',
    'runtime.run.started': 'Gateway 启动运行',
    'runtime.messages.initial': '组装上下文',
    'runtime.model.streaming': '模型流式输出',
    'runtime.usage': '统计 Token',
    'runtime.tool.started': '开始调用工具',
    'runtime.tool.finished': '工具返回',
    'runtime.run.completed': '运行完成',
    'runtime.run.failed': '运行失败',
    'runtime.channel.reply_sent': '回复已发出',
    'runtime.channel.reply_failed': '回复发送失败',
  }
  return labels[event.type] || event.title || event.type
}
</script>

<style scoped>
.architecture {
  border-bottom: 1px solid var(--border);
  background: linear-gradient(180deg, rgba(247, 249, 255, 0.88), #fff);
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 18px;
  padding: 18px 20px 14px;
}
.eyebrow {
  font: 750 9px/1 var(--mono);
  letter-spacing: 0.08em;
  color: var(--accent);
  margin: 0 0 7px;
}
h3 {
  margin: 0;
  color: var(--text-strong);
  font-size: 18px;
  font-weight: 680;
  letter-spacing: -0.02em;
}
.current-layer {
  display: flex;
  align-items: center;
  gap: 7px;
  min-width: 0;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.78);
}
.current-layer span {
  color: var(--muted);
  font-size: 11px;
}
.current-layer strong {
  font-size: 12px;
  color: var(--text-strong);
  white-space: nowrap;
}
.live-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--beam); box-shadow: 0 0 0 4px var(--accent-soft); }
.layers {
  display: grid;
  grid-template-columns: repeat(7, minmax(95px, 1fr));
  gap: 0;
  padding: 4px 16px 18px;
  border-top: 1px solid var(--border);
}
.layer {
  min-width: 0;
  min-height: 145px;
  padding: 20px 8px 0;
  position: relative;
}
.trail {
  position: absolute;
  top: 36px;
  left: 0;
  width: 100%;
  height: 2px;
  background: var(--border-strong);
  overflow: hidden;
}
.layer:first-child .trail { left: 50%; width: 50%; }
.layer:last-child .trail { width: 50%; }
.layer.done .trail,
.layer.active .trail {
  background: linear-gradient(90deg, var(--beam), var(--beam-cyan));
}
.layer.failed .trail { background: var(--red); }
.trail i {
  position: absolute;
  inset: 0 auto 0 -45%;
  width: 42%;
  background: linear-gradient(90deg, transparent, #fff, transparent);
  opacity: 0;
}
.layer.active .trail i {
  opacity: 0.9;
  animation: beam-flow 1.65s linear infinite;
}
@keyframes beam-flow { to { transform: translateX(340%); } }
.layer-top {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-bottom: 11px;
}
.step-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 33px;
  height: 33px;
  border: 3px solid #fff;
  border-radius: 50%;
  background: #e7eaf1;
  color: var(--muted);
  box-shadow: 0 0 0 1px var(--border-strong);
  font: 750 10px/1 var(--mono);
}
.step-index svg { width: 17px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.layer.active .step-index { color: #fff; background: var(--accent); box-shadow: 0 0 0 1px var(--accent), 0 0 0 7px var(--accent-soft), 0 0 18px rgba(86, 104, 246, 0.32); }
.layer.done .step-index { color: #fff; background: var(--green); box-shadow: 0 0 0 1px var(--green); }
.layer.failed .step-index { color: #fff; background: var(--red); box-shadow: 0 0 0 1px var(--red), 0 0 0 6px var(--red-soft); }
.step-status {
  color: var(--muted);
  font: 700 9px/1 var(--mono);
}
.layer.active .step-status {
  color: var(--accent);
}
.layer.done .step-status {
  color: var(--green);
}
.layer.failed .step-status {
  color: var(--red);
}
.layer-id,
.layer-detail {
  display: block;
  text-align: center;
}
.layer-id {
  color: var(--text-strong);
  font-size: 12px;
  line-height: 1.2;
}
.layer-detail {
  margin-top: 5px;
  color: var(--muted);
  font-size: 9px;
  line-height: 1.3;
}
.layer-event {
  margin-top: 10px;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.76);
}
.layer-event span,
.layer-event time {
  display: block;
  color: var(--muted);
  font: 650 8px/1.2 var(--mono);
}
.layer-event > span { display: none; }
.layer-event strong {
  display: block;
  margin: 5px 0;
  overflow: hidden;
  color: var(--text);
  font-size: 10px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}
@media (max-width: 1100px) {
  .layers {
    grid-template-columns: repeat(7, minmax(92px, 1fr));
    overflow-x: auto;
  }
}
@media (max-width: 720px) {
  .section-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .layers { grid-template-columns: repeat(7, minmax(105px, 1fr)); }
}
</style>
