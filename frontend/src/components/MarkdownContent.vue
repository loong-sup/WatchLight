<template>
  <div class="markdown-content">
    <template v-for="(block, index) in blocks" :key="index">
      <component
        :is="`h${block.level || 2}`"
        v-if="block.type === 'heading'"
        :class="`heading level-${block.level || 2}`"
      >
        <InlineContent :nodes="block.inlines || []" />
      </component>
      <p v-else-if="block.type === 'paragraph'">
        <InlineContent :nodes="block.inlines || []" />
      </p>
      <component :is="block.ordered ? 'ol' : 'ul'" v-else-if="block.type === 'list'">
        <li v-for="(item, itemIndex) in block.items || []" :key="itemIndex">
          <InlineContent :nodes="item" />
        </li>
      </component>
      <blockquote v-else-if="block.type === 'quote'">
        <InlineContent :nodes="block.inlines || []" />
      </blockquote>
      <pre v-else-if="block.type === 'code'"><code :data-language="block.language || undefined">{{ block.text }}</code></pre>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, type PropType } from 'vue'
import { parseMarkdown, type InlineNode } from '@/utils/markdown'

const props = defineProps<{ content: string }>()
const blocks = computed(() => parseMarkdown(props.content || ''))

const InlineContent = defineComponent({
  props: {
    nodes: { type: Array as PropType<InlineNode[]>, required: true },
  },
  setup(inlineProps) {
    return () =>
      inlineProps.nodes.map((node, index) => {
        if (node.type === 'strong') return h('strong', { key: index }, node.text)
        if (node.type === 'emphasis') return h('em', { key: index }, node.text)
        if (node.type === 'code') return h('code', { key: index }, node.text)
        if (node.type === 'link' && node.href) {
          return h(
            'a',
            { key: index, href: node.href, target: '_blank', rel: 'noopener noreferrer' },
            node.text,
          )
        }
        return node.text
      })
  },
})
</script>

<style scoped>
.markdown-content {
  min-width: 0;
  color: #111827;
  font-size: 13px;
  line-height: 1.68;
  overflow-wrap: anywhere;
}
.markdown-content > :first-child { margin-top: 0; }
.markdown-content > :last-child { margin-bottom: 0; }
.heading { margin: 1.05em 0 0.52em; color: var(--text-strong); line-height: 1.3; }
.level-1 { font-size: 1.42em; }
.level-2 { font-size: 1.28em; }
.level-3 { font-size: 1.16em; }
.level-4, .level-5, .level-6 { font-size: 1.04em; }
p { margin: 0.62em 0; white-space: pre-wrap; }
ul, ol { margin: 0.6em 0; padding-left: 1.55em; }
li { margin: 0.24em 0; }
blockquote {
  margin: 0.72em 0;
  padding: 0.45em 0.85em;
  border-left: 3px solid var(--accent);
  border-radius: 0 7px 7px 0;
  color: var(--muted);
  background: var(--accent-soft);
  white-space: pre-wrap;
}
pre {
  margin: 0.75em 0;
  padding: 12px 14px;
  overflow: auto;
  border: 1px solid #dfe4ee;
  border-radius: 9px;
  color: #e5e7eb;
  background: #171b27;
  font: 500 12px/1.62 var(--mono);
  white-space: pre;
}
:deep(strong) { color: var(--text-strong); font-weight: 720; }
:deep(em) { color: #374151; }
:deep(code) {
  padding: 0.12em 0.34em;
  border-radius: 4px;
  color: #4052e8;
  background: #edf0ff;
  font: 550 0.92em/1.5 var(--mono);
}
pre :deep(code) { padding: 0; color: inherit; background: transparent; font: inherit; }
:deep(a) { color: var(--accent-strong); text-decoration: none; border-bottom: 1px solid currentColor; }
:deep(a:hover) { color: #273bd0; }
</style>
