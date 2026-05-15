<template>
  <section class="panel evidence-panel">
    <div class="panel-title">
      <div>
        <h2>引用来源</h2>
        <p class="muted compact">展示接口已返回的来源编号、引用资源和资源依据片段。</p>
      </div>
      <span class="status">{{ evidenceItems.length }} 条</span>
    </div>

    <div v-if="evidenceItems.length" class="evidence-card-list">
      <article v-for="item in evidenceItems" :key="item.key" class="evidence-card">
        <span>{{ item.type }}</span>
        <strong>{{ item.title }}</strong>
        <p>{{ item.summary }}</p>
        <small>{{ item.hint }}</small>
      </article>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂无引用来源</strong>
      <span>完成资源生成后，导师回答会优先展示引用资源。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Resource, TutorResponse } from '../types'

const props = defineProps<{
  sourceRefs?: string[]
  citedResources?: NonNullable<TutorResponse['cited_resources']>
  resources?: Resource[]
}>()

const evidenceItems = computed(() => {
  const items: Array<{ key: string; type: string; title: string; summary: string; hint: string }> = []
  for (const resource of props.citedResources || []) {
    items.push({
      key: `cited-${resource.id}`,
      type: typeLabel(resource.type),
      title: resource.title,
      summary: `难度：${resource.difficulty}`,
      hint: '来自导师接口返回的 cited_resources'
    })
  }
  for (const ref of props.sourceRefs || []) {
    const matched = props.resources?.find(resource => resource.source_refs?.includes(ref) || resource.id === ref)
    items.push({
      key: `ref-${ref}`,
      type: matched ? typeLabel(matched.type) : '来源编号',
      title: matched?.title || readableRef(ref),
      summary: matched?.audit_reason || matched?.review_reason || '接口返回了来源编号，但未提供原文片段。',
      hint: matched ? '已匹配到当前资源库资源' : '保留原始来源编号用于追溯'
    })
  }
  for (const resource of props.resources || []) {
    for (const source of resource.evidence_sources || []) {
      items.push({
        key: `evidence-${resource.id}-${source.id}`,
        type: typeLabel(resource.type),
        title: resource.title,
        summary: source.text || source.reason || '该依据未返回文本片段。',
        hint: `依据：${source.id}`
      })
    }
  }
  const deduped = new Map<string, typeof items[number]>()
  for (const item of items) {
    if (!deduped.has(item.key)) deduped.set(item.key, item)
  }
  return [...deduped.values()].slice(0, 8)
})

function readableRef(ref: string) {
  const section = ref.includes('#') ? ref.split('#')[1] : ref
  return section.replace(/:\d+$/, '').replace(/_/g, ' ') || ref
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    lecture_doc: '图文讲解',
    mind_map: '思维导图',
    quiz: '互动练习',
    reading: '拓展阅读',
    media_script: '视频脚本',
    animation_demo: '动画演示',
    ppt_draft: 'PPT 草稿',
    visual_card: '学习卡片',
    code_case: '代码实验'
  }
  return labels[type] || type
}
</script>
