<template>
  <div class="page">
    <div class="header">
      <div><h1>资源库</h1><p class="muted">所有资源都展示来源、难度、审核状态和创建智能体。</p></div>
      <select v-model="filter"><option value="">全部</option><option v-for="t in types" :key="t">{{ t }}</option></select>
    </div>
    <div class="grid">
      <section class="span-5 cards"><ResourceCard v-for="r in filtered" :key="r.id" :resource="r" @select="selected = $event" /></section>
      <section class="panel span-7 resource-content">
        <template v-if="selected">
          <h2>{{ selected.title }}</h2>
          <MermaidRenderer v-if="selected.content_format === 'mermaid'" :content="selected.content" />
          <pre v-else-if="selected.content_format === 'code' || selected.content_format === 'json'">{{ selected.content }}</pre>
          <MarkdownRenderer v-else :content="selected.content" />
        </template>
        <p v-else class="muted">请选择一个资源查看详情。</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ResourceCard from '../components/ResourceCard.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'
import { useLearningStore } from '../store'
import type { Resource } from '../types'
const store = useLearningStore()
const selected = ref<Resource | null>(null)
const filter = ref('')
const types = computed(() => [...new Set(store.resources.map(r => r.type))])
const filtered = computed(() => filter.value ? store.resources.filter(r => r.type === filter.value) : store.resources)
onMounted(store.refresh)
</script>
