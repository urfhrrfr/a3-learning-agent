<template>
  <div class="page tutor-center-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">智能导师</span>
        <h1>像聊天一样把问题问清楚</h1>
        <p>提出问题后，导师会给出解释、下一步建议和小练习；需要时可以展开查看回答依据。</p>
      </div>
      <div class="today-focus-card">
        <span>当前学习状态</span>
        <strong>{{ store.profile ? `${Math.round(store.profile.mastery * 100)}%` : '-' }}</strong>
        <p>{{ profileSummary }}</p>
      </div>
    </section>

    <div class="grid tutor-center-grid">
      <section class="panel span-4 tutor-question-panel">
        <div class="panel-title">
          <div>
            <h2>问题输入</h2>
            <p class="muted compact">可以直接问概念、题目或材料里没看懂的地方。</p>
          </div>
        </div>
        <label class="field">
          <span>引用资源</span>
          <select v-model="selectedResourceId" :disabled="asking">
            <option value="">自动选择相关资源</option>
            <option v-for="resource in store.resources" :key="resource.id" :value="resource.id">
              {{ resource.title }}
            </option>
          </select>
        </label>
        <div v-if="!store.resources.length" class="empty small-empty">
          <strong>暂无可引用资源</strong>
          <span>导师会先结合学习画像和通用课程知识回答；生成资源后将展示依据。</span>
          <RouterLink class="btn ghost" to="/generate">生成可引用资源</RouterLink>
        </div>
        <textarea rows="7" v-model="question" placeholder="例如：我看不懂过拟合和泛化的区别，可以用一个例子解释吗？"></textarea>
        <div class="resource-actions">
          <button class="btn hero-primary" :disabled="asking || !question.trim()" @click="ask">
            {{ asking ? '思考中...' : '发送问题' }}
          </button>
          <button class="btn secondary" :disabled="asking || !messages.length" @click="clearChat">清空对话</button>
        </div>
        <span v-if="asking" class="inline-state">正在生成回答</span>
        <div v-if="localError" class="empty error-state">
          <strong>导师暂时没有返回答案</strong>
          <span>{{ localError }}</span>
          <button class="btn secondary" type="button" :disabled="asking || !lastFailedQuestion" @click="retryLastQuestion">重试上一问</button>
        </div>

      </section>

      <main class="span-8 tutor-main-stack">
        <TutorAnswerPanel
          :answer="latestAnswer"
          :loading="asking"
          :next-step="nextStep"
          :exercise="exercise"
          v-model:exercise-answer="exerciseAnswer"
          :exercise-result="exerciseResult"
          :submitting-exercise="submittingExercise"
          @submit-exercise="submitExercise"
        />
        <MermaidRenderer v-if="mermaid" :content="mermaid" />
      </main>

      <details class="system-details span-12">
        <summary>为什么这样回答？</summary>
        <section class="panel user-explain-panel">
          <div class="explain-grid">
            <article v-for="item in answerReasons" :key="item.title">
              <span>{{ item.title }}</span>
              <strong>{{ item.text }}</strong>
            </article>
          </div>
          <div v-if="profileSuggestion" class="profile-nudge">
            <p>{{ profileSuggestion.message }}</p>
            <button
              v-if="!profileSuggestion.already_exists"
              class="btn secondary"
              type="button"
              :disabled="confirmingWeakPoint"
              @click="confirmWeakPoint"
            >
              {{ confirmingWeakPoint ? '写入中...' : '加入薄弱点' }}
            </button>
          </div>
        </section>
      </details>

      <section class="panel span-12">
        <div class="panel-title">
          <div>
            <h2>最近对话</h2>
            <p class="muted compact">保留本页本地对话历史，用于继续追问。</p>
          </div>
        </div>
        <div class="chat-thread" v-if="messages.length">
          <article v-for="(message, index) in messages" :key="index" class="chat-bubble" :class="message.role">
            <div class="chat-role">{{ message.role === 'user' ? '我' : '导师' }}</div>
            <MarkdownRenderer :content="message.content" />
          </article>
        </div>
        <div v-else class="empty">
          <strong>还没有对话</strong>
          <span>发送第一个问题后，导师回答和上下文会展示在这里。</span>
          <button class="btn secondary" type="button" @click="question = '什么是过拟合？请用一个新手能理解的例子解释。'">填入示例问题</button>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'
import TutorAnswerPanel from '../components/TutorAnswerPanel.vue'
import { friendlyErrorMessage, useLearningStore } from '../store'
import type { TutorExercise, TutorExerciseResult, TutorMessage, TutorNextStep, TutorResponse } from '../types'

const question = ref('')
const selectedResourceId = ref('')
const messages = ref<TutorMessage[]>([])
const mermaid = ref('')
const provider = ref('')
const usedFallback = ref(false)
const fallbackReason = ref('')
const sourceRefs = ref<string[]>([])
const asking = ref(false)
const confirmingWeakPoint = ref(false)
const localError = ref('')
const lastFailedQuestion = ref('')
const profileSuggestion = ref<TutorResponse['profile_suggestion']>(null)
const personalization = ref<TutorResponse['personalization'] | null>(null)
const citedResources = ref<NonNullable<TutorResponse['cited_resources']>>([])
const nextStep = ref<TutorNextStep | null>(null)
const exercise = ref<TutorExercise | null>(null)
const exerciseAnswer = ref('')
const exerciseResult = ref<TutorExerciseResult | null>(null)
const submittingExercise = ref(false)
const store = useLearningStore()

onMounted(() => {
  store.ensureReady()
})

const latestAnswer = computed(() => [...messages.value].reverse().find(message => message.role === 'assistant')?.content || '')
const selectedResource = computed(() => store.resources.find(resource => resource.id === selectedResourceId.value) || null)
const profileSummary = computed(() => {
  if (!store.profile) return '等待画像同步'
  return `${store.profile.current_chapter} · ${store.profile.weak_points.slice(0, 2).join('、') || '薄弱点待识别'}`
})
const providerLabel = computed(() => {
  if (provider.value === 'spark') return '星火模型'
  if (provider.value === 'openai_compatible') return '兼容大模型'
  if (provider.value === 'mock') return 'Mock'
  return provider.value || '未提问'
})
const answerReasons = computed(() => {
  const reasons = [
    {
      title: '结合学习目标',
      text: store.profile?.learning_goal || '你还没有填写明确学习目标'
    },
    {
      title: '针对薄弱点',
      text: personalization.value?.weak_points?.length
        ? personalization.value.weak_points.slice(0, 3).join('、')
        : store.profile?.weak_points?.slice(0, 3).join('、') || '暂未识别薄弱点'
    },
    {
      title: '符合学习偏好',
      text: personalization.value?.preferred_modalities?.length
        ? personalization.value.preferred_modalities.slice(0, 3).join('、')
        : store.profile?.preferred_modalities?.slice(0, 3).join('、') || '会尽量用清晰例子解释'
    }
  ]
  if (selectedResource.value || citedResources.value.length) {
    reasons.push({
      title: '参考学习资料',
      text: selectedResource.value?.title || citedResources.value.map(item => item.title).slice(0, 2).join('、')
    })
  }
  return reasons
})

async function ask() {
  const text = question.value.trim()
  if (!text) return
  asking.value = true
  localError.value = ''
  const history = messages.value.slice(-8)
  messages.value.push({ role: 'user', content: text })
  question.value = ''
  try {
    const data = await api.tutor(text, selectedResourceId.value || null, history)
    messages.value.push({ role: 'assistant', content: data.answer })
    mermaid.value = data.mermaid
    provider.value = data.llm_provider || ''
    usedFallback.value = Boolean(data.used_fallback)
    fallbackReason.value = data.fallback_reason || ''
    sourceRefs.value = data.source_refs || []
    profileSuggestion.value = data.profile_suggestion || null
    personalization.value = data.personalization || null
    citedResources.value = data.cited_resources || []
    nextStep.value = data.next_step || null
    exercise.value = data.exercise || null
    exerciseAnswer.value = ''
    exerciseResult.value = null
    lastFailedQuestion.value = ''
  } catch (error) {
    localError.value = friendlyErrorMessage(error, '智能辅导请求失败')
    lastFailedQuestion.value = text
    messages.value.pop()
  } finally {
    asking.value = false
  }
}

async function submitExercise() {
  if (!exercise.value) return
  submittingExercise.value = true
  localError.value = ''
  try {
    const data = await api.submitTutorExercise(exercise.value, exerciseAnswer.value)
    exerciseResult.value = data
    store.profile = data.profile
    store.path = data.learning_path
    nextStep.value = data.next_step
    personalization.value = {
      preferred_mode: personalization.value?.preferred_mode || '例子',
      preferred_modalities: data.profile.preferred_modalities,
      weak_points: data.profile.weak_points
    }
    messages.value.push({
      role: 'assistant',
      content: `练习反馈：${data.feedback}\n\n下一步建议：${data.next_step?.title || '继续巩固当前概念'}`
    })
  } catch (error) {
    localError.value = friendlyErrorMessage(error, '练习反馈提交失败')
  } finally {
    submittingExercise.value = false
  }
}

async function confirmWeakPoint() {
  if (!profileSuggestion.value?.topic) return
  confirmingWeakPoint.value = true
  localError.value = ''
  try {
    const data = await api.confirmWeakPoint(profileSuggestion.value.topic, profileSuggestion.value.message)
    store.profile = data.profile
    profileSuggestion.value = {
      ...profileSuggestion.value,
      already_exists: true,
      message: data.profile_updated
        ? `已加入画像薄弱点：${profileSuggestion.value.topic}`
        : `画像中已包含：${profileSuggestion.value.topic}`
    }
    personalization.value = {
      preferred_mode: personalization.value?.preferred_mode || '例子',
      preferred_modalities: data.profile.preferred_modalities,
      weak_points: data.profile.weak_points
    }
  } catch (error) {
    localError.value = friendlyErrorMessage(error, '薄弱点确认失败')
  } finally {
    confirmingWeakPoint.value = false
  }
}

function retryLastQuestion() {
  if (!lastFailedQuestion.value) return
  question.value = lastFailedQuestion.value
  void ask()
}

function clearChat() {
  messages.value = []
  mermaid.value = ''
  sourceRefs.value = []
  fallbackReason.value = ''
  provider.value = ''
  usedFallback.value = false
  profileSuggestion.value = null
  personalization.value = null
  citedResources.value = []
  nextStep.value = null
  exercise.value = null
  exerciseAnswer.value = ''
  exerciseResult.value = null
}
</script>
