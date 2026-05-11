<template>
  <div class="mermaid-panel">
    <div v-if="loading" class="mermaid-state">
      <span class="spinner" aria-hidden="true"></span>
      <span>正在渲染思维导图...</span>
    </div>
    <div v-show="!failed" ref="target" class="mermaid-canvas"></div>
    <div v-if="failed" class="mermaid-fallback">
      <strong>导图渲染失败，已保留原始 Mermaid 文本</strong>
      <p class="muted">{{ errorMessage || '请检查语法或稍后重试。' }}</p>
      <pre>{{ normalizedContent }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps<{ content: string }>()
const target = ref<HTMLElement | null>(null)
const failed = ref(false)
const loading = ref(false)
const errorMessage = ref('')
let initialized = false
let renderVersion = 0

function cleanLabel(value: string) {
  return value
    .replace(/["'`]/g, '')
    .replace(/[()[\]{}]/g, match => ({ '(': '（', ')': '）', '[': '【', ']': '】', '{': '｛', '}': '｝' }[match] || match))
    .replace(/\s+/g, ' ')
    .trim()
}

function normalizeMindmap(content: string) {
  const stripped = content
    .trim()
    .replace(/^```mermaid\s*/i, '')
    .replace(/^```\s*/i, '')
    .replace(/```$/i, '')
    .trim()
  const lines = stripped.split(/\r?\n/).map(line => line.trimEnd()).filter(Boolean)
  if (!lines.length || lines[0].trim() !== 'mindmap') return stripped
  if (!stripped.includes('-->')) return stripped

  const title = cleanLabel(lines.find(line => line.trim().startsWith('root'))?.replace(/^.*root\s*\(\((.*?)\)\).*$/i, '$1') || '知识结构')
  const sections = new Map<string, string[]>([
    ['学习目标', []],
    ['核心概念', []],
    ['常见误区', []],
    ['实践任务', []],
  ])
  let current = '核心概念'

  for (const rawLine of lines.slice(2)) {
    const line = rawLine.trim()
    if (!line) continue
    if (sections.has(line)) {
      current = line
      continue
    }
    const arrowMatch = line.match(/-->\s*[A-Za-z0-9_]+\s*(?:\[(.*?)\]|\((.*?)\)|\{(.*?)\})/)
    const label = cleanLabel(arrowMatch?.[1] || arrowMatch?.[2] || arrowMatch?.[3] || line)
    if (label && label !== 'mindmap') sections.get(current)?.push(label)
  }

  const output = ['mindmap', `  root((${title}))`]
  for (const [section, children] of sections) {
    output.push(`    ${section}`)
    for (const child of children.length ? children : ['待补充']) {
      output.push(`      ${child}`)
    }
  }
  return output.join('\n')
}

const normalizedContent = computed(() => normalizeMindmap(props.content))

async function render() {
  if (!target.value) return
  const version = ++renderVersion
  try {
    loading.value = true
    failed.value = false
    errorMessage.value = ''
    target.value.innerHTML = ''
    const { default: mermaid } = await import('mermaid')
    if (!initialized) {
      mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' })
      initialized = true
    }
    const { svg } = await mermaid.render(`m_${Math.random().toString(16).slice(2)}`, normalizedContent.value)
    if (version !== renderVersion) return
    target.value.innerHTML = svg
  } catch (error) {
    if (version !== renderVersion) return
    failed.value = true
    errorMessage.value = error instanceof Error ? error.message : ''
  } finally {
    if (version === renderVersion) {
      loading.value = false
    }
  }
}

onMounted(render)
watch(() => props.content, render)
</script>
