<template>
  <div class="page">
    <div class="header resources-header">
      <div>
        <span class="eyebrow">我的学习资料</span>
        <h1>查看生成好的学习材料</h1>
        <p class="muted">可以查看本轮资料，也可以按需打开历史资料包。</p>
      </div>
      <select v-model="filter" :disabled="!types.length" aria-label="筛选资源类型">
        <option value="">全部资源</option>
        <option v-for="t in types" :key="t" :value="t">{{ typeLabel(t) }}</option>
      </select>
    </div>

    <div class="resource-workspace">
      <section class="resource-sidebar">
        <div v-if="store.error && !store.resources.length" class="empty error-state">
          <strong>资源库暂时无法同步</strong>
          <span>{{ store.error }}</span>
          <button class="btn secondary" type="button" @click="store.refresh">重新同步</button>
        </div>

        <div class="resource-summary">
          <div>
            <span>{{ selectedHistoryJob ? '历史资料' : '可学习' }}</span>
            <strong>{{ activeResources.length }}</strong>
          </div>
          <div>
            <span>{{ selectedHistoryJob ? '资料类型' : '已收藏' }}</span>
            <strong>{{ selectedHistoryJob ? resourceTypeCounts.length : favoriteCount }}</strong>
          </div>
          <div>
            <span>{{ selectedHistoryJob ? '查看方式' : '不适合' }}</span>
            <strong>{{ selectedHistoryJob ? '只读' : hiddenCount }}</strong>
          </div>
        </div>

        <section v-if="selectedHistoryJob" class="panel compact-panel active-history-note">
          <span class="eyebrow">正在查看历史资料包</span>
          <h2>{{ historyTitle(selectedHistoryJob) }}</h2>
          <p class="muted compact">{{ formatDate(selectedHistoryJob.completed_at || selectedHistoryJob.created_at) }} 生成。</p>
          <button class="btn ghost" type="button" @click="returnToCurrentResources">返回本轮资料</button>
        </section>

        <section class="panel compact-panel">
          <div class="panel-title">
            <div>
              <h2>{{ selectedHistoryJob ? '资料包类型' : '本轮材料类型' }}</h2>
              <p class="muted compact">按当前已加载的资源统计。</p>
            </div>
          </div>
          <div v-if="resourceTypeCounts.length" class="multimodal-list">
            <div v-for="item in resourceTypeCounts" :key="item.type">
              <span>{{ typeLabel(item.type) }}</span>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
          <div v-else class="empty small-empty">
            <strong>{{ store.historyDetailLoadingId ? '正在加载资料包' : '暂无资料类型' }}</strong>
            <span>{{ store.historyDetailLoadingId ? '正在读取资料包详情。' : '生成资料后会显示类型统计。' }}</span>
          </div>
        </section>

        <div v-if="filtered.length" class="resource-list-head">
          <div>
            <strong>{{ selectedHistoryJob ? '资料包内容' : '本轮学习资料' }}</strong>
            <span>{{ filtered.length }} 份资料</span>
          </div>
          <button
            v-if="filtered.length > collapsedResourceLimit"
            class="btn ghost"
            type="button"
            @click="resourcesExpanded = !resourcesExpanded"
          >
            {{ resourcesExpanded ? '收起资料' : `展开全部 ${filtered.length} 份` }}
          </button>
        </div>

        <div class="cards resource-list" :class="{ expanded: resourcesExpanded }">
          <ResourceCard
            v-for="r in visibleResources"
            :key="r.id"
            :resource="r"
            compact
            :readonly="!!selectedHistoryJob"
            @select="selected = $event"
            @feedback="handleFeedback"
          />
          <div v-if="!filtered.length" class="empty">
            <strong>{{ store.historyDetailLoadingId ? '正在加载历史资料包' : activeResources.length ? '当前筛选下没有资料' : selectedHistoryJob ? '这个资料包暂无内容' : '还没有学习资料' }}</strong>
            <span>{{ store.historyDetailLoadingId ? '正在读取所选资料包详情。' : '可以切换筛选条件，或先生成一组资料。' }}</span>
            <RouterLink v-if="!selectedHistoryJob && !store.resources.length && !store.historyDetailLoadingId" class="btn secondary" to="/generate">生成资料</RouterLink>
            <button v-else class="btn ghost" type="button" @click="filter = ''">查看全部</button>
          </div>
        </div>
      </section>

      <ResourceContent v-if="selected" :resource="selected" />
      <section v-else class="panel resource-content resource-placeholder">
        <span class="resource-kind">预览</span>
        <h2>选择一份资料开始学习</h2>
        <p class="muted">选中的学习材料会显示在这里。</p>
        <RouterLink v-if="!store.resources.length" class="btn secondary" to="/generate">先生成资料</RouterLink>
      </section>
    </div>

    <section class="panel history-panel">
      <div class="panel-title">
        <div>
          <h2>历史资料包</h2>
          <p class="muted compact">这里先展示轻量摘要，点击后再加载完整详情。</p>
        </div>
        <span class="status pending">{{ historicalGenerations.length }} 个资料包</span>
      </div>
      <div v-if="historicalGenerations.length" class="history-package-stack" :class="{ expanded: historyExpanded }">
        <button
          v-for="job in visibleHistoryGenerations"
          :key="job.id"
          class="history-package-row"
          :class="{ active: selectedHistoryJob?.id === job.id || store.historyDetailLoadingId === job.id }"
          type="button"
          @click="openHistoryJob(job)"
        >
          <div class="history-record-head">
            <div>
              <strong>{{ historyTitle(job) }}</strong>
              <small>{{ formatDate(job.completed_at || job.created_at) }} · {{ job.resource_count }} 份资料</small>
            </div>
            <span class="status" :class="statusClass(job.status)">{{ statusLabel(job.status) }}</span>
          </div>
          <div class="history-type-summary">
            <span v-for="item in job.resource_type_counts.slice(0, 5)" :key="item.type">{{ typeLabel(item.type) }} {{ item.count }}</span>
          </div>
        </button>
      </div>
      <button
        v-if="historicalGenerations.length > collapsedHistoryLimit"
        class="history-toggle"
        type="button"
        @click="historyExpanded = !historyExpanded"
      >
        <span>{{ historyExpanded ? '收起历史记录' : `展开全部 ${historicalGenerations.length} 个资料包` }}</span>
        <strong>{{ historyExpanded ? '上收' : '下拉' }}</strong>
      </button>
      <div v-else class="empty small-empty">
        <strong>暂无历史资料包</strong>
        <span>生成新的资料后，历史资料包会保存在这里。</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'
import { useLearningStore } from '../store'
import type { GenerationHistoryItem, GenerationHistorySummary, Resource } from '../types'

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const selectedHistoryJob = ref<GenerationHistoryItem | null>(null)
const requestedHistoryJobId = ref('')
const filter = ref('')
const historyExpanded = ref(false)
const collapsedHistoryLimit = 3
const resourcesExpanded = ref(false)
const collapsedResourceLimit = 4

const typeLabels: Record<string, string> = {
  lecture_doc: '图文讲解',
  mind_map: '思维导图',
  quiz: '互动练习',
  reading: '拓展阅读',
  media_script: '视频脚本',
  animation_demo: '动画演示',
  ppt_draft: 'PPT 草稿',
  visual_card: '学习卡片',
  code_case: '代码案例'
}

const activeResources = computed(() => selectedHistoryJob.value?.resources || (requestedHistoryJobId.value ? [] : store.resources))
const types = computed(() => [...new Set(activeResources.value.map(r => r.type))])
const filtered = computed(() => filter.value ? activeResources.value.filter(r => r.type === filter.value) : activeResources.value)
const visibleResources = computed(() => resourcesExpanded.value ? filtered.value : filtered.value.slice(0, collapsedResourceLimit))
const favoriteCount = computed(() => store.resources.filter(r => r.user_feedback === 'favorite').length)
const hiddenCount = computed(() => store.resources.filter(r => r.user_feedback === 'hidden').length)
const resourceTypeCounts = computed(() => resourceTypeSummary(activeResources.value))
const historicalGenerations = computed(() => store.resourceHistory.filter(job => !job.is_current))
const visibleHistoryGenerations = computed(() => historyExpanded.value ? historicalGenerations.value : historicalGenerations.value.slice(0, collapsedHistoryLimit))

function typeLabel(type: string) {
  return typeLabels[type] || type
}

function formatDate(value?: string | null) {
  if (!value) return '时间未知'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function historyTitle(job: GenerationHistoryItem | GenerationHistorySummary) {
  return job.request.goal || job.request.chapter || '历史资料包'
}

function resourceTypeSummary(resources: Resource[]) {
  const counts = new Map<string, number>()
  for (const resource of resources) counts.set(resource.type, (counts.get(resource.type) || 0) + 1)
  return [...counts.entries()].map(([type, count]) => ({ type, count }))
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    completed: '已完成',
    running: '生成中',
    queued: '等待生成',
    failed: '生成失败'
  }
  return labels[status] || '已保存'
}

function statusClass(status: string) {
  if (status === 'failed') return 'failed'
  if (status === 'running' || status === 'queued') return 'pending'
  return 'completed'
}

async function openHistoryJob(job: GenerationHistorySummary) {
  requestedHistoryJobId.value = job.id
  selectedHistoryJob.value = store.resourceHistoryDetails[job.id] || null
  filter.value = ''
  resourcesExpanded.value = false
  selected.value = selectedHistoryJob.value?.resources[0] || null
  try {
    const detail = await store.loadResourceHistoryDetail(job.id)
    if (requestedHistoryJobId.value !== job.id) return
    selectedHistoryJob.value = detail
    selected.value = detail.resources[0] || null
  } catch {
    if (requestedHistoryJobId.value === job.id) returnToCurrentResources()
  }
}

function returnToCurrentResources() {
  requestedHistoryJobId.value = ''
  selectedHistoryJob.value = null
  filter.value = ''
  resourcesExpanded.value = false
  selected.value = store.resources[0] || null
}

onMounted(async () => {
  await store.ensureReady()
  if (!selected.value && filtered.value.length) {
    selected.value = filtered.value[0]
  }
})

watch(filtered, (resources) => {
  resourcesExpanded.value = false
  if (!resources.length) {
    selected.value = null
    return
  }
  if (!selected.value || !resources.some(resource => resource.id === selected.value?.id)) {
    selected.value = resources[0]
  }
})

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  if (selectedHistoryJob.value) return
  await store.submitResourceFeedback(resource.id, action)
  if (selected.value?.id === resource.id) {
    selected.value = store.resources.find(r => r.id === resource.id) || selected.value
  }
}
</script>
