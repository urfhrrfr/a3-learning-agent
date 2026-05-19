<template>
  <div class="page">
    <div class="header resources-header">
      <div>
        <span class="eyebrow">我的学习资料</span>
        <h1>查看生成好的多模态学习材料</h1>
        <p class="muted">讲义、导图、练习、视频脚本、动画演示和代码案例都放在这里。先选一份打开，学完再收藏或屏蔽。</p>
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
          <p class="muted compact">{{ formatDate(selectedHistoryJob.completed_at || selectedHistoryJob.created_at) }} 生成，不会替换本轮资料。</p>
          <button class="btn ghost" type="button" @click="returnToCurrentResources">返回本轮资料</button>
        </section>

        <section class="panel compact-panel">
          <div class="panel-title">
            <div>
              <h2>{{ selectedHistoryJob ? '这个资料包包含' : '本轮材料类型' }}</h2>
              <p class="muted compact">{{ selectedHistoryJob ? '按这次历史生成的资料统计。' : '按生成结果真实统计，不补写空数据。' }}</p>
            </div>
          </div>
          <div v-if="resourceTypeCounts.length" class="multimodal-list">
            <div v-for="item in resourceTypeCounts" :key="item.type">
              <span>{{ typeLabel(item.type) }}</span>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
          <div v-else class="empty small-empty">
            <strong>暂无材料类型</strong>
            <span>生成材料后会显示类型分布。</span>
          </div>
        </section>

        <div class="cards resource-list">
          <ResourceCard
            v-for="r in filtered"
            :key="r.id"
            :resource="r"
            :readonly="!!selectedHistoryJob"
            @select="selected = $event"
            @feedback="handleFeedback"
          />
          <div v-if="!filtered.length" class="empty">
            <strong>{{ activeResources.length ? '这个分类暂时没有材料' : selectedHistoryJob ? '这个历史资料包里暂无材料' : '还没有学习材料' }}</strong>
            <span>{{ activeResources.length ? '这是因为当前筛选条件下没有匹配内容。切回“全部资源”，或重新生成一组更偏这个类型的材料。' : selectedHistoryJob ? '可以返回本轮资料，或选择下方其他历史资料包。' : '这是因为你还没有生成材料。先去描述学习目标，系统会把内容整理成可阅读、可练习的材料包。' }}</span>
            <RouterLink v-if="!selectedHistoryJob && !store.resources.length" class="btn secondary" to="/generate">生成第一套材料</RouterLink>
            <button v-else class="btn ghost" type="button" @click="filter = ''">查看全部资源</button>
          </div>
        </div>
      </section>

      <ResourceContent v-if="selected" :resource="selected" />
      <section v-else class="panel resource-content resource-placeholder">
        <span class="resource-kind">预览</span>
        <h2>选择左侧材料开始学习</h2>
        <p class="muted">打开后会看到正文、导图、练习、脚本、动画场景或代码案例。来源和审核说明收纳在详情底部。</p>
        <RouterLink v-if="!store.resources.length" class="btn secondary" to="/generate">先生成材料</RouterLink>
      </section>
    </div>

    <section class="panel history-panel">
      <div class="panel-title">
        <div>
          <h2>历史生成记录</h2>
          <p class="muted compact">这里保留以前生成的资料包，点击后可以打开里面的学习资料。</p>
        </div>
        <span class="status pending">{{ historicalGenerations.length }} 个资料包</span>
      </div>
      <div v-if="historicalGenerations.length" class="history-package-grid">
        <button
          v-for="job in historicalGenerations"
          :key="job.id"
          class="history-package-card"
          :class="{ active: selectedHistoryJob?.id === job.id }"
          type="button"
          @click="openHistoryJob(job)"
        >
          <div class="history-record-head">
            <div>
              <strong>{{ historyTitle(job) }}</strong>
              <small>{{ formatDate(job.completed_at || job.created_at) }} · {{ job.resources.length }} 份学习资料</small>
            </div>
            <span class="status" :class="statusClass(job.status)">{{ statusLabel(job.status) }}</span>
          </div>
          <div class="history-type-summary">
            <span v-for="item in resourceTypeSummary(job.resources).slice(0, 5)" :key="item.type">{{ typeLabel(item.type) }} {{ item.count }}</span>
          </div>
        </button>
      </div>
      <div v-else class="empty small-empty">
        <strong>暂无历史资料包</strong>
        <span>生成新的资料后，以前的资料包会保存在这里，之后可以随时点开继续学习。</span>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'
import { useLearningStore } from '../store'
import type { GenerationHistoryItem, Resource } from '../types'

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const selectedHistoryJob = ref<GenerationHistoryItem | null>(null)
const filter = ref('')

const typeLabels: Record<string, string> = {
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

const activeResources = computed(() => selectedHistoryJob.value?.resources || store.resources)
const types = computed(() => [...new Set(activeResources.value.map(r => r.type))])
const filtered = computed(() => filter.value ? activeResources.value.filter(r => r.type === filter.value) : activeResources.value)
const favoriteCount = computed(() => store.resources.filter(r => r.user_feedback === 'favorite').length)
const hiddenCount = computed(() => store.resources.filter(r => r.user_feedback === 'hidden').length)
const resourceTypeCounts = computed(() => {
  return resourceTypeSummary(activeResources.value)
})
const historicalGenerations = computed(() => store.resourceHistory.filter(job => !job.is_current))

function typeLabel(type: string) {
  return typeLabels[type] || type
}

function formatDate(value?: string | null) {
  if (!value) return '时间未知'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function historyTitle(job: GenerationHistoryItem) {
  return job.request.goal || job.request.chapter || '历史学习资料包'
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

function openHistoryJob(job: GenerationHistoryItem) {
  selectedHistoryJob.value = job
  filter.value = ''
  selected.value = job.resources[0] || null
}

function returnToCurrentResources() {
  selectedHistoryJob.value = null
  filter.value = ''
  selected.value = store.resources[0] || null
}

onMounted(async () => {
  await store.ensureReady()
  if (!selected.value && filtered.value.length) {
    selected.value = filtered.value[0]
  }
})

watch(filtered, (resources) => {
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
