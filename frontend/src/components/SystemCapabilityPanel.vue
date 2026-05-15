<template>
  <section class="panel capability-panel">
    <div class="panel-title">
      <h2>学习服务状态</h2>
      <span class="status" :class="healthStatusClass">
        {{ healthStatusLabel }}
      </span>
    </div>

    <div class="capability-grid">
      <div class="capability-item">
        <span>AI 生成模式</span>
        <strong>{{ generationMode }}</strong>
        <small>{{ generationDetail }}</small>
        <small class="tech-line">provider={{ providerName }}</small>
      </div>
      <div class="capability-item">
        <span>实时进度</span>
        <strong>{{ progressMode }}</strong>
        <small>{{ progressDetail }}</small>
        <small class="tech-line">{{ cacheTechLine }}</small>
      </div>
      <div class="capability-item">
        <span>学习数据保存</span>
        <strong>已启用</strong>
        <small>画像、资源、学习路径和评估结果会保留</small>
        <small class="tech-line">storage=SQLite</small>
      </div>
      <div class="capability-item">
        <span>生成流程记录</span>
        <strong>{{ traceCount }} 步</strong>
        <small>{{ completedTraceCount }} 步已完成，可用于查看协作过程</small>
        <small class="tech-line">agent_trace={{ traceCount }}</small>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTrace, HealthStatus } from '../types'

const props = defineProps<{
  health: HealthStatus | null
  traces: AgentTrace[]
}>()

const providerName = computed(() => props.health?.llm_provider || 'unknown')
const traceCount = computed(() => props.traces.length)
const completedTraceCount = computed(() => props.traces.filter(trace => trace.status === 'completed').length)
const healthStatusClass = computed(() => {
  if (!props.health) return 'pending'
  return props.health.status === 'healthy' ? 'completed' : 'failed'
})
const healthStatusLabel = computed(() => {
  if (!props.health) return '检查中'
  return props.health.status === 'healthy' ? '可用' : '受限'
})

const generationMode = computed(() => {
  if (!props.health) return '正在检查'
  return props.health.mock_llm ? '稳定演示' : '智能生成'
})

const generationDetail = computed(() => {
  if (!props.health) return '正在读取后端服务状态'
  return props.health.mock_llm ? '使用兜底内容，适合课堂演示和离线运行' : '正在调用真实模型生成个性化内容'
})

const progressMode = computed(() => {
  const cache = props.health?.cache
  if (!cache) return '正在检查'
  if (!cache.enabled) return '基础同步'
  return cache.available ? '增强同步' : '自动降级'
})

const progressDetail = computed(() => {
  const cache = props.health?.cache
  if (!cache) return '正在读取进度同步方式'
  if (!cache.enabled) return '生成进度会随任务状态更新'
  if (cache.available) return '生成进度和流程记录会更快同步'
  return cache.reason ? `缓存暂不可用，已自动降级：${cache.reason}` : '缓存暂不可用，核心学习流程不受影响'
})

const cacheTechLine = computed(() => {
  const cache = props.health?.cache
  if (!cache) return 'cache=checking'
  if (!cache.enabled) return 'cache=memory'
  return cache.available ? 'cache=Redis' : 'cache=fallback'
})
</script>
