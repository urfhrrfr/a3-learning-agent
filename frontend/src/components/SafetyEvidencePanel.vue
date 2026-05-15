<template>
  <section class="panel safety-panel">
    <div class="panel-title">
      <div>
        <h2>可信生成与依据</h2>
        <p class="muted compact">不新增接口，只汇总健康状态、资源质检、来源和智能体警告。</p>
      </div>
      <span class="status" :class="overallStatusClass">{{ overallStatus }}</span>
    </div>

    <div class="safety-grid">
      <article class="safety-item">
        <span>模型模式</span>
        <strong>{{ modelMode }}</strong>
        <small>{{ modelDetail }}</small>
      </article>
      <article class="safety-item">
        <span>质检通过</span>
        <strong>{{ passedCount }}/{{ resources.length }}</strong>
        <small>{{ blockedCount ? `${blockedCount} 份暂不建议使用` : '未发现 blocked 资源' }}</small>
      </article>
      <article class="safety-item">
        <span>来源依据</span>
        <strong>{{ sourceCount }}</strong>
        <small>{{ selectedResource ? selectedResource.title : '统计当前资源库来源引用' }}</small>
      </article>
      <article class="safety-item">
        <span>运行警告</span>
        <strong>{{ warningCount }}</strong>
        <small>{{ warningCount ? '可展开智能体轨迹查看' : '暂无智能体警告' }}</small>
      </article>
    </div>

    <div class="evidence-list" v-if="evidenceSources.length">
      <article v-for="source in evidenceSources.slice(0, 3)" :key="source.id" class="evidence-row">
        <span>{{ source.id }}</span>
        <p>{{ source.text || source.reason || '该来源暂无文本片段，保留来源编号用于追溯。' }}</p>
      </article>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂无可展示来源片段</strong>
      <span>资源生成完成后，若后端返回 evidence_sources 或 source_refs，会在这里汇总。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTrace, EvidenceSource, HealthStatus, Resource } from '../types'

const props = defineProps<{
  health: HealthStatus | null
  traces: AgentTrace[]
  resources: Resource[]
  selectedResource?: Resource | null
}>()

const passedCount = computed(() => props.resources.filter(resource => resource.review_status === 'passed').length)
const blockedCount = computed(() => props.resources.filter(resource => resource.review_status === 'blocked').length)
const warningCount = computed(() => props.traces.reduce((sum, trace) => sum + trace.warnings.length, 0))
const evidenceSources = computed<EvidenceSource[]>(() => {
  const target = props.selectedResource ? [props.selectedResource] : props.resources
  return target.flatMap(resource => {
    if (resource.evidence_sources?.length) return resource.evidence_sources
    return (resource.source_refs || []).map(id => ({ id, text: '', relevance_score: 0, reason: '' }))
  })
})
const sourceCount = computed(() => evidenceSources.value.length)

const modelMode = computed(() => {
  if (!props.health) return '检查中'
  return props.health.mock_llm ? '演示兜底' : '真实模型'
})
const modelDetail = computed(() => {
  if (!props.health) return '等待后端健康状态'
  return props.health.mock_llm ? '当前使用稳定演示内容，避免无模型环境中断' : `provider=${props.health.llm_provider || 'unknown'}`
})
const overallStatus = computed(() => {
  if (!props.resources.length) return '等待资源'
  if (blockedCount.value) return '需复核'
  if (warningCount.value) return '有提醒'
  return '可信可演示'
})
const overallStatusClass = computed(() => {
  if (blockedCount.value) return 'failed'
  if (warningCount.value) return 'needs_revision'
  return 'completed'
})
</script>
