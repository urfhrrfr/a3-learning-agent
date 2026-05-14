<template>
  <div class="page">
    <div class="header"><h1>学习画像</h1></div>
    <div class="grid">
      <ChatPanel class="span-7" :loading="loading" @send="send" />
      <ProfileInsightPanel class="span-5" :profile="store.profile" />
      <section class="panel span-12">
        <div class="panel-title">
          <h2>画像维度清单与更新规则</h2>
        </div>
        <table class="storyboard-table" v-if="dimensions.length">
          <thead>
            <tr>
              <th>维度</th>
              <th>字段</th>
              <th>取值类型</th>
              <th>定义</th>
              <th>更新策略</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in dimensions" :key="item.key">
              <td>{{ item.label }}</td>
              <td><code>{{ item.key }}</code></td>
              <td>{{ item.value_type }}</td>
              <td>{{ item.description }}</td>
              <td>{{ item.update_rule }}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <section class="panel span-12">
        <div class="panel-title">
          <div>
            <h2>随学随新：画像更新记录</h2>
            <p class="muted compact">默认只展示本次更新了什么、为什么更新，以及系统判断的可信程度。</p>
          </div>
        </div>
        <div v-if="changeLogs.length" class="profile-update-list">
          <article class="profile-update-card" v-for="log in changeLogs.slice(0, 8)" :key="`${log.version}-${log.updated_at}`">
            <div class="profile-update-head">
              <div>
                <span class="profile-version">v{{ log.version }}</span>
                <h3>{{ summarizeChange(log) }}</h3>
              </div>
              <span class="confidence-badge" :class="confidenceClass(log)">
                可信度 {{ formatConfidence(getConfidence(log)) }}
              </span>
            </div>
            <p class="profile-update-reason">{{ getReason(log) }}</p>
            <div class="profile-update-meta">
              <span>来自：{{ sourceLabel(getSource(log)) }}</span>
              <span>{{ formatUpdatedAt(log.updated_at) }}</span>
            </div>
            <div class="field-change-list" v-if="changedFieldKeys(log).length">
              <div class="field-change" v-for="key in changedFieldKeys(log)" :key="key">
                <span>{{ fieldLabel(key) }}</span>
                <strong>{{ renderAfterValue(log, key) }}</strong>
              </div>
            </div>
            <p v-else class="muted compact">这次对话没有改变已有画像字段。</p>
            <details class="profile-evidence">
              <summary>查看依据与版本细节</summary>
              <div class="profile-evidence-grid">
                <div>
                  <span>触发语句</span>
                  <p>{{ log.trigger_message || '未记录' }}</p>
                </div>
                <div>
                  <span>识别到的信息</span>
                  <div class="chips">
                    <span class="chip" v-for="key in Object.keys(log.extracted)" :key="key">{{ fieldLabel(key) }}</span>
                    <span v-if="!Object.keys(log.extracted).length" class="chip">暂无提取字段</span>
                  </div>
                </div>
              </div>
              <details class="profile-diff" v-if="hasFusionMeta(log)">
                <summary>审计元信息</summary>
                <pre>{{ renderFusionMeta(log) }}</pre>
              </details>
              <details class="profile-diff">
                <summary>字段 before/after 对比</summary>
                <pre>{{ renderChangedFields(log.changed_fields) }}</pre>
              </details>
            </details>
          </article>
        </div>
        <p v-else class="muted">暂无画像变更记录，发送一条画像对话后会自动记录。</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'
import ProfileInsightPanel from '../components/ProfileInsightPanel.vue'
import { useLearningStore } from '../store'
import type { ProfileChangeLog, ProfileDimension } from '../types'

const store = useLearningStore()
const dimensions = ref<ProfileDimension[]>([])
const changeLogs = ref<ProfileChangeLog[]>([])

const fieldLabels: Record<string, string> = {
  knowledge_base: '知识基础',
  learning_goal: '学习目标',
  cognitive_style: '认知风格',
  preferred_modalities: '偏好形式',
  time_budget: '时间安排',
  weak_points: '薄弱点',
  mistake_patterns: '错误模式',
  interests: '兴趣方向',
  mastery: '掌握度'
}

async function loadProfileMeta() {
  const [dimensionRows, logs] = await Promise.all([api.profileDimensions(), api.profileChangeLog()])
  dimensions.value = dimensionRows
  changeLogs.value = logs
}

onMounted(async () => {
  await store.ensureReady()
  await loadProfileMeta()
})

const loading = ref(false)

async function send(message: string) {
  loading.value = true
  await store.sendProfileMessage(message)
  await loadProfileMeta()
  loading.value = false
}

function changedFieldKeys(log: ProfileChangeLog) {
  return Object.keys(log.changed_fields || {})
}

function fieldLabel(key: string) {
  const dimension = dimensions.value.find((item) => item.key === key)
  return fieldLabels[key] || dimension?.label || key
}

function getConfidence(log: ProfileChangeLog) {
  return log.fusion_meta?.confidence ?? log.extraction_confidence
}

function getSource(log: ProfileChangeLog) {
  return log.fusion_meta?.source || log.extraction_source || 'unknown'
}

function getReason(log: ProfileChangeLog) {
  return log.fusion_meta?.merge_reasoning || log.fusion_reason || '系统根据本次对话更新了学习画像。'
}

function summarizeChange(log: ProfileChangeLog) {
  const fields = changedFieldKeys(log).map(fieldLabel)
  if (!fields.length) return '本次画像未发生字段变化'
  if (fields.length === 1) return `更新了「${fields[0]}」`
  return `更新了 ${fields.length} 个画像维度`
}

function renderAfterValue(log: ProfileChangeLog, key: string) {
  const value = log.changed_fields?.[key]?.after
  if (Array.isArray(value)) return value.join('、') || '空'
  if (value === null || value === undefined || value === '') return '空'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

function formatUpdatedAt(value: string) {
  if (!value) return '时间未记录'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function sourceLabel(source: string) {
  const labels: Record<string, string> = {
    llm: '模型识别',
    fallback: '规则兜底',
    user: '用户确认',
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

function renderChangedFields(changedFields: ProfileChangeLog['changed_fields']) {
  return JSON.stringify(changedFields, null, 2)
}

function formatConfidence(confidence?: number) {
  if (typeof confidence !== 'number') return '-'
  return `${Math.round(confidence * 100)}%`
}

function hasFusionMeta(log: ProfileChangeLog) {
  return Boolean(log.fusion_meta || log.conflicts?.length || log.fusion_reason)
}

function renderFusionMeta(log: ProfileChangeLog) {
  return JSON.stringify({
    source: getSource(log),
    confidence: getConfidence(log),
    changed_fields: log.fusion_meta?.changed_fields,
    conflicts: log.fusion_meta?.conflicts || log.conflicts,
    merge_reasoning: getReason(log)
  }, null, 2)
}
</script>
