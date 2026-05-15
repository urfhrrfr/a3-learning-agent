<template>
  <section class="panel profile-version-panel">
    <div class="panel-title">
      <div>
        <h2>画像版本时间线</h2>
        <p class="muted compact">展示画像如何随对话、辅导和评估持续更新。</p>
      </div>
      <span class="status" :class="{ running: loading }">{{ loading ? '加载中' : `${logs.length} 条` }}</span>
    </div>

    <div v-if="logs.length" class="version-timeline">
      <article v-for="log in logs" :key="`${log.version}-${log.updated_at}`" class="version-card">
        <div class="version-marker">v{{ log.version }}</div>
        <div class="version-body">
          <div class="version-head">
            <div>
              <strong>{{ summarizeChange(log) }}</strong>
              <small>{{ formatUpdatedAt(log.updated_at) }} · {{ sourceLabel(getSource(log)) }}</small>
            </div>
            <div class="version-actions">
              <span class="confidence-badge" :class="confidenceClass(log)">
                可信度 {{ formatConfidence(getConfidence(log)) }}
              </span>
              <button
                v-if="canRollback(log)"
                class="btn ghost"
                type="button"
                :disabled="rollbackingVersion === log.version"
                @click="$emit('rollback', log.version)"
              >
                {{ rollbackingVersion === log.version ? '回滚中' : '回滚到此版' }}
              </button>
            </div>
          </div>
          <p class="profile-update-reason">{{ getReason(log) }}</p>
          <div class="field-change-list" v-if="changedFieldKeys(log).length">
            <div class="field-change" v-for="key in changedFieldKeys(log)" :key="key">
              <span>{{ fieldLabel(key) }}</span>
              <strong>{{ renderValue(log.changed_fields[key]?.after) }}</strong>
              <small>之前：{{ renderValue(log.changed_fields[key]?.before) }}</small>
            </div>
          </div>
          <details class="profile-diff">
            <summary>查看 before / after 原始字段</summary>
            <pre>{{ JSON.stringify(log.changed_fields, null, 2) }}</pre>
          </details>
        </div>
      </article>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂无画像更新记录</strong>
      <span>发送画像对话或完成评估后，后端返回的 change-log 会显示在这里。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { ProfileChangeLog } from '../types'

const props = defineProps<{
  logs: ProfileChangeLog[]
  currentVersion?: number
  rollbackingVersion?: number | null
  loading?: boolean
  fieldLabels?: Record<string, string>
}>()

defineEmits<{
  rollback: [version: number]
}>()

function changedFieldKeys(log: ProfileChangeLog) {
  return Object.keys(log.changed_fields || {})
}

function fieldLabel(key: string) {
  return props.fieldLabels?.[key] || key
}

function getConfidence(log: ProfileChangeLog) {
  return log.fusion_meta?.confidence ?? log.extraction_confidence
}

function getSource(log: ProfileChangeLog) {
  return log.fusion_meta?.source || log.extraction_source || 'unknown'
}

function getReason(log: ProfileChangeLog) {
  return log.fusion_meta?.merge_reasoning || log.fusion_reason || '系统根据学习过程更新了画像。'
}

function summarizeChange(log: ProfileChangeLog) {
  const fields = changedFieldKeys(log).map(fieldLabel)
  if (!fields.length) return '本次画像未发生字段变化'
  if (fields.length === 1) return `更新了「${fields[0]}」`
  return `更新了 ${fields.length} 个画像维度：${fields.slice(0, 3).join('、')}${fields.length > 3 ? '等' : ''}`
}

function formatUpdatedAt(value: string) {
  if (!value) return '时间未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    llm: '画像对话/模型识别',
    fallback: '规则兜底',
    user: '用户确认',
    tutor: '智能导师',
    assessment: '练习评估',
    unknown: '未记录'
  }
  return labels[source] || source
}

function confidenceClass(log: ProfileChangeLog) {
  const confidence = getConfidence(log)
  if (typeof confidence !== 'number') return 'unknown'
  if (confidence >= 0.75) return 'high'
  if (confidence >= 0.45) return 'medium'
  return 'low'
}

function formatConfidence(confidence?: number) {
  if (typeof confidence !== 'number') return '-'
  return `${Math.round(confidence * 100)}%`
}

function renderValue(value: unknown) {
  if (Array.isArray(value)) return value.join('、') || '空'
  if (value === null || value === undefined || value === '') return '空'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function canRollback(log: ProfileChangeLog) {
  return Boolean(props.currentVersion && log.version < props.currentVersion)
}
</script>
