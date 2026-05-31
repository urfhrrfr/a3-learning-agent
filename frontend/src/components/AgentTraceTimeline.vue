<template>
  <section class="panel trace-panel">
    <div class="panel-title">
      <div>
        <h2>生成过程</h2>
        <p class="muted compact">{{ traces.length ? `已完成 ${traces.length} 个协作步骤` : '任务启动后展示生成进度' }}</p>
      </div>
      <span class="status">{{ traces.length ? '运行记录' : '等待中' }}</span>
    </div>

    <div v-if="traces.length" class="trace-list">
      <div v-for="(trace, index) in traces" :key="trace.id" class="trace-item">
        <div class="trace-index">{{ index + 1 }}</div>
        <div class="trace-body">
          <div class="split trace-head">
            <div>
              <b>{{ agentLabel(trace.agent) }}</b>
              <p class="muted compact">{{ cleanTraceText(trace.input_summary) }}</p>
            </div>
            <div class="trace-badges">
              <span class="status" :class="trace.status">{{ statusLabel(trace.status) }}</span>
              <span v-if="isResourceAgent(trace.agent)" class="chip" :class="usedFallback(trace) ? 'warning' : 'success'">
                {{ usedFallback(trace) ? '模板辅助' : '模型生成' }}
              </span>
            </div>
          </div>

          <p>{{ cleanTraceText(trace.output_summary) }}</p>

          <details class="trace-details">
            <summary>查看技术细节</summary>
            <div class="trace-detail-grid">
              <span>模型：{{ providerLabel(trace.llm_provider) }}</span>
              <span>置信度：{{ Math.round(trace.confidence * 100) }}%</span>
              <span>重试：{{ trace.retry_count }} 次</span>
              <span v-if="trace.finished_at">完成：{{ trace.finished_at }}</span>
            </div>
            <p class="compact" v-if="trace.collaboration_stage"><b>阶段：</b>{{ trace.collaboration_stage }}</p>
            <p class="compact" v-if="trace.boundary"><b>边界：</b>{{ cleanTraceText(trace.boundary) }}</p>
            <p class="compact" v-if="trace.depends_on?.length"><b>上游：</b>{{ trace.depends_on.join(' -> ') }}</p>
            <p class="compact" v-if="trace.arbitration_note"><b>仲裁：</b>{{ cleanTraceText(trace.arbitration_note) }}</p>
            <p class="compact" v-if="trace.review_conclusion"><b>审核：</b>{{ cleanTraceText(trace.review_conclusion) }}</p>
            <div v-if="trace.source_refs.length" class="chips">
              <span v-for="(ref, refIndex) in trace.source_refs" :key="ref" class="chip">{{ sourceLabel(ref, refIndex) }}</span>
            </div>
            <div v-if="trace.warnings.length" class="chips">
              <span v-for="warning in trace.warnings" :key="warning" class="chip warning">{{ cleanTraceText(warning) }}</span>
            </div>
          </details>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      生成开始后，这里会展示每个步骤的简要进度。
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AgentTrace } from '../types'

defineProps<{ traces: AgentTrace[] }>()

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

function cleanTraceText(value: string) {
  return value
    .replace(/\s*\[来源:\s*[^\]]+?\]/g, '')
    .replace(/\s*\[Source:\s*[^\]]+?\]/gi, '')
}

function sourceLabel(ref: string, index: number) {
  const section = ref.includes('#') ? ref.split('#')[1] : ref
  const readable = section
    .replace(/:\d+$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, char => char.toUpperCase())
  return `依据 ${index + 1}：${readable}`
}

function agentLabel(agent: string) {
  return agentLabels[agent] || agent
}

function statusLabel(status: AgentTrace['status']) {
  if (status === 'completed') return '完成'
  if (status === 'running') return '运行中'
  if (status === 'failed') return '失败'
  return '等待'
}

function providerLabel(provider: string) {
  if (provider === 'spark') return '星火模型'
  if (provider === 'mock') return 'Mock'
  return provider || '未标注模型'
}

function isResourceAgent(agent: string) {
  return [
    'LectureAgent',
    'MindMapAgent',
    'QuizAgent',
    'ReadingAgent',
    'MediaAgent',
    'PPTDraftAgent',
    'VisualCardAgent',
    'CodeCaseAgent'
  ].includes(agent)
}

function usedFallback(trace: AgentTrace) {
  return trace.output_summary.includes('模板兜底') || trace.warnings.some(item => item.includes('回退') || item.includes('fallback'))
}
</script>
