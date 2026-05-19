<template>
  <article class="panel resource-card clean-resource-card" :class="{ compact: props.compact }">
    <div class="resource-card-head">
      <div class="resource-title-block">
        <span class="resource-kind">{{ typeLabel }}</span>
        <h2>{{ resource.title }}</h2>
      </div>
    </div>

    <p class="resource-summary-text">{{ summaryText }}</p>

    <div class="task-hint">
      <span>适合我的原因</span>
      <strong>{{ audienceLabel }}</strong>
    </div>

    <p v-if="resource.review_status === 'needs_revision'" class="soft-note">
      内容可先查看，完整质检说明在详情页。
    </p>

    <div class="resource-actions">
      <button class="btn secondary" type="button" @click="$emit('select', resource)">开始学习</button>
      <button class="btn ghost" type="button" @click="$emit('select', resource)">查看详情</button>
      <button
        v-if="!props.readonly"
        class="btn ghost"
        type="button"
        :disabled="resource.user_feedback === 'favorite'"
        @click="$emit('feedback', resource, 'favorite')"
      >
        收藏
      </button>
      <button
        v-if="!props.readonly"
        class="btn ghost"
        type="button"
        :disabled="resource.user_feedback === 'hidden'"
        @click="$emit('feedback', resource, 'hidden')"
      >
        屏蔽
      </button>
      <button
        v-if="!props.readonly && resource.user_feedback !== 'neutral'"
        class="btn ghost"
        type="button"
        @click="$emit('feedback', resource, 'neutral')"
      >
        恢复
      </button>
    </div>
    <div v-if="feedbackLabel" class="feedback-state">
      <span>{{ feedbackLabel }}</span>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Resource } from '../types'

const props = defineProps<{ resource: Resource; compact?: boolean; readonly?: boolean }>()

defineEmits<{
  select: [resource: Resource]
  feedback: [resource: Resource, action: Resource['user_feedback']]
}>()

const typeLabels: Record<string, string> = {
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

const formatLabels: Record<Resource['content_format'], string> = {
  markdown: '文档',
  mermaid: '图示',
  json: '互动',
  code: '代码'
}

const typeLabel = computed(() => typeLabels[props.resource.type] || props.resource.type)
const formatLabel = computed(() => formatLabels[props.resource.content_format])
const summaryText = computed(() => {
  return `${formatLabel.value}资料，适合用于${props.resource.difficulty || '当前阶段'}学习。`
})

const audienceLabel = computed(() => {
  if (props.resource.personalized_reason) return props.resource.personalized_reason
  const tags = props.resource.target_profile.filter(Boolean).slice(0, 3)
  return tags.length ? tags.join(' / ') : '适合当前学习目标'
})

const feedbackLabel = computed(() => {
  if (props.resource.user_feedback === 'favorite') return '已收藏，后续推荐会优先考虑'
  if (props.resource.user_feedback === 'hidden') return '已屏蔽，后续推荐会降低权重'
  return ''
})
</script>
