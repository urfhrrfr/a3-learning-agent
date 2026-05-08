<template>
  <div class="panel">
    <div ref="target"></div>
    <pre v-if="failed">{{ content }}</pre>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import mermaid from 'mermaid'

const props = defineProps<{ content: string }>()
const target = ref<HTMLElement | null>(null)
const failed = ref(false)

async function render() {
  if (!target.value) return
  try {
    failed.value = false
    mermaid.initialize({ startOnLoad: false, securityLevel: 'loose' })
    const { svg } = await mermaid.render(`m_${Math.random().toString(16).slice(2)}`, props.content)
    target.value.innerHTML = svg
  } catch {
    failed.value = true
  }
}

onMounted(render)
watch(() => props.content, render)
</script>
