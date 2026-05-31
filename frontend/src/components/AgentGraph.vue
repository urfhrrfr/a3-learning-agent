<template>
  <section class="panel agent-graph-panel">
    <div class="panel-title">
      <div>
        <h2>生成协作说明</h2>
        <p class="muted compact">{{ traces.length ? '展示学习资料从规划到审核的生成过程。' : '生成任务启动后会展示协作过程。' }}</p>
      </div>
      <span class="status" :class="{ running: loading }">{{ loading ? '协作中' : traces.length ? '有记录' : '等待中' }}</span>
    </div>

    <div v-if="nodes.length" class="agent-graph">
      <article
        v-for="node in nodes"
        :key="node.id"
        class="agent-node"
        :class="[node.status, { fallback: node.fallback }]"
      >
        <span class="agent-node-role">{{ node.stage }}</span>
        <strong>{{ node.label }}</strong>
        <small>{{ node.summary }}</small>
        <div class="agent-node-foot">
          <span>{{ statusLabel(node.status) }}</span>
          <em>{{ Math.round(node.confidence * 100) }}%</em>
        </div>
      </article>
    </div>

    <div v-else class="agent-graph-empty">
      <strong>等待一次资源生成任务</strong>
      <span>这里会展示资料规划、内容生成和审核的协作过程。</span>
      <RouterLink class="btn ghost" to="/generate">去生成资源</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTrace } from '../types'

const props = defineProps<{
  traces: AgentTrace[]
  loading?: boolean
}>()

const agentLabels: Record<string, string> = {
  KnowledgeAgent: '知识检索',
  PlannerAgent: '学习规划',
  LectureAgent: '讲解文档',
  MindMapAgent: '思维导图',
  QuizAgent: '练习题',
  ReadingAgent: '拓展阅读',
  MediaAgent: '视频脚本',
  PPTDraftAgent: 'HTML PPT',
  VisualCardAgent: '学习卡片',
  CodeCaseAgent: '代码实验',
  ReviewAgent: '质量检查'
}

const nodes = computed(() => props.traces.map(trace => ({
  id: trace.id,
  label: agentLabels[trace.agent] || trace.agent,
  stage: trace.collaboration_stage || trace.agent,
  summary: cleanText(trace.output_summary || trace.input_summary || '等待输出'),
  status: trace.status,
  confidence: trace.confidence || 0,
  fallback: trace.output_summary.includes('模板兜底') || trace.warnings.some(item => item.includes('fallback') || item.includes('回退'))
})))

function cleanText(value: string) {
  const cleaned = value
    .replace(/\s*\[来源:\s*[^\]]+?\]/g, '')
    .replace(/\s*\[Source:\s*[^\]]+?\]/gi, '')
    .trim()
  return cleaned.length > 68 ? `${cleaned.slice(0, 68)}...` : cleaned
}

function statusLabel(status: AgentTrace['status']) {
  if (status === 'completed') return '完成'
  if (status === 'running') return '运行中'
  if (status === 'failed') return '失败'
  return '等待'
}
</script>
