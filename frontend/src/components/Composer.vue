<template>
  <form class="composer" @submit.prevent="runtime.sendLocalMessage">
    <div class="composer-box">
      <div class="input-mark" aria-hidden="true">
        <svg viewBox="0 0 24 24"><path d="M4 5h16v11H8l-4 3V5Z"></path></svg>
      </div>
      <textarea
        v-model="runtime.draft"
        rows="2"
        aria-label="发送本地 WebChat 消息"
        placeholder="向 Watchlight 发送一条消息…"
      ></textarea>
      <button type="submit" :disabled="!runtime.draft.trim()" aria-label="发送消息">
        <span>发送</span>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 14-7-4 14-3-6-7-1Z"></path><path d="m12 13 7-8"></path></svg>
      </button>
    </div>
    <div class="composer-actions">
      <span class="send-state"><i aria-hidden="true"></i>{{ runtime.sendStatus || 'WebChat · web:local' }}</span>
      <span>通过 Gateway 安全发送</span>
    </div>
  </form>
</template>

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'

const runtime = useRuntimeStore()
</script>

<style scoped>
.composer {
  border-top: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.94);
  padding: 13px 16px 11px;
}
.composer-box {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: end;
  gap: 8px;
  padding: 7px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-md);
  background: var(--bg-subtle);
  transition: border-color 160ms ease, box-shadow 160ms ease, background 160ms ease;
}
.composer-box:focus-within {
  border-color: #aeb8ff;
  background: var(--surface);
  box-shadow: 0 0 0 4px var(--accent-soft);
}
.input-mark {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  align-self: start;
  color: var(--accent);
}
.input-mark svg,
button svg {
  width: 17px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}
textarea {
  width: 100%;
  min-height: 48px;
  max-height: 150px;
  resize: none;
  border: 0;
  background: transparent;
  color: var(--text);
  padding: 8px 2px;
  outline: none;
  font: 500 13px/1.5 var(--sans);
}
textarea::placeholder { color: var(--muted-soft); }
.composer-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  padding: 0 3px;
  color: var(--muted);
  font: 700 10px/1 var(--mono);
}
.send-state { display: inline-flex; align-items: center; gap: 6px; }
.send-state i { width: 5px; height: 5px; border-radius: 50%; background: var(--green); box-shadow: 0 0 0 3px var(--green-soft); }
.composer-box button {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  border: 0;
  border-radius: 9px;
  background: linear-gradient(135deg, var(--accent-strong), #697af8);
  color: #fff;
  height: 38px;
  padding: 0 14px;
  font: 700 11px/1 var(--sans);
  box-shadow: 0 7px 16px rgba(86, 104, 246, 0.2);
  cursor: pointer;
}
.composer-box button:hover {
  background: var(--accent-strong);
}
.composer-box button:disabled {
  color: var(--muted-soft);
  background: #e7eaf0;
  box-shadow: none;
  opacity: 0.45;
  cursor: not-allowed;
}
@media (max-width: 560px) {
  .input-mark { display: none; }
  .composer-box { grid-template-columns: minmax(0, 1fr) auto; }
  .composer-actions > span:last-child { display: none; }
  .composer-box button span { display: none; }
  .composer-box button { width: 38px; padding: 0; justify-content: center; }
}
</style>
