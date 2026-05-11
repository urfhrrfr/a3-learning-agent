<template>
  <section class="panel trace-panel">
    <div class="panel-title">
      <div>
        <h2>Agent Trace</h2>
        <p class="muted compact">{{ traces.length ? `已记录 ${traces.length} 个协作步骤` : '任务启动后显示智能体协作过程' }}</p>
      </div>
      <span class="status">{{ traces.length ? '可审计' : '等待中' }}</span>
    </div>
    <div v-if="traces.length" class="trace-list">
      <div v-for="(trace, index) in traces" :key="trace.id" class="trace-item">
        <div class="trace-index">{{ index + 1 }}</div>
        <div class="trace-body">
          <div class="split trace-head">
            <div>
              <b>{{ trace.agent }}</b>
              <p class="muted compact">{{ trace.input_summary }}</p>
            </div>
            <div class="trace-badges">
              <span class="status" :class="trace.status">{{ trace.status }}</span>
              <span class="chip provider">{{ providerLabel(trace.llm_provider) }}</span>
              <span v-if="isResourceAgent(trace.agent)" class="chip" :class="usedFallback(trace) ? 'warning' : 'success'">
                {{ usedFallback(trace) ? '模板兜底' : '模型生成' }}
              </span>
            </div>
          </div>
          <p>{{ trace.output_summary }}</p>
          <div class="meta-row">
            <span>置信度 {{ Math.round(trace.confidence * 100) }}%</span>
            <span>重试 {{ trace.retry_count }} 次</span>
            <span v-if="trace.finished_at">完成 {{ trace.finished_at }}</span>
          </div>
          <p class="compact"><b>协作阶段：</b>{{ trace.collaboration_stage || '未标注' }}</p>
          <p class="compact"><b>分工边界：</b>{{ trace.boundary || '未标注' }}</p>
          <p class="compact" v-if="trace.depends_on?.length"><b>依赖上游：</b>{{ trace.depends_on.join(' -> ') }}</p>
          <p class="compact" v-if="trace.arbitration_note"><b>冲突仲裁：</b>{{ trace.arbitration_note }}</p>
          <p class="compact" v-if="trace.review_conclusion"><b>审核结论：</b>{{ trace.review_conclusion }}</p>
          <div class="chips">
            <span v-for="ref in trace.source_refs" :key="ref" class="chip">{{ ref }}</span>
          </div>
          <div v-if="trace.warnings.length" class="chips">
            <span v-for="warning in trace.warnings" :key="warning" class="chip warning">{{ warning }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty">
      生成开始后，这里会展示每个智能体的输入、输出、来源、置信度和状态。
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AgentTrace } from '../types'
defineProps<{ traces: AgentTrace[] }>()

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
