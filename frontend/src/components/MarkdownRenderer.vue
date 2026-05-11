<template>
  <div class="markdown" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ content: string }>()

function escapeHtml(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function inline(value: string) {
  return escapeHtml(value).replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
}

function renderTable(lines: string[]) {
  const rows = lines.map(line => line.trim().slice(1, -1).split('|').map(cell => inline(cell.trim())))
  const [head, , ...body] = rows
  return [
    '<table>',
    `<thead><tr>${head.map(cell => `<th>${cell}</th>`).join('')}</tr></thead>`,
    `<tbody>${body.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>`,
    '</table>'
  ].join('')
}

function renderMarkdown(content: string) {
  const lines = content.split(/\r?\n/)
  const output: string[] = []
  let listItems: string[] = []
  let tableLines: string[] = []

  const flushList = () => {
    if (!listItems.length) return
    output.push(`<ul>${listItems.map(item => `<li>${inline(item)}</li>`).join('')}</ul>`)
    listItems = []
  }
  const flushTable = () => {
    if (tableLines.length >= 2 && /^\|\s*-/.test(tableLines[1])) {
      output.push(renderTable(tableLines))
    } else {
      tableLines.forEach(line => output.push(`<p>${inline(line)}</p>`))
    }
    tableLines = []
  }

  for (const line of lines) {
    if (line.trim().startsWith('|')) {
      flushList()
      tableLines.push(line)
      continue
    }
    flushTable()
    if (!line.trim()) {
      flushList()
      continue
    }
    if (line.startsWith('### ')) {
      flushList()
      output.push(`<h3>${inline(line.slice(4))}</h3>`)
    } else if (line.startsWith('## ')) {
      flushList()
      output.push(`<h2>${inline(line.slice(3))}</h2>`)
    } else if (line.startsWith('# ')) {
      flushList()
      output.push(`<h1>${inline(line.slice(2))}</h1>`)
    } else if (line.startsWith('- ')) {
      listItems.push(line.slice(2))
    } else if (/^\d+\.\s/.test(line)) {
      flushList()
      output.push(`<p>${inline(line)}</p>`)
    } else {
      flushList()
      output.push(`<p>${inline(line)}</p>`)
    }
  }
  flushList()
  flushTable()
  return output.join('')
}

const html = computed(() => renderMarkdown(props.content))
</script>
