<template>
  <section v-if="resource" class="panel resource-content" :class="resourceShellClass">
    <div class="resource-detail-head">
      <div>
        <span class="resource-kind">{{ resourceTypeLabel }}</span>
        <h2>{{ resource.title }}</h2>
        <div class="resource-meta compact">
          <span>{{ contentFormatLabel }}</span>
          <span>{{ resource.difficulty }}</span>
        </div>
      </div>
      <span class="status" :class="resource.review_status">{{ reviewStatusLabel }}</span>
    </div>

    <div class="resource-intel-grid">
      <article class="resource-intel-card">
        <span>资源类型</span>
        <strong>{{ resourceTypeLabel }}</strong>
        <small>{{ contentFormatLabel }} · {{ resource.difficulty || '难度未返回' }}</small>
      </article>
      <article class="resource-intel-card">
        <span>推荐原因</span>
        <strong>{{ personalizationReason }}</strong>
        <small>{{ resource.target_profile?.length ? '适合当前学习状态' : '暂无更多说明' }}</small>
      </article>
      <article class="resource-intel-card">
        <span>内容检查</span>
        <strong>{{ reviewStatusLabel }}</strong>
        <small>{{ simpleReviewReason }}</small>
      </article>
      <article class="resource-intel-card">
        <span>关联学习路径</span>
        <strong>{{ relatedPathLabel }}</strong>
        <small>{{ relatedPathHint }}</small>
      </article>
    </div>

    <template v-if="resource.type === 'animation_demo'">
      <div class="format-hero">
        <span>动画演示</span>
        <strong>{{ animationFrames.length || '未识别' }} 个教学场景</strong>
        <p>{{ cleanText(animationPayload?.playback_note || '可直接在系统内预览的教学动画。') }}</p>
      </div>
      <div v-if="animationFrames.length" class="animation-player">
        <div class="animation-stage">
          <div class="animation-orbit" :class="`visual-${activeFrame.visual}`" aria-hidden="true">
            <span class="data-dot dot-a"></span>
            <span class="data-dot dot-b"></span>
            <span class="data-dot dot-c"></span>
            <span class="model-node">{{ cleanText(activeFrame.focus) }}</span>
            <span class="signal-line"></span>
          </div>
          <div class="animation-caption">
            <span>场景 {{ activeFrameIndex + 1 }}/{{ animationFrames.length }}</span>
            <h3>{{ cleanText(activeFrame.title) }}</h3>
            <p>{{ cleanText(activeFrame.caption) }}</p>
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
            <strong>{{ cleanText(frame.focus) }}</strong>
          </button>
        </div>
        <p class="speaker-note" v-if="animationPayload?.teacher_prompt">{{ cleanText(animationPayload.teacher_prompt) }}</p>
      </div>
      <pre v-else>{{ cleanContent }}</pre>
    </template>

    <template v-else-if="resource.type === 'quiz'">
      <div class="format-hero">
        <span>互动练习</span>
        <strong>{{ quizQuestions.length || '未识别' }} 道分层练习</strong>
        <p>题目按类型、难度和考查点整理，适合直接进入练习。</p>
      </div>
      <div v-if="quizQuestions.length" class="quiz-preview-list">
        <article class="quiz-preview-card" v-for="(question, index) in quizQuestions" :key="`${question.question}-${index}`">
          <div class="quiz-preview-head">
            <span>题目 {{ index + 1 }}</span>
            <div class="chips">
              <span class="chip">{{ cleanText(question.type || '问答题') }}</span>
              <span class="chip">{{ cleanText(question.difficulty || question.level || '基础') }}</span>
            </div>
          </div>
          <p class="quiz-question">{{ cleanText(question.question) }}</p>
          <div v-if="question.options?.length" class="option-list compact-options">
            <span v-for="option in question.options" :key="option" class="option-pill">{{ cleanText(option) }}</span>
          </div>
          <p class="muted compact" v-if="question.assessment_point">考查点：{{ cleanText(question.assessment_point) }}</p>
        </article>
      </div>
      <pre v-else>{{ cleanContent }}</pre>
    </template>

    <template v-else-if="resource.type === 'media_script'">
      <div class="format-hero">
        <span>视频脚本</span>
        <strong>{{ storyboardRows.length || '未识别' }} 个分镜</strong>
        <p>这里是脚本和分镜，不是已经生成的 mp4 视频。</p>
      </div>
      <div class="storyboard-deck" v-if="storyboardRows.length">
        <article class="storyboard-card" v-for="(row, index) in storyboardRows" :key="`${row.time}-${index}`">
          <div class="storyboard-card-head">
            <span>镜头 {{ index + 1 }}</span>
            <strong>{{ cleanText(row.time) }}</strong>
          </div>
          <div class="storyboard-visual">{{ cleanText(row.scene) }}</div>
          <dl>
            <dt>旁白</dt>
            <dd>{{ cleanText(row.voiceover) }}</dd>
            <dt>屏幕文字</dt>
            <dd>{{ cleanText(row.caption) }}</dd>
          </dl>
        </article>
      </div>
      <p v-else class="empty">未识别到分镜表格，以下保留脚本文本。</p>
      <div v-if="productionNotes.length" class="production-notes">
        <h3>制作提示</h3>
        <div class="chips">
          <span class="chip" v-for="note in productionNotes" :key="note">{{ cleanText(note) }}</span>
        </div>
      </div>
      <pre v-if="!storyboardRows.length">{{ cleanContent }}</pre>
    </template>

    <template v-else-if="resource.type === 'ppt_draft'">
      <div class="format-hero">
        <span>PPT 草稿</span>
        <strong>{{ slideRows.length || '未识别' }} 页课堂幻灯片</strong>
        <p>按页面主题、核心内容和讲者提示整理。</p>
      </div>
      <div class="slide-outline" v-if="slideRows.length">
        <article class="slide-card" v-for="slide in slideRows" :key="slide.page">
          <span class="slide-page">{{ cleanText(slide.page) }}</span>
          <div>
            <h3>{{ cleanText(slide.title) }}</h3>
            <p>{{ cleanText(slide.core) }}</p>
            <p class="speaker-note">{{ cleanText(slide.speaker) }}</p>
          </div>
        </article>
      </div>
      <MarkdownRenderer v-else :content="cleanContent" />
    </template>

    <template v-else-if="resource.type === 'visual_card'">
      <div class="format-hero">
        <span>学习卡片</span>
        <strong>{{ visualCards.length || '未识别' }} 张可视化卡片</strong>
        <p>集中展示概念、误区、自测和动画提示。</p>
      </div>
      <div class="learning-cards" v-if="visualCards.length">
        <article class="learning-card" v-for="card in visualCards" :key="card.id">
          <h4>{{ cleanText(card.title) }}</h4>
          <p class="muted">{{ cleanText(card.tagline) }}</p>
          <p><strong>知识点：</strong>{{ cleanText(card.what) }}</p>
          <p><strong>常见误区：</strong>{{ cleanText(card.pitfall) }}</p>
          <p><strong>自测问题：</strong>{{ cleanText(card.check_question) }}</p>
          <p class="muted">动画建议：{{ cleanText(card.animation_hint) }}</p>
        </article>
      </div>
      <pre v-else>{{ cleanContent }}</pre>
    </template>

    <template v-else-if="resource.content_format === 'mermaid'">
      <div class="format-hero">
        <span>思维导图</span>
        <strong>可视化知识结构</strong>
        <p>用图示梳理本节概念之间的关系。</p>
      </div>
      <MermaidRenderer :content="cleanContent" />
    </template>

    <template v-else-if="resource.content_format === 'code'">
      <div class="format-hero">
        <span>代码实验</span>
        <strong>可运行的最小案例</strong>
        <p>用代码块承载可复现实验步骤和示例。</p>
      </div>
      <pre>{{ cleanContent }}</pre>
    </template>

    <template v-else>
      <div class="format-hero">
        <span>阅读材料</span>
        <strong>讲解型学习内容</strong>
        <p>适合先阅读概念，再配合导图、练习或实验巩固。</p>
      </div>
      <MarkdownRenderer :content="cleanContent" />
    </template>

    <details class="source-drawer">
      <summary>这个资料来自哪里？</summary>
      <div class="source-drawer-body">
        <div>
          <h3>来源说明</h3>
          <div v-if="evidenceItems.length" class="source-list">
            <article v-for="(source, index) in evidenceItems" :key="source.id || index" class="source-item">
              <span>{{ sourceLabel(source.id, index) }}</span>
              <p>{{ source.text || '该来源暂未返回原文片段。' }}</p>
            </article>
          </div>
          <p v-else class="muted compact">暂无可展示来源说明。</p>
        </div>
        <div>
          <h3>内容检查状态</h3>
          <p class="compact">{{ friendlyAudit }}</p>
          <ul v-if="resource.review_notes?.length" class="audit-list">
            <li v-for="note in resource.review_notes.slice(0, 2)" :key="note">{{ note }}</li>
          </ul>
          <p v-else class="muted compact">暂无更多检查说明。</p>
        </div>
      </div>
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EvidenceSource, Resource } from '../types'
import { useLearningStore } from '../store'
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
const store = useLearningStore()
const activeFrameIndex = ref(0)

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

const formatLabels: Record<Resource['content_format'], string> = {
  markdown: '文档',
  mermaid: '图示',
  json: '互动',
  code: '代码'
}

function cleanText(value: unknown) {
  return String(value ?? '')
    .replace(/\s*\[来源:\s*[^\]]+?\]/g, '')
    .replace(/\s*\[Source:\s*[^\]]+?\]/gi, '')
    .trim()
}

function parseMarkdownTable(content: string, ignoredHeader: string) {
  return content
    .split(/\r?\n/)
    .filter(line => line.startsWith('|') && !line.includes('---') && !line.includes(ignoredHeader))
    .map(line => line.split('|').map(item => cleanText(item)).filter(Boolean))
}

function sourceLabel(id: string, index: number) {
  const raw = id || `source-${index + 1}`
  const section = raw.includes('#') ? raw.split('#')[1] : raw
  const sectionName = section.replace(/:\d+$/, '')
  const labels: Record<string, string> = {
    objectives: '学习目标',
    concept_cards: '概念卡片',
    detailed_concepts: '详细知识点',
    difficulties: '学习难点',
    misconceptions: '常见误区',
    real_cases: '真实案例',
    code_labs: '代码实验',
    practice_questions: '练习题',
    reading: '拓展阅读',
    task: '实践任务'
  }
  const readable = labels[sectionName] || '课程知识片段'
  return `来源 ${index + 1}：${readable}`
}

const resourceTypeLabel = computed(() => props.resource ? typeLabels[props.resource.type] || props.resource.type : '')
const contentFormatLabel = computed(() => props.resource ? formatLabels[props.resource.content_format] : '')
const cleanContent = computed(() => cleanText(props.resource?.content || ''))

const reviewStatusLabel = computed(() => {
  if (!props.resource) return ''
  if (props.resource.review_status === 'passed') return '可学习'
  if (props.resource.review_status === 'needs_revision') return '待完善'
  return '不可用'
})

const friendlyAudit = computed(() => {
  if (!props.resource) return ''
  if (props.resource.review_status === 'passed') return '这份内容已经通过系统检查。'
  if (props.resource.review_status === 'needs_revision') return '这份内容可以查看，但系统建议继续完善依据或表达。'
  return '这份内容暂不建议使用。'
})
const simpleReviewReason = computed(() => {
  const reason = props.resource?.audit_reason || props.resource?.review_reason || ''
  if (!reason) return '暂无更多说明'
  const friendly = reason.replace(/^fallback_reason:\s*/i, '系统使用课程知识库兜底生成：')
  return friendly.length > 42 ? `${friendly.slice(0, 42)}...` : friendly
})

const personalizationReason = computed(() => {
  if (props.resource?.personalized_reason) return props.resource.personalized_reason
  const targets = props.resource?.target_profile?.filter(Boolean) || []
  if (targets.length) return targets.slice(0, 3).join('、')
  return '暂无结构化推荐原因'
})

const relatedPathSteps = computed(() => {
  if (!props.resource || !store.path?.steps?.length) return []
  return store.path.steps.filter(step => step.recommended_resource_ids.includes(props.resource?.id || ''))
})

const relatedPathLabel = computed(() => {
  if (!store.path?.steps?.length) return '路径未同步'
  if (!relatedPathSteps.value.length) return '暂无关联阶段'
  return `${relatedPathSteps.value.length} 个阶段`
})

const relatedPathHint = computed(() => {
  if (!store.path?.steps?.length) return '当前还没有学习任务清单'
  if (!relatedPathSteps.value.length) return '这份资料暂未出现在当前任务清单'
  return relatedPathSteps.value.map(step => step.title).join('、')
})

const resourceShellClass = computed(() => {
  if (!props.resource) return ''
  return [`resource-format-${props.resource.content_format}`, `resource-type-${props.resource.type}`]
})

const evidenceItems = computed<EvidenceSource[]>(() => {
  if (!props.resource) return []
  if (props.resource.evidence_sources?.length) return props.resource.evidence_sources
  return (props.resource.source_refs || []).map(id => ({ id, text: '', relevance_score: 0, reason: '' }))
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
  return parseMarkdownTable(cleanContent.value, '时间')
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
  return parseMarkdownTable(cleanContent.value, '页码')
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
  return cleanContent.value
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
