<template>
  <div class="page generate-page ai-studio-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">生成学习资料</span>
        <h1>告诉我你想学什么</h1>
        <p>输入学习需求后，系统会生成讲解、导图、练习、脚本、代码等多种学习材料。</p>
      </div>
      <div class="today-focus-card">
        <span>生成状态</span>
        <strong>{{ store.loading ? `${Math.round(store.progress)}%` : store.resources.length ? '已生成' : '待提交' }}</strong>
        <small>{{ store.loading ? friendlyGenerationStep : resultSubtitle }}</small>
      </div>
    </section>

    <div class="quiet-workspace">
      <main class="studio-main">
        <section class="panel composer-panel studio-composer">
          <div class="panel-title">
            <div>
              <h2>你想学什么</h2>
              <p class="muted compact">写下章节、目标或卡住的地方，系统会整理成多模态学习资料。</p>
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
            <span>想生成的资源类型</span>
            <div class="segmented-options">
              <button type="button" :class="{ active: outputMode === 'all' }" :disabled="store.loading" @click="outputMode = 'all'">完整资料包</button>
              <button type="button" :class="{ active: outputMode === 'lesson' }" :disabled="store.loading" @click="outputMode = 'lesson'">讲解优先</button>
              <button type="button" :class="{ active: outputMode === 'practice' }" :disabled="store.loading" @click="outputMode = 'practice'">练习优先</button>
            </div>
          </div>
        </section>

        <div class="studio-status-grid">
          <GenerationProgress :progress="store.progress" :loading="store.loading" :current-step="friendlyGenerationStep" />
        </div>

        <section class="panel multimodal-panel">
          <div class="panel-title">
            <div>
              <h2>本次可生成的材料类型</h2>
              <p class="muted compact">可以按学习目标生成不同形式的资料。</p>
            </div>
          </div>
          <div class="multimodal-strip">
            <span v-for="item in multimodalTypes" :key="item">{{ item }}</span>
          </div>
        </section>

        <section class="panel result-panel studio-result-panel">
          <div class="panel-title">
            <div>
              <h2>生成结果</h2>
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
              @select="selected = $event"
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

        <ResourceContent v-if="selected" :resource="selected" />
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
              <strong>整理成讲义、导图、练习等材料</strong>
            </article>
            <article>
              <span>第三步</span>
              <strong>检查内容是否清楚、可靠、适合学习</strong>
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
import { useLearningStore } from '../store'
import type { Resource } from '../types'
import GenerationProgress from '../components/GenerationProgress.vue'
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
const outputMode = ref('all')

const promptTemplates: PromptTemplate[] = [
  { title: '概念讲清楚', prompt: '我想学习当前章节，请用循序渐进的方式讲清核心概念、生活化例子和常见误区。' },
  { title: '边学边练', prompt: '请为当前章节生成一张知识导图和 5 道分层练习题，帮助我检查概念理解。' },
  { title: '快速复习', prompt: '请把本章内容整理成 10 分钟复习材料，包含重点清单、易错点和最后自测题。' },
  { title: '代码案例', prompt: '请生成一个可运行的代码案例，用最小示例解释本章关键算法，并说明每一步在做什么。' }
]
const multimodalTypes = ['图文讲解', '思维导图', '互动练习', '视频脚本', '动画演示', '代码案例', 'PPT 草稿', '学习卡片']

const canSubmit = computed(() => !store.loading && draftPrompt.value.trim().length > 0)
const primaryActionText = computed(() => store.loading ? '正在生成资料...' : '开始生成')
const inputStateLabel = computed(() => {
  if (store.loading) return '生成中'
  if (draftPrompt.value.trim()) return '可提交'
  return '等待输入'
})
const resultSubtitle = computed(() => {
  if (store.loading) return friendlyGenerationStep.value
  if (store.resources.length) return `已生成 ${store.resources.length} 份资源，点击卡片开始学习`
  return '提交学习需求后，资源包会出现在这里'
})
const friendlyGenerationStep = computed(() => {
  const text = store.currentStep || ''
  if (text.includes('profile') || text.includes('画像') || text.includes('理解')) return '正在理解你的学习目标'
  if (text.includes('quiz') || text.includes('练习')) return '正在生成练习题'
  if (text.includes('review') || text.includes('审核') || text.includes('质检')) return '正在检查内容可靠性'
  if (text.includes('path') || text.includes('plan') || text.includes('规划')) return '正在整理学习建议'
  return '正在生成讲义和学习资料'
})
const profileHint = computed(() => {
  if (!store.profile) return '暂无画像，后端会使用默认学习画像。'
  return `${store.profile.course} / ${store.profile.current_chapter} / 目标：${store.profile.learning_goal}`
})

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
