<template>
  <div class="page generate-page">
    <section class="workspace-hero">
      <div class="workspace-copy">
        <span class="eyebrow">AI 资源生成工作台</span>
        <h1>把学习目标转成可审核、可复用的课程资源</h1>
        <p class="muted">
          输入章节、目标和薄弱点后，多智能体会协作生成讲解、导图、练习、阅读、脚本和代码案例。
        </p>
      </div>
      <div class="hero-actions">
        <button class="btn ghost" type="button" :disabled="store.loading" @click="resetDraft">清空输入</button>
        <button class="btn" type="button" :disabled="!canSubmit" @click="submitGeneration">
          <span v-if="store.loading" class="btn-spinner" aria-hidden="true"></span>
          {{ primaryActionText }}
        </button>
      </div>
    </section>

    <div class="ai-workspace">
      <aside class="workspace-side">
        <section class="panel compact-panel">
          <div class="panel-title">
            <h2>快捷模板</h2>
            <span class="muted">{{ promptTemplates.length }} 个</span>
          </div>
          <div class="template-list">
            <button
              v-for="template in promptTemplates"
              :key="template.title"
              class="template-item"
              type="button"
              @click="applyTemplate(template.prompt)"
            >
              <strong>{{ template.title }}</strong>
              <span>{{ template.prompt }}</span>
            </button>
          </div>
        </section>

        <section class="panel compact-panel">
          <div class="panel-title">
            <h2>最近任务</h2>
            <span class="muted">{{ store.resources.length ? '已生成' : '暂无' }}</span>
          </div>
          <div v-if="recentResources.length" class="history-list">
            <button v-for="resource in recentResources" :key="resource.id" class="history-item" type="button" @click="selected = resource">
              <span>{{ resource.title }}</span>
              <small>{{ resource.content_format }} · {{ resource.review_status }}</small>
            </button>
          </div>
          <div v-else class="empty small-empty">生成完成后会在这里保留最近资源。</div>
        </section>
      </aside>

      <main class="workspace-core">
        <section class="panel composer-panel">
          <div class="panel-title">
            <div>
              <h2>输入生成任务</h2>
              <p class="muted compact">Enter 提交，Shift + Enter 换行</p>
            </div>
            <span class="status" :class="{ running: store.loading }">{{ inputStateLabel }}</span>
          </div>
          <textarea
            v-model="draftPrompt"
            class="prompt-input"
            :disabled="store.loading"
            placeholder="例如：为机器学习基础章节生成一组适合本科生的讲解、导图和练习，重点解释监督学习与过拟合。"
            rows="7"
            @keydown.enter.exact.prevent="submitGeneration"
          ></textarea>
          <div class="composer-footer">
            <span class="muted">{{ draftPrompt.length }} 字 · {{ store.profile?.current_chapter || '默认章节' }}</span>
            <div class="split">
              <button v-if="store.loading" class="btn secondary" type="button" disabled>停止生成</button>
              <button class="btn" type="button" :disabled="!canSubmit" @click="submitGeneration">
                <span v-if="store.loading" class="btn-spinner" aria-hidden="true"></span>
                {{ primaryActionText }}
              </button>
            </div>
          </div>
        </section>

        <GenerationProgress :progress="store.progress" :loading="store.loading" :current-step="store.currentStep" />
        <LearningItineraryCard
          :plan-summary="store.planSummary"
          :time-budget="store.profile?.time_budget"
        />

        <section class="panel result-panel">
          <div class="panel-title">
            <div>
              <h2>生成结果</h2>
              <p class="muted compact">{{ resultSubtitle }}</p>
            </div>
            <div class="result-actions">
              <button class="icon-btn with-border" type="button" :disabled="!selected" title="复制摘要" @click="copySummary">复制</button>
              <button class="icon-btn with-border" type="button" :disabled="!store.resources.length || store.loading" title="重新生成" @click="submitGeneration">重试</button>
              <button class="icon-btn with-border" type="button" :disabled="!selected" title="导出资源" @click="showToast('已准备导出当前资源')">导出</button>
            </div>
          </div>

          <div v-if="store.loading" class="generating-state">
            <div class="stream-line">
              <span class="spinner"></span>
              <strong>{{ store.currentStep || '正在生成' }}</strong>
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
            <button class="btn secondary" type="button" @click="submitGeneration">重试</button>
          </div>

          <div v-else-if="store.resources.length" class="cards result-cards">
            <ResourceCard
              v-for="resource in store.resources"
              :key="resource.id"
              :resource="resource"
              @select="selected = $event"
              @feedback="handleFeedback"
            />
          </div>

          <div v-else class="empty empty-prompts">
            <strong>还没有生成结果</strong>
            <span>选择一个模板或输入学习目标，系统会生成可审核的多格式资源。</span>
            <div class="chips">
              <button v-for="template in promptTemplates.slice(0, 3)" :key="template.title" class="chip chip-button" type="button" @click="applyTemplate(template.prompt)">
                {{ template.title }}
              </button>
            </div>
          </div>
        </section>

        <ResourceContent v-if="selected" :resource="selected" />
      </main>

      <aside class="workspace-side">
        <section class="panel compact-panel">
          <div class="panel-title">
            <h2>生成参数</h2>
            <span class="status">影响下次生成</span>
          </div>
          <label class="field-label">
            <span>模型策略</span>
            <select v-model="modelMode" :disabled="store.loading">
              <option value="balanced">平衡质量与速度</option>
              <option value="creative">更强创造性</option>
              <option value="strict">更严格审核</option>
            </select>
          </label>
          <label class="field-label">
            <span>输出格式</span>
            <select v-model="outputMode" :disabled="store.loading">
              <option value="all">全量资源包</option>
              <option value="lesson">讲解优先</option>
              <option value="practice">练习优先</option>
            </select>
          </label>
          <label class="field-label">
            <span>生成深度</span>
            <input v-model.number="depth" type="range" min="1" max="3" :disabled="store.loading" />
          </label>
          <p class="muted compact">参数变更会在下一次提交时生效，不会改写当前结果。</p>
        </section>

        <AgentTraceTimeline :traces="store.traces" />
      </aside>
    </div>

    <div v-if="toast" class="toast" role="status">{{ toast }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useLearningStore } from '../store'
import type { Resource } from '../types'
import GenerationProgress from '../components/GenerationProgress.vue'
import LearningItineraryCard from '../components/LearningItineraryCard.vue'
import AgentTraceTimeline from '../components/AgentTraceTimeline.vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'

interface PromptTemplate {
  title: string
  prompt: string
}

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const draftPrompt = ref('')
const toast = ref('')
const modelMode = ref('balanced')
const outputMode = ref('all')
const depth = ref(2)

const promptTemplates: PromptTemplate[] = [
  { title: '章节讲解', prompt: '为当前章节生成一份循序渐进的讲解材料，包含核心概念、例子和常见误区。' },
  { title: '导图 + 练习', prompt: '生成一张知识导图和 5 道分层练习题，帮助我检查概念理解。' },
  { title: '视频脚本', prompt: '把本章内容改写成 3 分钟教学视频脚本，包含分镜、旁白和屏幕文字。' },
  { title: '代码案例', prompt: '生成一个可运行的代码案例，用最小示例解释本章关键算法。' }
]

const canSubmit = computed(() => !store.loading && draftPrompt.value.trim().length > 0)
const recentResources = computed(() => store.resources.slice(0, 4))
const primaryActionText = computed(() => store.loading ? '生成中...' : '开始生成')
const inputStateLabel = computed(() => {
  if (store.loading) return '已提交'
  if (draftPrompt.value.trim()) return '可提交'
  return '等待输入'
})
const resultSubtitle = computed(() => {
  if (store.loading) return '正在分析任务并生成多格式资源'
  if (store.resources.length) return `已生成 ${store.resources.length} 份资源，可继续查看、复制或反馈`
  return '结果会在任务完成后出现在这里'
})

onMounted(async () => {
  await store.ensureReady()
  hydrateDraft()
})

function hydrateDraft() {
  if (draftPrompt.value) return
  const chapter = store.profile?.current_chapter
  const goal = store.profile?.learning_goal
  if (!chapter && !goal) return
  draftPrompt.value = `围绕「${chapter}」生成个性化学习资源，目标是${goal}。`
}

function applyTemplate(prompt: string) {
  draftPrompt.value = prompt
}

function resetDraft() {
  draftPrompt.value = ''
}

async function submitGeneration() {
  if (!canSubmit.value) return
  await store.generateResources(selectedResourceTypes(), draftPrompt.value)
  selected.value = store.resources[0] || null
  showToast(store.resources.length ? '资源生成完成' : '任务完成，但暂无结果')
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

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
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
    showToast('复制失败，请检查浏览器权限')
  }
}

function showToast(message: string) {
  toast.value = message
  window.setTimeout(() => {
    if (toast.value === message) toast.value = ''
  }, 2200)
}
</script>
