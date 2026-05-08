<template>
  <div class="page">
    <div class="header">
      <div><h1>资源生成</h1><p class="muted">一次任务生成 6 类资源，并记录多智能体 Trace。</p></div>
      <button class="btn" :disabled="store.loading" @click="store.generateResources">启动生成</button>
    </div>
    <div class="grid">
      <GenerationProgress class="span-4" :progress="store.progress" :loading="store.loading" />
      <AgentTraceTimeline class="span-8" :traces="store.traces" />
      <section class="panel span-12">
        <h2>生成结果</h2>
        <div class="cards"><ResourceCard v-for="r in store.resources" :key="r.id" :resource="r" @select="selected = $event" /></div>
      </section>
      <section v-if="selected" class="panel span-12 resource-content">
        <MermaidRenderer v-if="selected.content_format === 'mermaid'" :content="selected.content" />
        <pre v-else-if="selected.content_format === 'code' || selected.content_format === 'json'">{{ selected.content }}</pre>
        <MarkdownRenderer v-else :content="selected.content" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useLearningStore } from '../store'
import type { Resource } from '../types'
import GenerationProgress from '../components/GenerationProgress.vue'
import AgentTraceTimeline from '../components/AgentTraceTimeline.vue'
import ResourceCard from '../components/ResourceCard.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'
const store = useLearningStore()
const selected = ref<Resource | null>(null)
onMounted(store.refresh)
</script>
