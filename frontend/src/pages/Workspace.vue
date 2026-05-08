<template>
  <div class="page">
    <div class="header">
      <div>
        <h1>学习工作台</h1>
        <p class="muted">从画像、资源、路径到评估的完整演示闭环。</p>
      </div>
      <button class="btn" @click="store.generateResources" :disabled="store.loading">生成个性化资源</button>
    </div>
    <div class="grid">
      <ProfileInsightPanel class="span-4" :profile="store.profile" />
      <LearningPathTimeline class="span-8" :path="store.path" />
      <GenerationProgress class="span-4" :progress="store.progress" :loading="store.loading" />
      <section class="panel span-8">
        <h2>最近资源</h2>
        <div class="cards"><ResourceCard v-for="r in store.resources.slice(0, 3)" :key="r.id" :resource="r" @select="selected = $event" /></div>
      </section>
      <section v-if="selected" class="panel span-12 resource-content">
        <h2>{{ selected.title }}</h2>
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
import ProfileInsightPanel from '../components/ProfileInsightPanel.vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import GenerationProgress from '../components/GenerationProgress.vue'
import ResourceCard from '../components/ResourceCard.vue'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'

const store = useLearningStore()
const selected = ref<Resource | null>(null)
onMounted(store.refresh)
</script>
