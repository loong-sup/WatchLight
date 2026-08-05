<template>
  <section class="messages-panel">
    <div class="tabs">
      <button :class="{ active: tab === 'current' }" type="button" @click="tab = 'current'">当前上下文 · {{ runtime.activeMessages.length }}</button>
      <button :class="{ active: tab === 'initial' }" type="button" @click="tab = 'initial'">初始消息 · {{ runtime.activeRun?.initialMessages.length || 0 }}</button>
    </div>

    <div class="message-list">
      <article v-for="(message, index) in messages" :key="index" class="message-row">
        <div class="message-meta">
          <span>{{ message.role }}</span>
          <span v-if="message.name">{{ message.name }}</span>
        </div>
        <MarkdownContent
          v-if="message.role === 'assistant' && typeof message.content === 'string'"
          class="rendered-message"
          :content="message.content"
        />
        <pre v-else>{{ formatMessage(message) }}</pre>
      </article>
    </div>

    <div v-if="!messages.length" class="empty">暂无消息上下文。</div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import MarkdownContent from '@/components/MarkdownContent.vue'
import { useRuntimeStore } from '@/stores/runtime'
import type { RuntimeMessage } from '@/api/types'

const runtime = useRuntimeStore()
const tab = ref<'current' | 'initial'>('current')

const messages = computed(() => {
  const run = runtime.activeRun
  if (!run) return []
  return tab.value === 'initial' ? run.initialMessages : runtime.activeMessages
})

function formatMessage(message: RuntimeMessage) {
  if (message.tool_call) return JSON.stringify(message.tool_call, null, 2)
  if (typeof message.content === 'string') return message.content
  return JSON.stringify(message, null, 2)
}
</script>

<style scoped>
.messages-panel {
  min-height: 0;
  display: flex;
  flex-direction: column;
  border-top: 1px solid var(--border);
}
.tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 8px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-subtle);
}
.tabs button {
  height: 32px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  cursor: pointer;
}
.tabs button.active {
  background: var(--surface);
  color: var(--accent);
  box-shadow: var(--shadow-sm);
}
.message-list {
  padding: 12px;
}
.message-row {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: var(--surface);
  margin-bottom: 10px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.message-meta {
  display: flex;
  justify-content: space-between;
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  color: var(--muted);
  font: 700 10px/1 var(--mono);
  text-transform: uppercase;
  background: var(--bg-subtle);
}
pre {
  padding: 10px;
  margin: 0;
  max-height: 280px;
  overflow: auto;
  color: var(--text);
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font: 500 11px/1.55 var(--mono);
}
.rendered-message {
  padding: 10px 12px 12px;
  max-height: 360px;
  overflow: auto;
}
.empty {
  margin: 12px;
  padding: 18px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--bg-subtle);
  color: var(--muted);
  font-size: 11px;
  text-align: center;
}
</style>
