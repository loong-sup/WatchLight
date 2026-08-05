<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand-block">
        <div class="brand-mark" aria-hidden="true">
          <span></span>
        </div>
        <div>
          <div class="brand-line">
            <strong>Watchlight</strong>
            <span class="product-tag">Runtime</span>
          </div>
          <p>AI 运行观测工作台</p>
        </div>
      </div>

      <div class="metric-strip" aria-label="运行概览">
        <article v-for="metric in metrics" :key="metric.label" :class="['metric', metric.tone]">
          <span>{{ metric.label }}</span>
          <strong>{{ metric.value }}</strong>
          <small>{{ metric.hint }}</small>
        </article>
      </div>

      <div class="top-actions">
        <div :class="['connection-pill', runtime.wsStatus]">
          <span class="status-orb" aria-hidden="true"></span>
          <div>
            <small>Gateway · 18789</small>
            <strong>{{ connectionLabel(runtime.wsStatus) }}</strong>
          </div>
        </div>
        <button
          class="icon-button inspector-toggle"
          type="button"
          :aria-pressed="inspectorOpen"
          :aria-label="inspectorOpen ? '隐藏检查器' : '显示检查器'"
          @click="inspectorOpen = !inspectorOpen"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <rect x="3" y="4" width="18" height="16" rx="2"></rect>
            <path d="M15 4v16"></path>
          </svg>
        </button>
      </div>
    </header>

    <main :class="['workspace', { 'inspector-hidden': !inspectorOpen }]">
      <RunList />
      <section class="main-stage">
        <div class="center-scroll">
          <ArchitectureMap />
          <RuntimeTimeline />
        </div>
        <Composer />
      </section>
      <InspectorPanel v-if="inspectorOpen" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ArchitectureMap from '@/components/ArchitectureMap.vue'
import Composer from '@/components/Composer.vue'
import InspectorPanel from '@/components/InspectorPanel.vue'
import RunList from '@/components/RunList.vue'
import RuntimeTimeline from '@/components/RuntimeTimeline.vue'
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()
const inspectorOpen = ref(true)

const metrics = computed(() => {
  const run = runtime.activeRun
  const status = run?.status || 'idle'
  return [
    {
      label: '会话',
      value: runtime.runs.length,
      hint: runtime.runs.length ? '本次工作区' : '等待接入',
      tone: 'neutral',
    },
    {
      label: '当前运行',
      value: statusLabel(status),
      hint: run?.model || '暂无模型',
      tone: status,
    },
    {
      label: '事件',
      value: runtime.activeEvents.length,
      hint: run ? '当前链路' : '暂无运行',
      tone: runtime.activeEvents.length ? 'active' : 'neutral',
    },
    {
      label: '工具',
      value: run?.tools.length || 0,
      hint: run?.tools.some((tool) => tool.status === 'active') ? '正在调用' : '调用记录',
      tone: run?.tools.some((tool) => tool.status === 'failed') ? 'failed' : 'neutral',
    },
  ]
})

function connectionLabel(status: string) {
  const labels: Record<string, string> = {
    connected: '实时连接',
    handshake: '正在握手',
    disconnected: '连接断开',
    error: '连接异常',
  }
  return labels[status] || status
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    idle: '空闲',
    active: '运行中',
    done: '已完成',
    failed: '失败',
  }
  return labels[status] || status
}

onMounted(async () => {
  if (window.innerWidth <= 1060) inspectorOpen.value = false
  await Promise.allSettled([runtime.connect(), runtime.loadSnapshot()])
})
</script>

<style>
:root {
  --bg: #f4f6fa;
  --bg-subtle: #f8f9fc;
  --surface: #ffffff;
  --surface-raised: rgba(255, 255, 255, 0.94);
  --surface-tint: #f7f9ff;
  --text: #192033;
  --text-strong: #0e1424;
  --muted: #687086;
  --muted-soft: #939bad;
  --border: #e2e6ef;
  --border-strong: #d4dae7;
  --accent: #5668f6;
  --accent-strong: #4052e8;
  --accent-soft: #edf0ff;
  --beam: #6b7cff;
  --beam-cyan: #42cbd3;
  --green: #159a68;
  --green-soft: #e9f8f1;
  --red: #dc4c64;
  --red-soft: #fff0f3;
  --amber: #bd7a17;
  --amber-soft: #fff7e8;
  --shadow-sm: 0 1px 2px rgba(20, 28, 54, 0.04), 0 5px 16px rgba(20, 28, 54, 0.035);
  --shadow-md: 0 12px 32px rgba(31, 42, 78, 0.08);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --sans: Inter, 'Noto Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  --mono: 'JetBrains Mono', 'SFMono-Regular', Consolas, monospace;
}

* {
  box-sizing: border-box;
}

html,
body,
#app {
  height: 100%;
  overflow: hidden;
}

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  -webkit-font-smoothing: antialiased;
}

button,
textarea {
  font-family: inherit;
}

button:focus-visible,
textarea:focus-visible,
summary:focus-visible,
a:focus-visible {
  outline: 3px solid rgba(86, 104, 246, 0.24);
  outline-offset: 2px;
}

::selection {
  background: var(--accent);
  color: #fff;
}

.app-shell {
  height: 100dvh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(circle at 48% -20%, rgba(86, 104, 246, 0.1), transparent 34%),
    var(--bg);
}

.topbar {
  flex: 0 0 88px;
  height: 88px;
  display: grid;
  grid-template-columns: minmax(230px, 0.8fr) minmax(440px, 1.5fr) auto;
  align-items: center;
  gap: 24px;
  padding: 12px 20px;
  border-bottom: 1px solid rgba(212, 218, 231, 0.86);
  background: rgba(250, 251, 254, 0.88);
  backdrop-filter: blur(18px);
  z-index: 10;
}

.brand-block,
.brand-line,
.top-actions,
.connection-pill {
  display: flex;
  align-items: center;
}

.brand-block {
  gap: 12px;
  min-width: 0;
}

.brand-mark {
  position: relative;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  display: grid;
  place-items: center;
  border-radius: 13px;
  color: #fff;
  background: linear-gradient(145deg, #4156ed, #7584ff 60%, #48ccd2);
  box-shadow: 0 8px 24px rgba(86, 104, 246, 0.24);
  overflow: hidden;
}

.brand-mark::before,
.brand-mark::after,
.brand-mark span {
  content: '';
  position: absolute;
  border-radius: 999px;
}

.brand-mark::before {
  width: 26px;
  height: 10px;
  border: 2px solid rgba(255, 255, 255, 0.92);
}

.brand-mark::after {
  width: 7px;
  height: 7px;
  background: #fff;
  box-shadow: 0 0 12px #fff;
}

.brand-mark span {
  width: 32px;
  height: 2px;
  background: rgba(255, 255, 255, 0.42);
  transform: rotate(-34deg);
}

.brand-line {
  gap: 8px;
}

.brand-line strong {
  color: var(--text-strong);
  font-size: 17px;
  letter-spacing: -0.02em;
}

.product-tag {
  padding: 3px 6px;
  border: 1px solid #dce1ff;
  border-radius: 5px;
  color: var(--accent);
  background: var(--accent-soft);
  font: 700 9px/1 var(--mono);
  text-transform: uppercase;
}

.brand-block p {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 11px;
}

.metric-strip {
  min-width: 0;
  display: grid;
  grid-template-columns: repeat(4, minmax(94px, 1fr));
  gap: 8px;
}

.metric {
  min-width: 0;
  height: 62px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-content: center;
  gap: 4px 10px;
  padding: 9px 11px;
  border: 1px solid rgba(226, 230, 239, 0.9);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.72);
}

.metric > span,
.metric small {
  color: var(--muted);
  font-size: 10px;
}

.metric > span {
  font-weight: 650;
}

.metric strong {
  grid-row: span 2;
  align-self: center;
  color: var(--text-strong);
  font-size: 17px;
  line-height: 1;
  white-space: nowrap;
}

.metric small {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric.active strong { color: var(--accent); }
.metric.done strong { color: var(--green); }
.metric.failed strong { color: var(--red); }

.top-actions {
  gap: 8px;
}

.connection-pill {
  min-width: 132px;
  gap: 9px;
  padding: 9px 11px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}

.connection-pill small,
.connection-pill strong {
  display: block;
}

.connection-pill small {
  margin-bottom: 3px;
  color: var(--muted);
  font: 600 9px/1 var(--mono);
}

.connection-pill strong {
  color: var(--text-strong);
  font-size: 11px;
}

.status-orb {
  width: 9px;
  height: 9px;
  flex: 0 0 9px;
  border: 2px solid #fff;
  border-radius: 50%;
  background: var(--red);
  box-shadow: 0 0 0 3px var(--red-soft);
}

.connected .status-orb,
.handshake .status-orb {
  background: var(--green);
  box-shadow: 0 0 0 3px var(--green-soft);
}

.handshake .status-orb {
  background: var(--amber);
  box-shadow: 0 0 0 3px var(--amber-soft);
}

.icon-button {
  width: 40px;
  height: 40px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--muted);
  background: var(--surface);
  cursor: pointer;
}

.icon-button:hover,
.icon-button[aria-pressed='true'] {
  border-color: #cdd3ff;
  color: var(--accent);
  background: var(--accent-soft);
}

.icon-button svg {
  width: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
}

.workspace {
  flex: 0 0 calc(100dvh - 88px);
  height: calc(100dvh - 88px);
  min-height: 0;
  display: grid;
  grid-template-columns: 286px minmax(520px, 1fr) 380px;
  gap: 12px;
  padding: 12px;
  overflow: hidden;
}

.workspace.inspector-hidden {
  grid-template-columns: 286px minmax(0, 1fr);
}

.workspace > * {
  height: 100%;
  min-height: 0;
}

.main-stage {
  min-width: 0;
  min-height: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) auto;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(circle at 50% 0, rgba(86, 104, 246, 0.055), transparent 30%),
    var(--surface);
  box-shadow: var(--shadow-sm);
}

.center-scroll {
  height: 100%;
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

::-webkit-scrollbar {
  width: 7px;
  height: 7px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  border: 2px solid transparent;
  border-radius: 99px;
  background: #c5cbd8;
  background-clip: padding-box;
}

@media (max-width: 1220px) {
  .topbar {
    grid-template-columns: minmax(210px, 0.7fr) minmax(360px, 1.3fr) auto;
    gap: 14px;
  }
  .metric:nth-child(1) { display: none; }
  .metric-strip { grid-template-columns: repeat(3, minmax(90px, 1fr)); }
  .workspace { grid-template-columns: 252px minmax(450px, 1fr) 340px; }
}

@media (max-width: 1060px) {
  .workspace,
  .workspace.inspector-hidden {
    grid-template-columns: 244px minmax(0, 1fr);
  }
  .workspace > .inspector {
    position: fixed;
    z-index: 20;
    top: 100px;
    right: 12px;
    bottom: 12px;
    width: min(380px, calc(100vw - 24px));
    height: auto;
    box-shadow: var(--shadow-md);
  }
  .connection-pill { min-width: auto; }
  .connection-pill small { display: none; }
}

@media (max-width: 820px) {
  html,
  body,
  #app { overflow: auto; }
  .app-shell { height: auto; min-height: 100dvh; overflow: visible; }
  .topbar {
    height: auto;
    min-height: 138px;
    grid-template-columns: 1fr auto;
    align-items: start;
    padding: 14px;
  }
  .metric-strip {
    grid-column: 1 / -1;
    grid-row: 2;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .workspace,
  .workspace.inspector-hidden {
    height: auto;
    min-height: calc(100dvh - 138px);
    display: block;
    padding: 10px;
    overflow: visible;
  }
  .workspace > * { height: auto; margin-bottom: 10px; }
  .workspace > .inspector {
    top: 148px;
    height: calc(100dvh - 160px);
    margin: 0;
  }
  .main-stage { min-height: 760px; }
  .center-scroll { overflow: visible; }
}

@media (max-width: 560px) {
  .brand-block p { display: none; }
  .top-actions { align-self: center; }
  .metric { height: 58px; padding: 8px; }
  .metric small { display: none; }
  .metric strong { grid-row: auto; font-size: 15px; }
}

@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    scroll-behavior: auto !important;
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
