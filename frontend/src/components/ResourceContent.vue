<template>
  <section v-if="resource" class="panel resource-content" :class="resourceShellClass">
    <div class="panel-title">
      <div>
        <h2>{{ resource.title }}</h2>
        <div class="resource-meta compact">
          <span>{{ resourceTypeLabel }}</span>
          <span>{{ contentFormatLabel }}</span>
          <span>{{ resource.difficulty }}</span>
        </div>
      </div>
      <span class="status" :class="resource.review_status">{{ reviewStatusLabel }}</span>
    </div>

    <div class="resource-audit">
      <p><strong>审核状态：</strong>{{ reviewStatusLabel }}</p>
      <p><strong>审核 confidence：</strong>{{ resource.review_confidence.toFixed(2) }}</p>
      <p><strong>审核理由：</strong>{{ resource.audit_reason || resource.review_reason || '暂无审核说明' }}</p>
      <div v-if="resource.review_notes?.length">
        <strong>审核证据：</strong>
        <ul>
          <li v-for="note in resource.review_notes" :key="note">{{ note }}</li>
        </ul>
      </div>
    </div>

    <template v-if="resource.type === 'animation_demo'">
      <div class="format-hero">
        <span>Playable Animation</span>
        <strong>{{ animationFrames.length || '未识别' }} 段动态图解</strong>
        <p>{{ animationPayload?.playback_note || '系统内直接播放的教学动画，不需要人工录制。' }}</p>
      </div>
      <div v-if="animationFrames.length" class="animation-player">
        <div class="animation-stage">
          <div class="animation-orbit" :class="`visual-${activeFrame.visual}`" aria-hidden="true">
            <span class="data-dot dot-a"></span>
            <span class="data-dot dot-b"></span>
            <span class="data-dot dot-c"></span>
            <span class="model-node">{{ activeFrame.focus }}</span>
            <span class="signal-line"></span>
          </div>
          <div class="animation-caption">
            <span>场景 {{ activeFrameIndex + 1 }}/{{ animationFrames.length }}</span>
            <h3>{{ activeFrame.title }}</h3>
            <p>{{ activeFrame.caption }}</p>
          </div>
        </div>
        <div class="animation-strip">
          <button
            v-for="(frame, index) in animationFrames"
            :key="frame.id"
            type="button"
            class="animation-step"
            :class="{ active: index === activeFrameIndex }"
            @click="activeFrameIndex = index"
          >
            <span>{{ index + 1 }}</span>
            <strong>{{ frame.focus }}</strong>
          </button>
        </div>
        <p class="speaker-note" v-if="animationPayload?.teacher_prompt">{{ animationPayload.teacher_prompt }}</p>
      </div>
      <pre v-else>{{ resource.content }}</pre>
    </template>

    <template v-else-if="resource.type === 'quiz'">
      <div class="format-hero">
        <span>Interactive Quiz</span>
        <strong>{{ quizQuestions.length || '未识别' }} 道分层练习题</strong>
        <p>题目按类型、难度、考查点拆开展示，便于直接进入练习评估。</p>
      </div>
      <div v-if="quizQuestions.length" class="quiz-preview-list">
        <article class="quiz-preview-card" v-for="(question, index) in quizQuestions" :key="`${question.question}-${index}`">
          <div class="quiz-preview-head">
            <span>题目 {{ index + 1 }}</span>
            <div class="chips">
              <span class="chip">{{ question.type || '问答题' }}</span>
              <span class="chip">{{ question.difficulty || question.level || '基础' }}</span>
            </div>
          </div>
          <p class="quiz-question">{{ question.question }}</p>
          <div v-if="question.options?.length" class="option-list compact-options">
            <span v-for="option in question.options" :key="option" class="option-pill">{{ option }}</span>
          </div>
          <p class="muted compact" v-if="question.assessment_point">考查点：{{ question.assessment_point }}</p>
        </article>
      </div>
      <pre v-else>{{ resource.content }}</pre>
    </template>

    <template v-else-if="resource.type === 'media_script'">
      <div class="format-hero">
        <span>Storyboard</span>
        <strong>{{ storyboardRows.length || '未识别' }} 个镜头</strong>
        <p>这是分镜脚本，不是已经生成的 mp4 视频；可交给拍摄或视频生成工具继续生产。</p>
      </div>
      <div class="storyboard-deck" v-if="storyboardRows.length">
        <article class="storyboard-card" v-for="(row, index) in storyboardRows" :key="`${row.time}-${index}`">
          <div class="storyboard-card-head">
            <span>镜头 {{ index + 1 }}</span>
            <strong>{{ row.time }}</strong>
          </div>
          <div class="storyboard-visual">{{ row.scene }}</div>
          <dl>
            <dt>旁白</dt>
            <dd>{{ row.voiceover }}</dd>
            <dt>屏幕文字</dt>
            <dd>{{ row.caption }}</dd>
          </dl>
        </article>
      </div>
      <p v-else class="empty">未识别到分镜表数据，以下保留脚本文本。</p>
      <div v-if="productionNotes.length" class="production-notes">
        <h3>制作提示</h3>
        <div class="chips">
          <span class="chip" v-for="note in productionNotes" :key="note">{{ note }}</span>
        </div>
      </div>
      <pre v-if="!storyboardRows.length">{{ resource.content }}</pre>
    </template>

    <template v-else-if="resource.type === 'ppt_draft'">
      <div class="format-hero">
        <span>Slide Outline</span>
        <strong>{{ slideRows.length || '未识别' }} 页课堂讲解幻灯片</strong>
        <p>把 PPT 草稿呈现为讲课节奏、页面主题和讲者提示。</p>
      </div>
      <div class="slide-outline" v-if="slideRows.length">
        <article class="slide-card" v-for="slide in slideRows" :key="slide.page">
          <span class="slide-page">{{ slide.page }}</span>
          <div>
            <h3>{{ slide.title }}</h3>
            <p>{{ slide.core }}</p>
            <p class="speaker-note">{{ slide.speaker }}</p>
          </div>
        </article>
      </div>
      <MarkdownRenderer v-else :content="resource.content" />
    </template>

    <template v-else-if="resource.type === 'visual_card'">
      <div class="format-hero">
        <span>Visual Cards</span>
        <strong>{{ visualCards.length || '未识别' }} 张可视化学习卡</strong>
        <p>用卡片化结构集中展示概念、误区、自测和动画提示。</p>
      </div>
      <div class="learning-cards" v-if="visualCards.length">
        <article class="learning-card" v-for="card in visualCards" :key="card.id">
          <h4>{{ card.title }}</h4>
          <p class="muted">{{ card.tagline }}</p>
          <p><strong>知识点：</strong>{{ card.what }}</p>
          <p><strong>常见误区：</strong>{{ card.pitfall }}</p>
          <p><strong>自测问题：</strong>{{ card.check_question }}</p>
          <p class="muted">动画建议：{{ card.animation_hint }}</p>
        </article>
      </div>
      <pre v-else>{{ resource.content }}</pre>
    </template>

    <template v-else-if="resource.content_format === 'mermaid'">
      <div class="format-hero">
        <span>Mind Map</span>
        <strong>可视化知识结构</strong>
        <p>思维导图会先清洗常见语法问题，再异步渲染；失败时保留原文。</p>
      </div>
      <MermaidRenderer :content="resource.content" />
    </template>

    <template v-else-if="resource.content_format === 'code'">
      <div class="format-hero">
        <span>Code Lab</span>
        <strong>可实践代码案例</strong>
        <p>用代码块承载可复制的实验步骤和最小示例。</p>
      </div>
      <pre>{{ resource.content }}</pre>
    </template>

    <template v-else>
      <div class="format-hero">
        <span>Reading</span>
        <strong>讲解型学习材料</strong>
        <p>适合先阅读概念，再配合导图、分镜或练习巩固。</p>
      </div>
      <MarkdownRenderer :content="resource.content" />
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Resource } from '../types'
import MarkdownRenderer from './MarkdownRenderer.vue'
import MermaidRenderer from './MermaidRenderer.vue'

interface StoryboardRow {
  time: string
  scene: string
  voiceover: string
  caption: string
}

interface SlideRow {
  page: string
  title: string
  core: string
  speaker: string
}

interface VisualCard {
  id: string
  title: string
  tagline: string
  what: string
  pitfall: string
  check_question: string
  animation_hint: string
}

interface QuizQuestion {
  level?: string
  difficulty?: string
  type?: string
  question: string
  options?: string[]
  assessment_point?: string
}

interface AnimationFrame {
  id: string
  title: string
  caption: string
  focus: string
  visual: string
}

interface AnimationPayload {
  kind?: string
  duration_seconds?: number
  playback_note?: string
  scenario?: string
  frames?: AnimationFrame[]
  teacher_prompt?: string
}

const props = defineProps<{ resource: Resource | null }>()
const activeFrameIndex = ref(0)

const typeLabels: Record<string, string> = {
  lecture_doc: '图文讲解',
  mind_map: '思维导图',
  quiz: '交互练习',
  reading: '拓展阅读',
  media_script: '视频/动画脚本',
  animation_demo: '可播放动画',
  ppt_draft: 'PPT 大纲',
  visual_card: '可视化学习卡',
  code_case: '代码实验'
}

const formatLabels: Record<Resource['content_format'], string> = {
  markdown: 'Markdown',
  mermaid: 'Mermaid',
  json: 'JSON',
  code: 'Code'
}

function parseMarkdownTable(content: string, ignoredHeader: string) {
  return content
    .split(/\r?\n/)
    .filter(line => line.startsWith('|') && !line.includes('---') && !line.includes(ignoredHeader))
    .map(line => line.split('|').map(item => item.trim()).filter(Boolean))
}

const resourceTypeLabel = computed(() => props.resource ? typeLabels[props.resource.type] || props.resource.type : '')
const contentFormatLabel = computed(() => props.resource ? formatLabels[props.resource.content_format] : '')
const reviewStatusLabel = computed(() => {
  if (!props.resource) return ''
  if (props.resource.review_status === 'passed') return '已通过'
  if (props.resource.review_status === 'needs_revision') return '需修订'
  return '已阻止'
})
const resourceShellClass = computed(() => {
  if (!props.resource) return ''
  return [`resource-format-${props.resource.content_format}`, `resource-type-${props.resource.type}`]
})

const animationPayload = computed<AnimationPayload | null>(() => {
  if (!props.resource || props.resource.type !== 'animation_demo') return null
  try {
    return JSON.parse(props.resource.content) as AnimationPayload
  } catch {
    return null
  }
})

const animationFrames = computed<AnimationFrame[]>(() => {
  const frames = animationPayload.value?.frames
  return Array.isArray(frames) ? frames.filter(frame => frame.title && frame.caption) : []
})

const activeFrame = computed(() => animationFrames.value[activeFrameIndex.value] || animationFrames.value[0])

watch(() => props.resource?.id, () => {
  activeFrameIndex.value = 0
})

const quizQuestions = computed<QuizQuestion[]>(() => {
  if (!props.resource || props.resource.type !== 'quiz') return []
  try {
    const parsed = JSON.parse(props.resource.content) as QuizQuestion[]
    return Array.isArray(parsed) ? parsed.filter(item => item.question) : []
  } catch {
    return []
  }
})

const storyboardRows = computed<StoryboardRow[]>(() => {
  if (!props.resource || props.resource.type !== 'media_script') return []
  return parseMarkdownTable(props.resource.content, '时间')
    .filter(parts => parts.length >= 4)
    .map(parts => ({
      time: parts[0],
      scene: parts[1],
      voiceover: parts[2],
      caption: parts[3]
    }))
})

const slideRows = computed<SlideRow[]>(() => {
  if (!props.resource || props.resource.type !== 'ppt_draft') return []
  return parseMarkdownTable(props.resource.content, '页码')
    .filter(parts => parts.length >= 4)
    .map(parts => ({
      page: parts[0],
      title: parts[1],
      core: parts[2],
      speaker: parts[3]
    }))
})

const productionNotes = computed(() => {
  if (!props.resource || props.resource.type !== 'media_script') return []
  return props.resource.content
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(line => line.startsWith('- '))
    .map(line => line.slice(2))
})

const visualCards = computed<VisualCard[]>(() => {
  if (!props.resource || props.resource.type !== 'visual_card') return []
  try {
    const parsed = JSON.parse(props.resource.content) as { cards?: VisualCard[] }
    return Array.isArray(parsed.cards) ? parsed.cards : []
  } catch {
    return []
  }
})
</script>
