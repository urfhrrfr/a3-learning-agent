<template>
  <section class="panel path-update-result">
    <div class="panel-title">
      <div>
        <h2>路径调整结果</h2>
        <p class="muted compact">展示评估后学习路径如何变化，以及下一步应该做什么。</p>
      </div>
      <span class="status" :class="{ completed: Boolean(path?.steps.length), pending: !path?.steps.length }">
        {{ path?.steps.length ? '已生成' : '待生成' }}
      </span>
    </div>

    <template v-if="path?.steps.length">
      <div class="adjustment-section">
        <b>调整原因</b>
        <p>{{ path.adjustment_reason || report?.feedback || '当前路径暂未返回调整原因。' }}</p>
      </div>

      <article class="next-path-card">
        <span>新的推荐阶段</span>
        <strong>{{ nextStep?.title || path.steps[0].title }}</strong>
        <p>{{ nextStep?.objective || path.steps[0].objective }}</p>
        <small>{{ nextStep?.estimated_minutes || path.steps[0].estimated_minutes }} 分钟</small>
      </article>

      <div v-if="nextResources.length" class="stage-resource-list">
        <article v-for="item in nextResources" :key="item.id" class="stage-resource-item" :class="{ missing: !item.resource }">
          <span>{{ item.resource ? typeLabel(item.resource.type) : '资源未加载' }}</span>
          <strong>{{ item.resource?.title || item.id }}</strong>
          <small>{{ item.resource?.difficulty || '当前资源列表中未找到该 ID' }}</small>
        </article>
      </div>
    </template>

    <div v-else class="empty small-empty">
      <strong>暂无路径调整数据</strong>
      <span>完成评估后，系统将根据薄弱点自动调整学习路径。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessmentReport, LearningPath, Resource } from '../types'

const props = defineProps<{
  path: LearningPath | null
  report: AssessmentReport | null
  resources: Resource[]
}>()

const resourceMap = computed(() => Object.fromEntries(props.resources.map(resource => [resource.id, resource])))
const nextStep = computed(() => props.path?.steps.find(step => step.status !== 'done') || props.path?.steps[0] || null)
const nextResources = computed(() => (nextStep.value?.recommended_resource_ids || []).map(id => ({
  id,
  resource: resourceMap.value[id]
})))

function typeLabel(type: string) {
  const labels: Record<string, string> = {
    lecture_doc: '图文讲解',
    mind_map: '思维导图',
    quiz: '互动练习',
    reading: '拓展阅读',
    media_script: '视频脚本',
    animation_demo: '动画演示',
    html_ppt: 'HTML PPT',
    visual_card: '学习卡片',
    code_case: '代码实验'
  }
  return labels[type] || type
}
</script>
