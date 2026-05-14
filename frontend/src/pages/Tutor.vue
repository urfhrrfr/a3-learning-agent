<template>
  <div class="page">
    <div class="header"><h1>智能辅导</h1></div>
    <div class="grid">
      <section class="panel span-4">
        <h2>提问</h2>
        <label class="field">
          <span>引用资源</span>
          <select v-model="selectedResourceId" :disabled="asking">
            <option value="">自动选择相关资源</option>
            <option v-for="resource in store.resources" :key="resource.id" :value="resource.id">
              {{ resource.title }}
            </option>
          </select>
        </label>
        <textarea rows="6" v-model="question" placeholder="输入你想追问的概念、例题或学习困惑"></textarea>
        <div class="split">
          <button class="btn" :disabled="asking || !question.trim()" @click="ask">
            {{ asking ? '思考中...' : '发送' }}
          </button>
          <button class="btn secondary" :disabled="asking || !messages.length" @click="clearChat">清空对话</button>
        </div>
        <span v-if="asking" class="inline-state">正在结合画像、资源和最近对话生成回答</span>
        <div v-if="localError" class="empty">{{ localError }}</div>
        <div class="trace-badges tutor-meta">
          <span class="chip provider">{{ providerLabel }}</span>
          <span class="chip" :class="usedFallback ? 'warning' : 'success'">{{ usedFallback ? '模板兜底' : '大模型回答' }}</span>
        </div>
        <p v-if="fallbackReason" class="review-note">兜底原因：{{ fallbackReason }}</p>
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
        <div v-if="personalization" class="tutor-profile">
          <span class="chip success">偏好：{{ personalization.preferred_mode }}</span>
          <span v-for="point in personalization.weak_points.slice(0, 3)" :key="point" class="chip warning">{{ point }}</span>
        </div>
        <p v-if="sourceRefs.length" class="muted compact">引用来源用于说明回答依据的课程片段。</p>
        <div class="chips" v-if="sourceRefs.length">
          <span v-for="ref in sourceRefs" :key="ref" class="chip">{{ ref }}</span>
        </div>
        <div v-if="citedResources.length" class="tutor-block">
          <b>本次引用</b>
          <span v-for="resource in citedResources" :key="resource.id">{{ resource.title }} · {{ resource.difficulty }}</span>
        </div>
        <div v-if="nextStep" class="tutor-block">
          <b>下一步</b>
          <strong>{{ nextStep.title }}</strong>
          <span>{{ nextStep.objective }}</span>
          <small>{{ nextStep.estimated_minutes }} 分钟 · {{ nextStep.reason }}</small>
        </div>
        <div v-if="exercise" class="tutor-exercise">
          <b>针对当前困惑的小练习</b>
          <p>{{ exercise.prompt }}</p>
          <small>{{ exercise.hint }}</small>
          <textarea rows="4" v-model="exerciseAnswer" placeholder="写下你的理解，导师会即时评估"></textarea>
          <button class="btn" type="button" :disabled="submittingExercise || !exerciseAnswer.trim()" @click="submitExercise">
            {{ submittingExercise ? '评估中...' : '提交练习' }}
          </button>
        </div>
        <div v-if="exerciseResult" class="tutor-result">
          <b>练习反馈 · {{ exerciseResult.score }} 分</b>
          <p>{{ exerciseResult.feedback }}</p>
          <small>掌握度变化：{{ Math.round(exerciseResult.mastery_delta * 100) }}%</small>
        </div>
      </section>

      <section class="panel span-8">
        <div class="panel-title">
          <h2>连续对话</h2>
        </div>
        <div class="chat-thread" v-if="messages.length">
          <article v-for="(message, index) in messages" :key="index" class="chat-bubble" :class="message.role">
            <div class="chat-role">{{ message.role === 'user' ? '我' : '导师' }}</div>
            <MarkdownRenderer :content="message.content" />
          </article>
        </div>
        <div v-else class="empty">
          你可以从任意课程问题开始，后续追问会带上最近对话上下文。
        </div>
        <MermaidRenderer v-if="mermaid" :content="mermaid" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import { useLearningStore } from '../store'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'
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

const providerLabel = computed(() => {
  if (provider.value === 'spark') return '星火模型'
  if (provider.value === 'openai_compatible') return '兼容大模型'
  if (provider.value === 'mock') return 'Mock'
  return provider.value || '未提问'
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
  } catch (error) {
    localError.value = error instanceof Error ? error.message : String(error)
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
    localError.value = error instanceof Error ? error.message : String(error)
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
    localError.value = error instanceof Error ? error.message : String(error)
  } finally {
    confirmingWeakPoint.value = false
  }
}

function clearChat() {
  messages.value = []
  mermaid.value = ''
  sourceRefs.value = []
  fallbackReason.value = ''
  profileSuggestion.value = null
  personalization.value = null
  citedResources.value = []
  nextStep.value = null
  exercise.value = null
  exerciseAnswer.value = ''
  exerciseResult.value = null
}
</script>
