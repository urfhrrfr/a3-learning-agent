<template>
  <article class="panel resource-card">
    <div class="panel-title">
      <div>
        <h2>{{ resource.title }}</h2>
        <p class="muted compact">{{ resource.target_profile.filter(Boolean).join(' / ') || '通用学习画像' }}</p>
      </div>
      <span class="status" :class="resource.review_status">{{ reviewLabel }}</span>
    </div>
    <div class="resource-meta">
      <span>{{ typeLabel }}</span>
      <span>{{ formatLabel }}</span>
      <span>{{ resource.difficulty }}</span>
    </div>
    <div class="chips">
      <span class="chip" v-for="ref in resource.source_refs.slice(0, 2)" :key="ref">{{ ref }}</span>
      <span v-if="resource.source_refs.length > 2" class="chip">+{{ resource.source_refs.length - 2 }} 来源</span>
    </div>
    <div class="meta-row">
      <span>{{ resource.created_by_agents.length }} 个智能体</span>
      <span>{{ resource.created_at }}</span>
    </div>
    <p class="review-note">
      审核说明：{{ resource.audit_reason || resource.review_reason || '暂无审核说明' }}
      <span class="muted">confidence: {{ resource.review_confidence.toFixed(2) }}</span>
    </p>
    <div v-if="resource.review_notes?.length" class="review-notes">
      <span class="chip" v-for="note in resource.review_notes.slice(0, 2)" :key="note">{{ note }}</span>
    </div>
    <div class="resource-actions">
      <button class="btn secondary" type="button" @click="$emit('select', resource)">查看内容</button>
      <button class="btn ghost" type="button" :disabled="resource.user_feedback === 'favorite'" @click="$emit('feedback', resource, 'favorite')">收藏</button>
      <button class="btn ghost" type="button" :disabled="resource.user_feedback === 'hidden'" @click="$emit('feedback', resource, 'hidden')">屏蔽</button>
      <button v-if="resource.user_feedback !== 'neutral'" class="btn ghost" type="button" @click="$emit('feedback', resource, 'neutral')">恢复</button>
    </div>
    <div class="feedback-state">
      <span>{{ feedbackLabel }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Resource } from '../types'
const props = defineProps<{ resource: Resource }>()
defineEmits<{
  select: [resource: Resource]
  feedback: [resource: Resource, action: Resource['user_feedback']]
}>()

const typeLabels: Record<string, string> = {
  lecture_doc: '图文讲解',
  mind_map: '思维导图',
  quiz: '交互练习',
  reading: '拓展阅读',
  media_script: '视频脚本',
  animation_demo: '可播放动画',
  ppt_draft: 'PPT 大纲',
  visual_card: '学习卡片',
  code_case: '代码实验'
}

const formatLabels: Record<Resource['content_format'], string> = {
  markdown: 'Markdown',
  mermaid: 'Mermaid',
  json: '结构化',
  code: '代码'
}

const typeLabel = computed(() => typeLabels[props.resource.type] || props.resource.type)
const formatLabel = computed(() => formatLabels[props.resource.content_format])

const reviewLabel = computed(() => {
  if (props.resource.review_status === 'passed') return '已通过'
  if (props.resource.review_status === 'needs_revision') return '需修订'
  return '已阻止'
})

const feedbackLabel = computed(() => {
  if (props.resource.user_feedback === 'favorite') return '已收藏，后续推荐会优先考虑'
  if (props.resource.user_feedback === 'hidden') return '已屏蔽，后续推荐会降低权重'
  return '未反馈'
})
</script>
