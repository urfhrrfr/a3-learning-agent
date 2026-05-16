<template>
  <article class="path-stage-card" :class="step.status">
    <div class="stage-card-head">
      <div>
        <span class="stage-number">阶段 {{ index + 1 }}</span>
        <h3>{{ step.title }}</h3>
      </div>
      <span class="status" :class="statusClass">{{ statusLabel }}</span>
    </div>

    <p class="stage-objective">{{ step.objective }}</p>

    <div class="stage-meta-row">
      <span>预计 {{ step.estimated_minutes }} 分钟</span>
      <span>{{ resolvedResources.length }} 份推荐资源</span>
    </div>

    <div class="task-block">
      <b>推荐学习任务</b>
      <p>{{ taskText }}</p>
    </div>

    <div class="recommended-resources">
      <b>推荐资源</b>
      <div v-if="resolvedResources.length" class="stage-resource-list">
        <article
          v-for="item in resolvedResources"
          :key="item.id"
          class="stage-resource-item"
          :class="{ missing: !item.resource }"
        >
          <span>{{ item.resource ? typeLabel(item.resource.type) : '资源待同步' }}</span>
          <strong>{{ item.resource?.title || '推荐资源暂未同步到材料库' }}</strong>
          <small>{{ item.resource ? item.resource.difficulty : '请先同步材料库或重新生成资源' }}</small>
        </article>
      </div>
      <p v-else class="muted compact">该阶段暂无绑定资源。</p>
    </div>

    <div class="reason-box">
      <span>个性化推荐原因</span>
      <p>{{ step.reason || '系统暂未返回推荐原因。' }}</p>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LearningPathStep, Resource } from '../types'

const props = defineProps<{
  step: LearningPathStep
  index: number
  resourceMap: Record<string, Resource>
}>()

const resolvedResources = computed(() => props.step.recommended_resource_ids.map(id => ({
  id,
  resource: props.resourceMap[id]
})))

const statusLabel = computed(() => {
  if (props.step.status === 'done') return '已完成'
  if (props.step.status === 'doing') return '进行中'
  return '未开始'
})

const statusClass = computed(() => {
  if (props.step.status === 'done') return 'completed'
  if (props.step.status === 'doing') return 'running'
  return 'pending'
})

const taskText = computed(() => {
  const titles = resolvedResources.value
    .map(item => item.resource?.title)
    .filter(Boolean)
    .slice(0, 2)
  if (titles.length) return `优先学习「${titles.join('」和「')}」，再根据阶段目标完成练习或复盘。`
  return '按阶段目标学习推荐内容，资源未加载时可先回到材料库同步资源。'
})

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
