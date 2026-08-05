export type InlineNode = {
  type: 'text' | 'strong' | 'emphasis' | 'code' | 'link'
  text: string
  href?: string
}

export type MarkdownBlock = {
  type: 'heading' | 'paragraph' | 'list' | 'quote' | 'code'
  level?: number
  inlines?: InlineNode[]
  items?: InlineNode[][]
  ordered?: boolean
  text?: string
  language?: string
}

const inlinePattern = /(\*\*[^*\n]+\*\*|__[^_\n]+__|\*[^*\n]+\*|`[^`\n]+`|\[[^\]\n]+]\([^)\s]+\))/g

export function parseInline(source: string): InlineNode[] {
  const nodes: InlineNode[] = []
  let cursor = 0
  for (const match of source.matchAll(inlinePattern)) {
    const index = match.index ?? 0
    if (index > cursor) nodes.push({ type: 'text', text: source.slice(cursor, index) })
    const token = match[0]
    if (token.startsWith('**') || token.startsWith('__')) {
      nodes.push({ type: 'strong', text: token.slice(2, -2) })
    } else if (token.startsWith('*')) {
      nodes.push({ type: 'emphasis', text: token.slice(1, -1) })
    } else if (token.startsWith('`')) {
      nodes.push({ type: 'code', text: token.slice(1, -1) })
    } else {
      const link = token.match(/^\[([^\]]+)]\(([^)]+)\)$/)
      if (link && isSafeLink(link[2])) {
        nodes.push({ type: 'link', text: link[1], href: link[2] })
      } else {
        nodes.push({ type: 'text', text: token })
      }
    }
    cursor = index + token.length
  }
  if (cursor < source.length) nodes.push({ type: 'text', text: source.slice(cursor) })
  return nodes
}

export function parseMarkdown(source: string): MarkdownBlock[] {
  const lines = source.replace(/\r\n?/g, '\n').split('\n')
  const blocks: MarkdownBlock[] = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    if (!line.trim()) {
      index += 1
      continue
    }
    const fence = line.match(/^```\s*([\w+-]*)\s*$/)
    if (fence) {
      const code: string[] = []
      index += 1
      while (index < lines.length && !/^```\s*$/.test(lines[index])) {
        code.push(lines[index])
        index += 1
      }
      if (index < lines.length) index += 1
      blocks.push({ type: 'code', text: code.join('\n'), language: fence[1] })
      continue
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      blocks.push({
        type: 'heading',
        level: heading[1].length,
        inlines: parseInline(heading[2]),
      })
      index += 1
      continue
    }
    const list = line.match(/^\s*(?:([-+*])|(\d+)\.)\s+(.+)$/)
    if (list) {
      const ordered = Boolean(list[2])
      const items: InlineNode[][] = []
      while (index < lines.length) {
        const item = lines[index].match(/^\s*(?:([-+*])|(\d+)\.)\s+(.+)$/)
        if (!item || Boolean(item[2]) !== ordered) break
        items.push(parseInline(item[3]))
        index += 1
      }
      blocks.push({ type: 'list', ordered, items })
      continue
    }
    if (/^>\s?/.test(line)) {
      const quote: string[] = []
      while (index < lines.length && /^>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^>\s?/, ''))
        index += 1
      }
      blocks.push({ type: 'quote', inlines: parseInline(quote.join('\n')) })
      continue
    }
    const paragraph = [line]
    index += 1
    while (index < lines.length && !isBlockStart(lines[index])) {
      paragraph.push(lines[index])
      index += 1
    }
    blocks.push({ type: 'paragraph', inlines: parseInline(paragraph.join('\n')) })
  }
  return blocks
}

function isBlockStart(line: string): boolean {
  return (
    !line.trim() ||
    /^```/.test(line) ||
    /^#{1,6}\s+/.test(line) ||
    /^\s*(?:[-+*]|\d+\.)\s+/.test(line) ||
    /^>\s?/.test(line)
  )
}

function isSafeLink(href: string): boolean {
  try {
    const url = new URL(href)
    return url.protocol === 'http:' || url.protocol === 'https:'
  } catch {
    return false
  }
}
