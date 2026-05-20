<template>
  <div class="page generate-page ai-studio-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">生成学习资料</span>
        <h1>告诉我你想学什么</h1>
        <p>输入学习需求后，系统会生成讲解、导图、练习、脚本、代码等多种学习材料。</p>
      </div>
      <div class="generate-hero-visual-card" aria-label="资源生成状态">
        <img class="generate-hero-visual-image" :src="resourceGenerationHero" alt="学习资料生成" />
        <div>
          <span>生成状态</span>
          <strong>{{ store.loading ? `${Math.round(store.progress)}%` : store.resources.length ? '已生成' : '待提交' }}</strong>
          <small>{{ store.loading ? friendlyGenerationStep : resultSubtitle }}</small>
        </div>
      </div>
    </section>

    <div class="quiet-workspace">
      <main class="studio-main">
        <section class="panel composer-panel studio-composer">
          <div class="panel-title">
            <div>
              <h2>学习需求</h2>
              <p class="muted compact">写下章节、目标或卡住的地方，系统会整理成多模态学习资料。</p>
            </div>
            <span class="status" :class="{ running: store.loading }">{{ inputStateLabel }}</span>
          </div>
          <textarea
            v-model="draftPrompt"
            class="prompt-input"
            :disabled="store.loading"
            placeholder="例如：为监督学习与过拟合生成讲解、导图和练习题。"
            rows="7"
            @keydown.enter.exact.prevent="submitGeneration"
          ></textarea>
          <div class="composer-footer">
            <div class="prompt-helper studio-helper">
              <span>当前画像</span>
              <strong>{{ profileHint }}</strong>
            </div>
            <div class="studio-actions">
              <button class="btn ghost" type="button" :disabled="store.loading" @click="resetDraft">清空</button>
              <button class="btn hero-primary" type="button" :disabled="!canSubmit" @click="submitGeneration">
                <span v-if="store.loading" class="btn-spinner" aria-hidden="true"></span>
                {{ primaryActionText }}
              </button>
            </div>
          </div>
          <div class="resource-type-picker">
            <span>资源类型偏好</span>
            <div class="segmented-options">
              <button type="button" :class="{ active: outputMode === 'all' }" :disabled="store.loading" @click="outputMode = 'all'">完整资料包</button>
              <button type="button" :class="{ active: outputMode === 'lesson' }" :disabled="store.loading" @click="outputMode = 'lesson'">讲解优先</button>
              <button type="button" :class="{ active: outputMode === 'practice' }" :disabled="store.loading" @click="outputMode = 'practice'">练习优先</button>
            </div>
          </div>
        </section>

        <GenerationProgress
          :progress="store.progress"
          :loading="store.loading"
          :current-step="friendlyGenerationStep"
          :complete="store.resources.length > 0 && !store.loading"
        />

        <section class="panel multimodal-panel">
          <div class="panel-title">
            <div>
              <h2>可生成的材料类型</h2>
              <p class="muted compact">系统可以按学习目标生成不同形式的资料。</p>
            </div>
          </div>
          <div class="multimodal-strip">
            <span v-for="item in multimodalTypes" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="panel result-panel studio-result-panel">
          <div class="panel-title">
            <div>
              <h2>本轮生成结果</h2>
              <p class="muted compact">{{ resultSubtitle }}</p>
            </div>
            <div class="result-actions">
              <button class="icon-btn with-border" type="button" :disabled="!selected" title="复制摘要" @click="copySummary">复制摘要</button>
              <button class="icon-btn with-border" type="button" :disabled="!store.resources.length || store.loading || !draftPrompt.trim()" title="重新生成" @click="submitGeneration">重新生成</button>
            </div>
          </div>

          <div v-if="store.loading" class="generating-state">
            <div class="stream-line">
              <span class="spinner"></span>
              <strong>{{ friendlyGenerationStep || '正在生成' }}</strong>
            </div>
            <div class="skeleton-lines" aria-hidden="true">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>

          <div v-else-if="store.error" class="empty error-state">
            <strong>生成失败</strong>
            <span>{{ store.error }}</span>
            <button class="btn secondary" type="button" :disabled="!draftPrompt.trim()" @click="submitGeneration">重试</button>
          </div>

          <div v-else-if="store.resources.length" class="cards result-cards">
            <ResourceCard
              v-for="resource in store.resources"
              :key="resource.id"
              :resource="resource"
              @select="selectCurrentResource"
              @feedback="handleFeedback"
            />
          </div>

          <div v-else class="empty empty-prompts">
            <strong>还没有生成结果</strong>
            <span>输入学习需求后，这里会展示可学习的资源卡片。</span>
            <div class="chips">
              <button
                v-for="template in promptTemplates.slice(0, 3)"
                :key="template.title"
                class="chip chip-button"
                type="button"
                @click="applyTemplate(template.prompt)"
              >
                {{ template.title }}
              </button>
            </div>
          </div>
        </section>

        <section class="panel history-panel">
          <div class="panel-title">
            <div>
              <h2>历史资料包</h2>
              <p class="muted compact">列表只加载摘要，点击后再读取完整资料包。</p>
            </div>
            <button v-if="selectedHistoryJob" class="btn ghost" type="button" @click="returnToCurrentResources">查看本轮资料</button>
            <span v-else class="status pending">{{ historicalGenerations.length }} 个资料包</span>
          </div>
          <div v-if="selectedHistoryJob" class="history-package-view">
            <div class="history-package-summary">
              <div>
                <span class="eyebrow">正在查看历史资料包</span>
                <h3>{{ historyTitle(selectedHistoryJob) }}</h3>
                <p class="muted compact">{{ formatDate(selectedHistoryJob.completed_at || selectedHistoryJob.created_at) }} · {{ selectedHistoryJob.resources.length }} 份资料</p>
              </div>
              <div class="history-type-summary">
                <span v-for="item in resourceTypeSummary(selectedHistoryJob.resources)" :key="item.type">{{ typeLabel(item.type) }} {{ item.count }}</span>
              </div>
            </div>
            <div class="cards result-cards">
              <ResourceCard
                v-for="resource in selectedHistoryJob.resources"
                :key="resource.id"
                :resource="resource"
                readonly
                @select="selectHistoryResource"
              />
            </div>
          </div>
          <div v-else-if="historicalGenerations.length" class="history-package-grid">
            <button
              v-for="job in historicalGenerations.slice(0, 6)"
              :key="job.id"
              class="history-package-card"
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
                <span v-for="item in job.resource_type_counts.slice(0, 4)" :key="item.type">{{ typeLabel(item.type) }} {{ item.count }}</span>
              </div>
            </button>
          </div>
          <div v-else-if="store.historyDetailLoadingId" class="empty small-empty">
            <strong>正在加载历史资料包</strong>
            <span>正在读取所选资料包详情。</span>
          </div>
          <div v-else class="empty small-empty">
            <strong>暂无历史资料包</strong>
            <span>生成新的资料后，以前的资料包会保存在这里。</span>
          </div>
        </section>

        <ResourceContent v-if="activePreviewResource" :resource="activePreviewResource" />
      </main>

      <details class="system-details">
        <summary>系统怎么生成资料？</summary>
        <div class="panel user-explain-panel">
          <div class="explain-grid">
            <article>
              <span>第一步</span>
              <strong>理解你的学习目标和薄弱点</strong>
            </article>
            <article>
              <span>第二步</span>
              <strong>整理成讲义、导图和练习</strong>
            </article>
            <article>
              <span>第三步</span>
              <strong>检查内容是否清楚可靠</strong>
            </article>
          </div>
        </div>
      </details>
    </div>

    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import resourceGenerationHero from '../assets/resource-generation-hero.png'
import { useLearningStore } from '../store'
import type { GenerationHistoryItem, GenerationHistorySummary, Resource } from '../types'
import GenerationProgress from '../components/GenerationProgress.vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'

interface PromptTemplate {
  title: string
  prompt: string
}

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const selectedHistoryJob = ref<GenerationHistoryItem | null>(null)
const selectedHistoryResource = ref<Resource | null>(null)
const requestedHistoryJobId = ref('')
const draftPrompt = ref('')
const toast = ref('')
const outputMode = ref('all')

const promptTemplates: PromptTemplate[] = [
  { title: '概念讲清楚', prompt: '请生成一份清晰讲解，包含例子、易错点和简短练习。' },
  { title: '边学边练', prompt: '请为本章生成一张知识导图和 5 道分层练习题。' },
  { title: '快速复习', prompt: '请生成 10 分钟复习资料，包含重点、常见错误和自测题。' },
  { title: '代码案例', prompt: '请生成可运行的最小代码示例，并解释每一步在做什么。' }
]
const multimodalTypes = ['图文讲解', '思维导图', '互动练习', '拓展阅读', '视频脚本', '动画演示', '代码案例', 'PPT 草稿']

const canSubmit = computed(() => !store.loading && draftPrompt.value.trim().length > 0)
const primaryActionText = computed(() => store.loading ? '正在生成...' : '开始生成')
const inputStateLabel = computed(() => {
  if (store.loading) return '生成中'
  if (draftPrompt.value.trim()) return '可提交'
  return '等待输入'
})
const resultSubtitle = computed(() => {
  if (store.loading) return friendlyGenerationStep.value
  if (store.resources.length) return `已生成 ${store.resources.length} 份资料，点击卡片开始学习。`
  return '提交学习需求后，资源包会出现在这里。'
})
const friendlyGenerationStep = computed(() => {
  const text = store.currentStep || ''
  if (text.includes('profile') || text.includes('画像') || text.includes('理解')) return '正在理解你的学习目标'
  if (text.includes('quiz') || text.includes('练习')) return '正在生成练习题'
  if (text.includes('review') || text.includes('审核') || text.includes('质检')) return '正在检查内容质量'
  if (text.includes('path') || text.includes('plan') || text.includes('规划')) return '正在整理学习建议'
  return '正在生成学习资料'
})
const profileHint = computed(() => {
  if (!store.profile) return '暂无画像，后端会使用默认学习画像。'
  return `${store.profile.course} / ${store.profile.current_chapter} / 目标：${store.profile.learning_goal}`
})
const historicalGenerations = computed(() => store.resourceHistory.filter(job => !job.is_current))
const activePreviewResource = computed(() => selectedHistoryResource.value || selected.value)

onMounted(async () => {
  await store.ensureReady()
  hydrateDraft()
  selected.value = store.resources[0] || null
})

function hydrateDraft() {
  if (draftPrompt.value) return
  const chapter = store.profile?.current_chapter
  const goal = store.profile?.learning_goal
  if (!chapter && !goal) return
  draftPrompt.value = `围绕${chapter || '当前章节'}生成个性化学习资料，目标是${goal || '掌握核心概念'}。`
}

function applyTemplate(prompt: string) {
  draftPrompt.value = prompt
}

function resetDraft() {
  draftPrompt.value = ''
}

async function submitGeneration() {
  if (!canSubmit.value) return
  returnToCurrentResources()
  await store.generateResources(selectedResourceTypes(), draftPrompt.value)
  selected.value = store.resources[0] || null
  showToast(store.resources.length ? '资源生成完成' : '任务完成，但暂无资源')
}

function selectedResourceTypes() {
  if (outputMode.value === 'lesson') {
    return ['lecture_doc', 'mind_map', 'reading', 'animation_demo']
  }
  if (outputMode.value === 'practice') {
    return ['mind_map', 'quiz', 'visual_card', 'code_case']
  }
  return []
}

function formatDate(value?: string | null) {
  if (!value) return '时间未知'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function typeLabel(type: string) {
  const labels: Record<string, string> = {
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
  return labels[type] || type
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
  selectedHistoryResource.value = selectedHistoryJob.value?.resources[0] || null
  try {
    const detail = await store.loadResourceHistoryDetail(job.id)
    if (requestedHistoryJobId.value !== job.id) return
    selectedHistoryJob.value = detail
    selectedHistoryResource.value = detail.resources[0] || null
    showToast('已打开历史资料包')
  } catch {
    if (requestedHistoryJobId.value === job.id) returnToCurrentResources()
  }
}

function selectHistoryResource(resource: Resource) {
  selectedHistoryResource.value = resource
}

function returnToCurrentResources() {
  requestedHistoryJobId.value = ''
  selectedHistoryJob.value = null
  selectedHistoryResource.value = null
}

function selectCurrentResource(resource: Resource) {
  returnToCurrentResources()
  selected.value = resource
}

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  returnToCurrentResources()
  await store.submitResourceFeedback(resource.id, action)
  selected.value = store.resources.find(item => item.id === resource.id) || selected.value
  showToast('反馈已保存')
}

async function copySummary() {
  if (!selected.value) return
  const summary = `${selected.value.title}\n${selected.value.audit_reason || selected.value.review_reason || ''}`
  try {
    await navigator.clipboard.writeText(summary)
    showToast('已复制摘要')
  } catch {
    showToast('复制失败')
  }
}

function showToast(message: string) {
  toast.value = message
  window.setTimeout(() => {
    if (toast.value === message) toast.value = ''
  }, 2200)
}
</script>
