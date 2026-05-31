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
      <span class="status" :class="reviewStatusClass">{{ reviewStatusLabel }}</span>
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
      <div v-if="animationHtmlDocument" ref="animationPreviewRef" class="html-animation-preview">
        <button class="fullscreen-preview-button" type="button" @click="openFullscreenPreview('animation')">
          全屏展示
        </button>
        <iframe
          title="HTML 教学动画预览"
          :srcdoc="animationHtmlDocument"
          sandbox=""
          loading="lazy"
        ></iframe>
      </div>
      <div v-else-if="animationFrames.length" class="animation-player">
        <div class="animation-controls">
          <button class="btn primary" type="button" @click="toggleAnimationPlayback">
            {{ isAnimationPlaying ? '暂停' : '播放' }}
          </button>
          <button class="btn ghost" type="button" @click="previousAnimationFrame">上一步</button>
          <button class="btn ghost" type="button" @click="nextAnimationFrame">下一步</button>
          <div class="animation-progress" role="progressbar" :aria-valuenow="animationProgressPercent" aria-valuemin="0" aria-valuemax="100">
            <span :style="{ width: `${animationProgressPercent}%` }"></span>
          </div>
          <small>{{ activeFrameIndex + 1 }}/{{ animationFrames.length }} · {{ animationDurationLabel }}</small>
        </div>
        <div class="animation-stage">
          <div class="animation-orbit" :class="[`visual-${activeFrame.visual}`, `template-${animationTemplate}`, `model-${animationTeachingModel}`, { playing: isAnimationPlaying }]" aria-hidden="true">
            <span class="orbit-label">{{ animationPayload?.scenario || resource.title }}</span>
            <div v-if="animationTeachingModel === 'reinforcement_loop'" class="template-scene model-scene reinforcement-scene">
              <div class="rl-grid">
                <span v-for="index in 9" :key="index" class="rl-cell" :class="{ agent: rlAgentCell === index, goal: index === 9, visited: index < rlAgentCell }"></span>
                <span class="rl-agent">智能体</span>
                <span class="rl-goal">目标</span>
              </div>
              <span class="rl-action-arrow" :class="`step-${activeFrameIndex + 1}`">动作</span>
              <span class="rl-reward" :class="{ positive: activeFrameIndex >= 2 }">{{ activeFrameIndex >= 2 ? '+1 奖励' : '等待反馈' }}</span>
              <div class="rl-policy">
                <span>策略倾向</span>
                <i :style="{ width: `${45 + activeFrameIndex * 15}%` }"></i>
              </div>
            </div>
            <div v-else-if="animationTeachingModel === 'search_pathfinding'" class="template-scene model-scene pathfinding-scene">
              <div class="path-map">
                <span v-for="index in 12" :key="index" class="path-node" :class="{ start: index === 1, goal: index === 12, open: index <= activeFrameIndex + 4, chosen: pathChosenNodes.includes(index) }">
                  {{ index === 1 ? '起' : index === 12 ? '终' : index }}
                </span>
              </div>
              <div class="path-scoreboard">
                <span>g 代价：{{ activeFrameIndex + 2 }}</span>
                <span>h 启发：{{ Math.max(1, 5 - activeFrameIndex) }}</span>
                <strong>优先扩展：{{ cleanText(activeSceneObjects[activeFrameIndex] || activeFrame.focus) }}</strong>
              </div>
            </div>
            <div v-else-if="animationTeachingModel === 'generalization_curve'" class="template-scene model-scene generalization-scene">
              <div class="curve-board">
                <span class="curve-line train"></span>
                <span class="curve-line valid" :class="{ diverge: activeFrameIndex >= 2 }"></span>
                <span class="curve-dot" :style="{ left: `${22 + activeFrameIndex * 18}%`, bottom: `${44 - activeFrameIndex * 5}%` }"></span>
                <small class="axis x-axis">训练轮次</small>
                <small class="axis y-axis">误差</small>
              </div>
              <div class="sample-split">
                <span>旧题：{{ activeFrameIndex >= 1 ? '更熟练' : '待学习' }}</span>
                <span>新题：{{ activeFrameIndex >= 2 ? '开始暴露问题' : '保留检查' }}</span>
              </div>
            </div>
            <div v-else-if="animationTeachingModel === 'retrieval_tool_loop'" class="template-scene model-scene retrieval-scene">
              <span class="retrieval-query">{{ cleanText(activeSceneObjects[0]) }}</span>
              <span class="retrieval-source source-a">{{ cleanText(activeSceneObjects[1]) }}</span>
              <span class="retrieval-source source-b">{{ cleanText(activeSceneObjects[2]) }}</span>
              <span class="retrieval-answer">{{ cleanText(activeSceneObjects[3]) }}</span>
              <span class="retrieval-link link-a"></span>
              <span class="retrieval-link link-b"></span>
            </div>
            <div v-else-if="isStructuredAnimation" class="template-scene model-scene concept-process-scene">
              <div v-for="(object, index) in activeSceneObjects" :key="`${object}-${index}`" class="process-node" :class="{ active: index <= activeFrameIndex }">
                <span>{{ index + 1 }}</span>
                <strong>{{ cleanText(object) }}</strong>
              </div>
              <span class="process-flow"></span>
              <div class="process-model-label">{{ teachingModelLabel }}</div>
            </div>
            <div v-else-if="animationTemplate === 'network'" class="template-scene network-scene">
              <div class="sentence-track">
                <span v-for="(token, index) in attentionTokens" :key="`${token}-${index}`" :class="{ hot: index === attentionHotIndex }">{{ token }}</span>
              </div>
              <div class="attention-map">
                <span
                  v-for="(token, index) in attentionTokens"
                  :key="`node-${token}-${index}`"
                  class="attention-node"
                  :class="[`attention-node-${index + 1}`, { hot: index === attentionHotIndex }]"
                >
                  {{ token }}
                </span>
                <span class="attention-link attention-link-a"></span>
                <span class="attention-link attention-link-b"></span>
                <span class="attention-link attention-link-c"></span>
                <span class="attention-link attention-link-d"></span>
                <span class="attention-pulse"></span>
              </div>
              <div class="attention-output">
                <span>模型重点看</span>
                <strong>{{ attentionTokens[attentionHotIndex] }}</strong>
              </div>
            </div>
            <div v-else-if="animationTemplate === 'search'" class="template-scene search-scene">
              <span v-for="index in 9" :key="index" class="search-cell" :class="{ active: index <= activeFrameIndex + 3, target: index === 9 }"></span>
              <span class="search-agent">AI</span>
              <span class="search-target">{{ cleanText(activeSceneObjects[3]) }}</span>
            </div>
            <div v-else-if="animationTemplate === 'dialogue'" class="template-scene dialogue-scene">
              <span class="chat-bubble-demo user">{{ cleanText(activeSceneObjects[0]) }}</span>
              <span class="chat-bubble-demo model">{{ beginnerScene.machine }}</span>
              <span class="chat-bubble-demo answer">{{ cleanText(activeSceneObjects[3]) }}</span>
              <span class="typing-dot"></span>
            </div>
            <div v-else-if="animationTemplate === 'risk'" class="template-scene risk-scene">
              <span class="case-card">{{ cleanText(activeSceneObjects[0]) }}</span>
              <span class="risk-meter"><i></i></span>
              <span class="guardrail-card">{{ cleanText(activeSceneObjects[3]) }}</span>
              <span class="warning-pulse">!</span>
            </div>
            <div v-else-if="animationTemplate === 'compare'" class="template-scene compare-scene">
              <div><span>{{ cleanText(activeSceneObjects[0]) }}</span><strong>{{ storyLabels.source }}</strong></div>
              <div><span>{{ cleanText(activeSceneObjects[2]) }}</span><strong>{{ storyLabels.result }}</strong></div>
              <span class="compare-divider">VS</span>
            </div>
            <div v-else class="learning-storyboard">
              <div class="story-zone source-zone">
                <span class="zone-title">{{ storyLabels.source }}</span>
                <span class="student-avatar">学生A</span>
                <span class="student-card">{{ activeSceneObjects[0] }}</span>
                <span class="student-card muted-card">{{ activeSceneObjects[1] }}</span>
              </div>
              <div class="story-zone machine-zone">
                <span class="zone-title">{{ storyLabels.machine }}</span>
                <span class="machine-core">{{ beginnerScene.machine }}</span>
                <span class="pulse-ring"></span>
              </div>
              <div class="story-zone result-zone">
                <span class="zone-title">{{ storyLabels.result }}</span>
                <span class="recommend-card">{{ activeSceneObjects[2] }}</span>
                <span class="recommend-card accent-card">{{ activeSceneObjects[3] }}</span>
              </div>
              <span class="moving-signal"></span>
            </div>
            <div v-if="activeFrame.visual === 'loss'" class="loss-chart">
              <span class="loss-line train"></span>
              <span class="loss-line valid"></span>
              <small>训练损失</small>
              <small>验证损失</small>
            </div>
            <div v-else-if="activeFrame.visual === 'overfit'" class="overfit-compare">
              <span>旧题全会</span>
              <span>新题翻车</span>
            </div>
          </div>
          <div class="animation-caption">
            <span>第 {{ activeFrameIndex + 1 }} 幕：{{ activeStepLabel }}</span>
            <h3>{{ activeTeachingTitle }}</h3>
            <p>{{ activeTeachingExplain }}</p>
            <p v-if="activeTeachingAction" class="animation-action">{{ activeTeachingAction }}</p>
            <p v-if="activeTeachingMisconception" class="animation-misconception">常见误区：{{ activeTeachingMisconception }}</p>
            <div class="animation-takeaway">
              <span>你只要记住</span>
              <strong>{{ activeTeachingRemember }}</strong>
            </div>
          </div>
        </div>
        <div class="animation-strip">
          <button
            v-for="(frame, index) in animationFrames"
            :key="frame.id"
            type="button"
            class="animation-step"
            :class="{ active: index === activeFrameIndex }"
            @click="selectAnimationFrame(index)"
          >
            <span>{{ index + 1 }}</span>
            <strong>{{ beginnerStepTitle(frame, index) }}</strong>
          </button>
        </div>
        <details class="animation-script" v-if="animationPayload?.teacher_prompt">
          <summary>展开教师旁白</summary>
          <p>{{ cleanText(animationPayload.teacher_prompt) }}</p>
        </details>
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

    <template v-else-if="resource.type === 'html_ppt'">
      <div class="format-hero">
        <span>HTML PPT</span>
        <strong>{{ htmlPptSlides.length || slideRows.length || '未识别' }} 页网页幻灯片</strong>
        <p>可直接在页面内预览的 16:9 教学课件。</p>
      </div>
      <div v-if="htmlPptDocument" ref="pptPreviewRef" class="html-ppt-preview">
        <button class="fullscreen-preview-button" type="button" @click="openFullscreenPreview('ppt')">
          全屏展示
        </button>
        <iframe
          title="HTML PPT 课件预览"
          :srcdoc="htmlPptDocument"
          sandbox=""
          loading="lazy"
        ></iframe>
      </div>
      <div class="slide-outline" v-if="htmlPptOutlineRows.length">
        <article class="slide-card" v-for="slide in htmlPptOutlineRows" :key="slide.page">
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
          <ul v-if="displayedReviewNotes.length" class="audit-list">
            <li v-for="note in displayedReviewNotes" :key="note">{{ note }}</li>
          </ul>
          <p v-else class="muted compact">暂无更多检查说明。</p>
        </div>
      </div>
    </details>
    <div
      v-if="fullscreenPreviewType"
      ref="fullscreenOverlayRef"
      class="resource-fullscreen-viewer"
      :class="`fullscreen-${fullscreenPreviewType}`"
      @click.self="closeFullscreenPreview"
    >
      <div class="resource-fullscreen-toolbar">
        <button
          v-if="fullscreenPreviewType === 'ppt'"
          class="fullscreen-nav-button"
          type="button"
          :disabled="fullscreenPptIndex <= 0"
          @click="previousFullscreenPptSlide"
        >
          上一页
        </button>
        <span v-if="fullscreenPreviewType === 'ppt'" class="fullscreen-page-indicator">
          {{ fullscreenPptIndex + 1 }} / {{ fullscreenPptTotal }}
        </span>
        <button
          v-if="fullscreenPreviewType === 'ppt'"
          class="fullscreen-nav-button"
          type="button"
          :disabled="fullscreenPptIndex >= fullscreenPptTotal - 1"
          @click="nextFullscreenPptSlide"
        >
          下一页
        </button>
        <button class="fullscreen-close-button" type="button" @click="closeFullscreenPreview">
          退出全屏展示
        </button>
      </div>
      <div class="resource-fullscreen-stage">
        <iframe
          v-if="fullscreenPreviewType === 'animation'"
          title="HTML 教学动画全屏展示"
          :srcdoc="fullscreenAnimationDocument"
          sandbox=""
        ></iframe>
        <iframe
          v-else
          title="HTML PPT 全屏放映"
          :srcdoc="fullscreenPptDocument"
          sandbox=""
        ></iframe>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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

interface HtmlPPTSlide {
  title?: string
  subtitle?: string
  layout?: string
  bullets?: string[]
  speaker_note?: string
  visual_type?: string
  accent?: string
}

interface HtmlPPTPayload {
  kind?: string
  title?: string
  theme?: string
  slides?: HtmlPPTSlide[]
  html_document?: string
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
  scene_objects?: string[]
  metric?: string
  action?: string
  misconception?: string
  takeaway?: string
}

interface AnimationPayload {
  schema_version?: number
  kind?: string
  teaching_model_id?: string
  template?: string
  concept?: string
  topic?: string
  duration_seconds?: number
  playback_note?: string
  scenario?: string
  frames?: AnimationFrame[]
  teacher_prompt?: string
  html_document?: string
}

interface BeginnerScene {
  eyebrow: string
  title: string
  explain: string
  remember: string
  machine: string
}

const props = defineProps<{ resource: Resource | null }>()
const store = useLearningStore()
const activeFrameIndex = ref(0)
const isAnimationPlaying = ref(false)
const animationElapsedMs = ref(0)
const animationPreviewRef = ref<HTMLElement | null>(null)
const pptPreviewRef = ref<HTMLElement | null>(null)
type FullscreenPreviewType = 'animation' | 'ppt'
const fullscreenPreviewType = ref<FullscreenPreviewType | null>(null)
const fullscreenOverlayRef = ref<HTMLElement | null>(null)
const fullscreenPptIndex = ref(0)
let animationTimer: number | undefined
const animationFrameDurationMs = 3200

const typeLabels: Record<string, string> = {
  lecture_doc: '图文讲解',
  mind_map: '思维导图',
  quiz: '互动练习',
  reading: '拓展阅读',
  media_script: '视频脚本',
  animation_demo: '动画演示',
  html_ppt: 'HTML PPT',
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

async function openFullscreenPreview(type: FullscreenPreviewType) {
  fullscreenPreviewType.value = type
  if (type === 'ppt') fullscreenPptIndex.value = 0
  await nextTick()
  const target = fullscreenOverlayRef.value
  if (!target || document.fullscreenElement === target) return
  try {
    await target.requestFullscreen()
  } catch {
    // The fixed overlay still covers the viewport if the browser blocks fullscreen.
  }
}

async function closeFullscreenPreview() {
  const target = fullscreenOverlayRef.value
  fullscreenPreviewType.value = null
  if (document.fullscreenElement === target) {
    try {
      await document.exitFullscreen()
    } catch {
      // Ignore browser-specific fullscreen exit errors.
    }
  }
}

function previousFullscreenPptSlide() {
  fullscreenPptIndex.value = Math.max(0, fullscreenPptIndex.value - 1)
}

function nextFullscreenPptSlide() {
  fullscreenPptIndex.value = Math.min(fullscreenPptTotal.value - 1, fullscreenPptIndex.value + 1)
}

function handleFullscreenKeydown(event: KeyboardEvent) {
  if (!fullscreenPreviewType.value) return
  if (event.key === 'Escape') {
    void closeFullscreenPreview()
    return
  }
  if (fullscreenPreviewType.value !== 'ppt') return
  if (event.key === 'ArrowLeft') previousFullscreenPptSlide()
  if (event.key === 'ArrowRight') nextFullscreenPptSlide()
}

function handleFullscreenChange() {
  if (!document.fullscreenElement && fullscreenPreviewType.value) {
    fullscreenPreviewType.value = null
  }
}

function injectReadablePreviewCss(html: string, mode: 'animation' | 'ppt') {
  const styleId = `a3-readable-${mode}-preview`
  if (html.includes(styleId)) return html
  if (mode === 'ppt') {
    const css = `
<style id="${styleId}">
  html, body {
    width: 100% !important;
    min-width: 0 !important;
    min-height: 100% !important;
    overflow: auto !important;
    font-size: 14px !important;
  }
  body {
    margin: 0 !important;
    padding: 0 !important;
    background: #151b22 !important;
  }
  *, *::before, *::after {
    box-sizing: border-box !important;
    overflow-wrap: anywhere !important;
  }
  main, .deck, [class*="deck"] {
    display: grid !important;
    gap: clamp(18px, 2.2vw, 28px) !important;
    width: 100% !important;
    max-width: 1280px !important;
    margin: 0 auto !important;
    padding: clamp(18px, 2.4vw, 32px) !important;
    height: auto !important;
    min-height: 0 !important;
    overflow: visible !important;
  }
  .slide, section[class*="slide"], [class*="slide"] {
    position: relative !important;
    display: block !important;
    width: 100% !important;
    max-width: 1180px !important;
    height: auto !important;
    min-height: 0 !important;
    aspect-ratio: 16 / 9 !important;
    margin: 0 auto !important;
    padding: clamp(28px, 4vw, 58px) !important;
    overflow: hidden !important;
  }
  h1, h2 {
    font-size: clamp(28px, 3.2vw, 46px) !important;
    line-height: 1.12 !important;
    max-width: 78% !important;
  }
  p, li, small, span, strong, aside {
    font-size: clamp(14px, 1.25vw, 20px) !important;
    line-height: 1.45 !important;
    white-space: normal !important;
    text-overflow: clip !important;
  }
  ul, ol {
    display: grid !important;
    gap: 10px !important;
    max-width: 72% !important;
  }
  aside {
    max-width: 42% !important;
    overflow: visible !important;
  }
  @media (max-width: 900px) {
    main, .deck, [class*="deck"] {
      padding: 14px !important;
    }
    .slide, section[class*="slide"], [class*="slide"] {
      aspect-ratio: auto !important;
      min-height: 560px !important;
      padding: 24px !important;
    }
    h1, h2, ul, ol, aside {
      max-width: 100% !important;
    }
  }
</style>`
    if (/<\/head>/i.test(html)) {
      return html.replace(/<\/head>/i, `${css}</head>`)
    }
    return `${css}${html}`
  }
  const stageRatio = mode === 'animation' ? '16 / 9' : '16 / 9'
  const css = `
<style id="${styleId}">
  html, body {
    width: 100% !important;
    height: 100% !important;
    min-width: 0 !important;
    min-height: 0 !important;
    overflow: hidden !important;
    font-size: 14px !important;
  }
  body {
    margin: 0 !important;
    padding: 0 !important;
    display: grid !important;
    place-items: center !important;
  }
  *, *::before, *::after {
    box-sizing: border-box !important;
    overflow-wrap: anywhere !important;
  }
  main, body > section, body > div:first-child,
  [class*="stage"], [class*="slide"], [class*="canvas"], [class*="screen"] {
    width: min(100vw, calc(100vh * 16 / 9)) !important;
    height: min(100vh, calc(100vw * 9 / 16)) !important;
    min-height: 0 !important;
    max-height: 100vh !important;
    aspect-ratio: ${stageRatio} !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding: clamp(14px, 1.6vw, 26px) !important;
    overflow: visible !important;
  }
  h1 {
    font-size: clamp(24px, 3.2vw, 42px) !important;
    line-height: 1.15 !important;
  }
  h2 {
    font-size: clamp(18px, 2vw, 28px) !important;
    line-height: 1.2 !important;
  }
  p, li, small, span, strong {
    font-size: clamp(13px, 1.15vw, 18px) !important;
  }
  p, span, strong, small, b, em, li, div {
    max-width: 100% !important;
  }
  [class*="card"], [class*="panel"], [class*="box"], [class*="scene"] {
    min-width: 0 !important;
    min-height: 0 !important;
    max-height: 100% !important;
    overflow: visible !important;
  }
  [class*="footer"], [class*="bottom"], [class*="caption"], [class*="note"],
  [class*="takeaway"], [class*="summary"], [class*="explain"], [class*="tip"],
  [class*="subtitle"], [class*="narration"], [class*="story"], [class*="description"],
  [class*="desc"], [class*="badge-row"] {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.45 !important;
  }
  [class*="footer"], [class*="bottom"], [class*="caption"], [class*="note"],
  [class*="takeaway"], [class*="summary"], [class*="tip"], [class*="narration"],
  [class*="story"], [class*="description"], [class*="desc"], [class*="badge-row"] {
    position: relative !important;
    inset: auto !important;
    left: auto !important;
    right: auto !important;
    top: auto !important;
    bottom: auto !important;
    transform: none !important;
    display: flex !important;
    flex-wrap: wrap !important;
    align-items: flex-start !important;
    gap: 8px 10px !important;
    height: auto !important;
    min-height: 0 !important;
    padding: 8px 10px !important;
    margin-top: 10px !important;
  }
  [class*="footer"] > *, [class*="bottom"] > *, [class*="caption"] > *,
  [class*="note"] > *, [class*="takeaway"] > *, [class*="summary"] > *,
  [class*="tip"] > *, [class*="narration"] > *, [class*="story"] > *,
  [class*="description"] > *, [class*="desc"] > *, [class*="badge-row"] > * {
    position: relative !important;
    inset: auto !important;
    transform: none !important;
    flex: 0 1 auto !important;
    min-width: 0 !important;
    max-width: 100% !important;
  }
  p[style*="position"], span[style*="position"], strong[style*="position"],
  small[style*="position"], b[style*="position"], em[style*="position"] {
    position: relative !important;
    inset: auto !important;
    left: auto !important;
    right: auto !important;
    top: auto !important;
    bottom: auto !important;
    transform: none !important;
    display: inline-block !important;
    max-width: 100% !important;
    margin: 3px 6px 3px 0 !important;
  }
  @media (max-width: 900px) {
    body {
      overflow: hidden !important;
    }
    main, body > section, body > div:first-child,
    [class*="stage"], [class*="slide"], [class*="canvas"], [class*="screen"] {
      width: 100% !important;
      aspect-ratio: auto !important;
      min-height: 560px !important;
      padding: 16px !important;
    }
  }
</style>`
  if (/<\/head>/i.test(html)) {
    return html.replace(/<\/head>/i, `${css}</head>`)
  }
  return `${css}${html}`
}

function injectDocumentStyle(html: string, styleId: string, css: string) {
  if (!html || html.includes(styleId)) return html
  const styleTag = `<style id="${styleId}">\n${css}\n</style>`
  if (/<\/head>/i.test(html)) {
    return html.replace(/<\/head>/i, `${styleTag}</head>`)
  }
  return `${styleTag}${html}`
}

type AnimationDisplayMode = 'maze' | 'rag' | 'default'

function animationBaseCss(mode: AnimationDisplayMode, fullscreen = false) {
  const stageWidth = fullscreen ? '1280px' : '100%'
  const stageHeight = fullscreen ? '720px' : '100%'
  const stageMaxHeight = fullscreen ? '100%' : '100%'
  const visualMaxHeight = fullscreen ? '520px' : '500px'
  const shellPadding = fullscreen ? 'clamp(12px, 1.5vw, 22px)' : 'clamp(12px, 1.4vw, 20px)'
  return `
html, body {
  width: 100% !important;
  height: 100% !important;
  min-width: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  background: #ffffff !important;
}
*, *::before, *::after {
  box-sizing: border-box !important;
  overflow-wrap: anywhere !important;
}
body {
  display: grid !important;
  place-items: ${fullscreen ? 'center' : 'stretch'} !important;
}
main, body > section, body > div:first-child,
[class*="stage"], [class*="canvas"], [class*="screen"] {
  width: ${stageWidth} !important;
  max-width: 100% !important;
  height: ${stageHeight} !important;
  max-height: ${stageMaxHeight} !important;
  min-height: 0 !important;
  aspect-ratio: 16 / 9 !important;
  margin-left: auto !important;
  margin-right: auto !important;
  padding: ${shellPadding} !important;
  overflow: hidden !important;
}
main, body > section, body > div:first-child {
  display: grid !important;
  gap: clamp(8px, 1vw, 14px) !important;
}
[class*="visual"], [class*="diagram"], [class*="chart"], [class*="graph"],
[class*="scene"], [class*="board"], [class*="panel"], [class*="compare"],
[class*="content"], [class*="main"], [class*="body"] {
  min-width: 0 !important;
  min-height: 0 !important;
  max-width: 100% !important;
  max-height: 100% !important;
  overflow: visible !important;
}
svg, canvas, img, video {
  max-width: 100% !important;
  max-height: ${visualMaxHeight} !important;
  object-fit: contain !important;
}
h1 {
  font-size: clamp(22px, 2.7vw, 38px) !important;
  line-height: 1.15 !important;
}
h2 {
  font-size: clamp(17px, 1.8vw, 26px) !important;
  line-height: 1.2 !important;
}
p, li, small, span, strong, b, em {
  max-width: 100% !important;
  white-space: normal !important;
  overflow-wrap: anywhere !important;
  line-height: 1.38 !important;
}
[class*="footer"], [class*="bottom"], [class*="caption"], [class*="note"],
[class*="takeaway"], [class*="summary"], [class*="tip"], [class*="narration"],
[class*="story"], [class*="description"], [class*="desc"], [class*="badge-row"] {
  white-space: normal !important;
  overflow: visible !important;
  text-overflow: clip !important;
  line-height: 1.45 !important;
  display: flex !important;
  flex-wrap: wrap !important;
  gap: 8px 10px !important;
}
`
}

function animationModeCss(mode: AnimationDisplayMode, fullscreen = false) {
  if (mode === 'maze') {
    return `
main, body > section, body > div:first-child {
  grid-template-rows: minmax(0, 1fr) auto !important;
  gap: clamp(8px, 1.2vw, 16px) !important;
}
main > *, body > section > *, body > div:first-child > * {
  min-width: 0 !important;
  min-height: 0 !important;
  max-width: 100% !important;
  max-height: 100% !important;
}
header, [class*="hero"], [class*="banner"], [class*="intro"], [class*="cover"],
[class*="spotlight"], [class*="glow"], [class*="decor"], [class*="orb"] {
  max-height: 76px !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
header h1, [class*="hero"] h1, [class*="banner"] h1, [class*="cover"] h1 {
  font-size: clamp(20px, 2.2vw, 32px) !important;
  line-height: 1.08 !important;
  margin: 0 !important;
}
header p, [class*="hero"] p, [class*="banner"] p, [class*="cover"] p {
  display: none !important;
}
[class*="maze"], [class*="grid"], [class*="map"], [class*="rl"],
[class*="state"], [class*="action"], [class*="reward"], [class*="policy"] {
  min-width: 0 !important;
  min-height: 0 !important;
  max-width: 100% !important;
  max-height: 100% !important;
  overflow: visible !important;
}
[class*="maze"], [class*="map"], [class*="rl-grid"], [class*="path"] {
  align-self: stretch !important;
  justify-self: stretch !important;
  height: auto !important;
}
[class*="state"], [class*="action"], [class*="reward"], [class*="policy"] {
  padding: clamp(8px, 1vw, 14px) !important;
  line-height: 1.35 !important;
}
`
  }
  if (mode === 'rag') {
    return `
main, body > section, body > div:first-child {
  grid-template-rows: auto minmax(0, 1fr) auto !important;
}
header, [class*="hero"], [class*="banner"], [class*="intro"], [class*="cover"] {
  max-height: ${fullscreen ? '130px' : '118px'} !important;
  min-height: 0 !important;
  overflow: visible !important;
}
header p, [class*="hero"] p, [class*="banner"] p, [class*="cover"] p {
  display: block !important;
  margin-top: 6px !important;
  line-height: 1.25 !important;
}
[class*="retrieval"], [class*="rag"], [class*="RAG"], [class*="search"],
[class*="source"], [class*="evidence"], [class*="quote"], [class*="answer"],
[class*="flow"], [class*="pipeline"], [class*="process"] {
  min-width: 0 !important;
  min-height: 0 !important;
  max-width: 100% !important;
  max-height: 100% !important;
  overflow: visible !important;
}
[class*="retrieval"], [class*="rag"], [class*="RAG"], [class*="flow"],
[class*="pipeline"], [class*="process"] {
  align-self: stretch !important;
}
[class*="source"], [class*="evidence"], [class*="quote"], [class*="answer"] {
  padding: clamp(8px, 1vw, 14px) !important;
  line-height: 1.35 !important;
}
`
  }
  return `
main, body > section, body > div:first-child {
  grid-template-rows: auto minmax(0, 1fr) auto !important;
}
header, [class*="hero"], [class*="banner"], [class*="intro"], [class*="cover"] {
  max-height: ${fullscreen ? '118px' : '104px'} !important;
  min-height: 0 !important;
  overflow: hidden !important;
}
`
}

function injectAnimationPreviewCss(html: string, mode: AnimationDisplayMode) {
  return injectDocumentStyle(html, `a3-animation-preview-${mode}-v3`, `${animationBaseCss(mode, false)}
${animationModeCss(mode, false)}`)
}

function injectAnimationFullscreenCss(html: string, mode: AnimationDisplayMode) {
  return injectDocumentStyle(html, `a3-animation-fullscreen-${mode}-v3`, `${animationBaseCss(mode, true)}
${animationModeCss(mode, true)}
[class*="label"], [class*="tag"], [class*="badge"], [class*="axis"],
[class*="legend"], [class*="caption"], [class*="note"] {
  font-size: clamp(11px, 1vw, 16px) !important;
  line-height: 1.25 !important;
}
[class*="footer"], [class*="bottom"], [class*="caption"], [class*="note"],
[class*="takeaway"], [class*="summary"], [class*="tip"], [class*="narration"],
[class*="story"], [class*="description"], [class*="desc"], [class*="badge-row"] {
  position: relative !important;
  inset: auto !important;
  transform: none !important;
  display: flex !important;
  flex-wrap: wrap !important;
  align-items: flex-start !important;
  gap: 8px 10px !important;
  width: auto !important;
  height: auto !important;
  max-width: 100% !important;
  min-height: 0 !important;
  padding: 8px 10px !important;
  white-space: normal !important;
  overflow: visible !important;
}
`)
}

function injectPptPreviewCss(html: string) {
  return injectDocumentStyle(html, 'a3-ppt-preview-v2', `
html, body {
  width: 100% !important;
  min-width: 0 !important;
  min-height: 100% !important;
  margin: 0 !important;
  overflow: auto !important;
  background: #151b22 !important;
}
*, *::before, *::after {
  box-sizing: border-box !important;
  overflow-wrap: anywhere !important;
}
main, .deck, [class*="deck"] {
  display: grid !important;
  gap: clamp(18px, 2.2vw, 28px) !important;
  width: 100% !important;
  max-width: 1280px !important;
  margin: 0 auto !important;
  padding: clamp(18px, 2.4vw, 32px) !important;
  height: auto !important;
  overflow: visible !important;
}
section.slide, .deck > .slide, main > .slide {
  position: relative !important;
  display: block !important;
  width: 100% !important;
  max-width: 1180px !important;
  height: auto !important;
  min-height: 0 !important;
  aspect-ratio: 16 / 9 !important;
  margin: 0 auto !important;
  overflow: hidden !important;
}
`)
}

function injectPptFullscreenCss(html: string, slideIndex: number) {
  const active = slideIndex + 1
  return injectDocumentStyle(html, `a3-ppt-fullscreen-v3-${active}`, `
html, body {
  width: 100% !important;
  height: 100% !important;
  min-width: 0 !important;
  min-height: 0 !important;
  margin: 0 !important;
  overflow: hidden !important;
  background: #151b22 !important;
}
*, *::before, *::after {
  box-sizing: border-box !important;
  overflow-wrap: anywhere !important;
}
body {
  display: grid !important;
  place-items: center !important;
}
main, .deck, [class*="deck"] {
  display: block !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
  overflow: hidden !important;
}
section.slide,
article.slide,
div.slide,
.deck > .slide,
main > .slide {
  display: none !important;
}
section.slide:nth-of-type(${active}),
article.slide:nth-of-type(${active}),
div.slide:nth-of-type(${active}),
.deck > .slide:nth-of-type(${active}),
main > .slide:nth-of-type(${active}) {
  display: block !important;
  position: relative !important;
  width: 100% !important;
  height: 100% !important;
  min-height: 0 !important;
  max-width: 100% !important;
  max-height: 100% !important;
  aspect-ratio: 16 / 9 !important;
  margin: 0 !important;
  padding: clamp(28px, 4vw, 58px) !important;
  overflow: hidden !important;
}
h1, h2 {
  font-size: clamp(28px, 3.2vw, 48px) !important;
  line-height: 1.12 !important;
  max-width: 78% !important;
}
p, li, small, span, strong, aside {
  font-size: clamp(14px, 1.3vw, 20px) !important;
  line-height: 1.45 !important;
  white-space: normal !important;
  text-overflow: clip !important;
}
ul, ol {
  max-width: 72% !important;
}
aside {
  max-width: 42% !important;
  overflow: visible !important;
}
`)
}

function countHtmlPptSlides(html: string) {
  const slideLikeTags = html.match(/<(?:section|article|div)\b[^>]*class=["'][^"']*["'][^>]*>/gi) || []
  return slideLikeTags.filter(tag => {
    const className = tag.match(/\bclass=["']([^"']+)["']/i)?.[1] || ''
    return className.split(/\s+/).includes('slide')
  }).length
}

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function buildFullscreenPptSlideDocument(slide: HtmlPPTSlide | undefined, index: number, total: number) {
  const title = escapeHtml(slide?.title || `第 ${index + 1} 页`)
  const subtitle = escapeHtml(slide?.subtitle || '')
  const accent = escapeHtml(slide?.accent || 'HTML PPT')
  const note = escapeHtml(slide?.speaker_note || '')
  const bullets = Array.isArray(slide?.bullets) ? slide.bullets.filter(Boolean).slice(0, 8) : []
  const bulletMarkup = bullets.map((item, bulletIndex) => `
    <li>
      <span>${bulletIndex + 1}</span>
      <p>${escapeHtml(item)}</p>
    </li>
  `).join('')
  const bulletClass = bullets.length > 5 ? 'compact' : ''
  return `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box-sizing: border-box; }
    html, body {
      width: 100%;
      height: 100%;
      margin: 0;
      overflow: hidden;
      font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
      color: #203348;
      background: #101820;
    }
    body {
      display: grid;
      place-items: center;
    }
    .slide {
      position: relative;
      display: grid;
      grid-template-rows: auto 1fr auto;
      gap: min(2.2vh, 20px);
      width: 100%;
      height: 100%;
      padding: min(5vh, 52px) min(5vw, 70px);
      overflow: hidden;
      background:
        linear-gradient(90deg, rgba(15,118,110,.08) 1px, transparent 1px),
        linear-gradient(0deg, rgba(15,118,110,.08) 1px, transparent 1px),
        #fbf8ef;
      background-size: 32px 32px;
    }
    .slide::after {
      content: "";
      position: absolute;
      right: -72px;
      bottom: -84px;
      width: 240px;
      height: 240px;
      border: 34px solid rgba(15,118,110,.11);
      transform: rotate(18deg);
      pointer-events: none;
    }
    header {
      position: relative;
      z-index: 1;
      display: grid;
      gap: 10px;
      max-width: 86%;
    }
    .kicker {
      margin: 0;
      color: #0f766e;
      font-size: clamp(13px, 1.25vw, 17px);
      font-weight: 900;
      letter-spacing: .06em;
    }
    h1 {
      margin: 0;
      color: #203348;
      font-size: clamp(30px, 4.4vw, 56px);
      line-height: 1.08;
      letter-spacing: 0;
    }
    .subtitle {
      margin: 0;
      color: #657384;
      font-size: clamp(17px, 1.75vw, 24px);
      line-height: 1.35;
    }
    .content {
      position: relative;
      z-index: 1;
      display: grid;
      align-content: center;
      min-height: 0;
    }
    ul {
      display: grid;
      grid-template-columns: 1fr;
      gap: clamp(10px, 1.45vh, 16px);
      max-width: 86%;
      margin: 0;
      padding: 0;
      list-style: none;
    }
    ul.compact {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      max-width: 94%;
      gap: clamp(8px, 1.2vh, 13px) 18px;
    }
    li {
      display: grid;
      grid-template-columns: auto 1fr;
      gap: 14px;
      align-items: start;
      min-width: 0;
    }
    li span {
      display: grid;
      place-items: center;
      width: clamp(28px, 3vw, 40px);
      height: clamp(28px, 3vw, 40px);
      border-radius: 999px;
      background: #f18518;
      color: #ffffff;
      font-weight: 900;
      font-size: clamp(15px, 1.55vw, 21px);
    }
    li p {
      min-width: 0;
      margin: 0;
      color: #203348;
      font-size: clamp(18px, 2.05vw, 27px);
      line-height: 1.36;
      overflow-wrap: anywhere;
    }
    ul.compact li p {
      font-size: clamp(15px, 1.55vw, 21px);
      line-height: 1.32;
    }
    footer {
      position: relative;
      z-index: 1;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 18px;
      align-items: end;
      min-height: 0;
      color: #7a8795;
      font-size: clamp(13px, 1.2vw, 17px);
      line-height: 1.35;
    }
    .note {
      margin: 0;
      max-width: 78%;
      overflow-wrap: anywhere;
    }
    .page {
      font-weight: 900;
      color: rgba(32, 51, 72, .45);
    }
  </style>
</head>
<body>
  <main class="slide">
    <header>
      <p class="kicker">${accent}</p>
      <h1>${title}</h1>
      ${subtitle ? `<p class="subtitle">${subtitle}</p>` : ''}
    </header>
    <section class="content">
      <ul class="${bulletClass}">${bulletMarkup || '<li><span>1</span><p>暂无要点</p></li>'}</ul>
    </section>
    <footer>
      <p class="note">${note}</p>
      <span class="page">${index + 1} / ${total}</span>
    </footer>
  </main>
</body>
</html>`
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
  if (props.resource.review_status === 'needs_revision') return '已复核'
  return '不可用'
})
const reviewStatusClass = computed(() => {
  if (!props.resource) return ''
  return props.resource.review_status === 'needs_revision' ? 'passed' : props.resource.review_status
})

const friendlyAudit = computed(() => {
  if (!props.resource) return ''
  if (props.resource.review_status === 'passed') return '这份内容已经通过系统检查。'
  if (props.resource.review_status === 'needs_revision') return '这份内容已完成课程相关性与来源检查，可用于当前学习。'
  return '这份内容暂不建议使用。'
})
const displayedReviewNotes = computed(() => {
  const notes = props.resource?.review_notes || []
  if (props.resource?.review_status !== 'needs_revision') return notes.slice(0, 2)
  const positiveNotes = notes.filter(note =>
    note.includes('证据') ||
    note.includes('来源') ||
    note.includes('相关关键词') ||
    note.includes('校验')
  ).filter(note =>
    !note.includes('缺少') &&
    !note.includes('不足') &&
    !note.includes('无法') &&
    !note.includes('未找到')
  )
  return (positiveNotes.length ? positiveNotes : ['已关联课程知识库来源', '已完成学习内容检查']).slice(0, 2)
})
const simpleReviewReason = computed(() => {
  if (props.resource?.review_status === 'needs_revision') return '已完成课程相关性与来源检查'
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
  return Array.isArray(frames) ? frames.filter(frame => frame.title && frame.caption).slice(0, 4) : []
})
const animationHtmlDocument = computed(() => {
  const html = animationPayload.value?.html_document
  return typeof html === 'string' && html.trim().length > 0 ? injectAnimationPreviewCss(html, animationDisplayMode.value) : ''
})

const fullscreenAnimationDocument = computed(() => {
  const html = animationPayload.value?.html_document
  return typeof html === 'string' && html.trim().length > 0 ? injectAnimationFullscreenCss(html, animationDisplayMode.value) : ''
})

const activeFrame = computed(() => animationFrames.value[activeFrameIndex.value] || animationFrames.value[0])
const teachingModelLabels: Record<string, string> = {
  agent_loop: '感知-决策-行动',
  ai_boundary_test: '智能边界判断',
  search_pathfinding: '路径搜索',
  logic_rule_chain: '规则推理链',
  generalization_curve: '泛化曲线',
  supervised_split: '监督学习',
  cluster_space: '空间聚类',
  neural_training_loop: '神经训练循环',
  language_pipeline: '语言处理流水线',
  vision_feature_map: '视觉特征图',
  reinforcement_loop: '强化学习循环',
  prompt_context_loop: '提示词上下文',
  retrieval_tool_loop: '检索/工具增强',
  safety_case_review: '安全案例复核'
}
const legacyTemplateByTeachingModel: Record<string, string> = {
  agent_loop: 'flow',
  ai_boundary_test: 'compare',
  search_pathfinding: 'search',
  logic_rule_chain: 'flow',
  generalization_curve: 'compare',
  supervised_split: 'compare',
  cluster_space: 'network',
  neural_training_loop: 'network',
  language_pipeline: 'dialogue',
  vision_feature_map: 'network',
  reinforcement_loop: 'search',
  prompt_context_loop: 'dialogue',
  retrieval_tool_loop: 'dialogue',
  safety_case_review: 'risk'
}
const animationTeachingModel = computed(() => {
  const model = animationPayload.value?.teaching_model_id || ''
  return teachingModelLabels[model] ? model : ''
})
const isStructuredAnimation = computed(() => Boolean(animationTeachingModel.value))
const teachingModelLabel = computed(() => teachingModelLabels[animationTeachingModel.value] || '教学过程模型')
const animationTemplate = computed(() => {
  if (animationTeachingModel.value) return legacyTemplateByTeachingModel[animationTeachingModel.value] || 'flow'
  const template = animationPayload.value?.template
  const allowed = new Set(['flow', 'compare', 'network', 'search', 'dialogue', 'risk'])
  if (template && allowed.has(template)) return template
  const visual = activeFrame.value?.visual || ''
  if (visual.startsWith('network')) return 'network'
  if (visual.startsWith('search')) return 'search'
  if (visual.startsWith('dialogue')) return 'dialogue'
  if (visual.startsWith('risk')) return 'risk'
  if (visual.startsWith('compare') || ['generalization', 'overfit'].includes(visual)) return 'compare'
  return 'flow'
})
const animationDisplayMode = computed<AnimationDisplayMode>(() => {
  if (['reinforcement_loop', 'search_pathfinding'].includes(animationTeachingModel.value)) return 'maze'
  if (animationTeachingModel.value === 'retrieval_tool_loop') return 'rag'
  if (animationTemplate.value === 'search') return 'maze'
  const text = `${animationPayload.value?.topic || ''} ${animationPayload.value?.concept || ''} ${animationPayload.value?.scenario || ''}`
  if (animationTemplate.value === 'dialogue' && /rag|检索|引用|知识库|retrieval/i.test(text)) return 'rag'
  return 'default'
})
const activeSceneObjects = computed(() => {
  const objects = activeFrame.value?.scene_objects
  if (Array.isArray(objects) && objects.length >= 4) return objects.slice(0, 4)
  const defaults: Record<string, string[]> = {
    agent_loop: ['环境线索', '决策规则', '执行动作', '新状态'],
    ai_boundary_test: ['任务', '表现', '能力边界', '新场景'],
    search_pathfinding: ['起点', '代价', '启发值', '目标'],
    logic_rule_chain: ['事实', '规则', '结论', '检查'],
    generalization_curve: ['训练集', '训练损失', '验证损失', '泛化'],
    supervised_split: ['样本', '标签', '预测', '指标'],
    cluster_space: ['数据点', '距离', '簇中心', '解释'],
    neural_training_loop: ['输入信号', '权重', '误差', '更新'],
    language_pipeline: ['句子', '词向量', '上下文', '任务结果'],
    vision_feature_map: ['像素', '特征', '目标框', '增强样本'],
    reinforcement_loop: ['当前状态', '动作', '奖励', '策略'],
    prompt_context_loop: ['任务', '上下文', '回答', '改写'],
    retrieval_tool_loop: ['问题', '资料', '证据', '回答'],
    safety_case_review: ['场景', '风险信号', '影响', '护栏'],
    flow: ['输入信息', 'AI处理', '输出结果', '检查效果'],
    compare: ['情况A', '关键差异', '情况B', '如何选择'],
    network: ['输入节点', '重要连接', '权重变化', '输出节点'],
    search: ['起点', '尝试路线', '奖励反馈', '找到目标'],
    dialogue: ['用户问题', '上下文', '模型思考', '生成回答'],
    risk: ['真实案例', '风险信号', '判断选择', '安全边界']
  }
  if (animationTeachingModel.value) return defaults[animationTeachingModel.value] || defaults.flow
  return defaults[animationTemplate.value] || defaults.flow
})
const attentionTokens = computed(() => {
  if (animationTemplate.value !== 'network') return activeSceneObjects.value
  const cleaned = activeSceneObjects.value.map(item => cleanText(item)).filter(Boolean)
  if (cleaned.length >= 4) return cleaned.slice(0, 4)
  return ['这句话', '关键词', '上下文', '答案']
})
const attentionHotIndex = computed(() => Math.min(activeFrameIndex.value, attentionTokens.value.length - 1))
const storyLabels = computed(() => {
  const labels: Record<string, { source: string; machine: string; result: string }> = {
    flow: { source: '输入', machine: 'AI处理', result: '输出' },
    compare: { source: '左边情况', machine: '比较差异', result: '右边情况' },
    network: { source: '节点', machine: '连接加权', result: '结果' },
    search: { source: '起点', machine: '尝试路径', result: '目标' },
    dialogue: { source: '提问', machine: '理解上下文', result: '回答' },
    risk: { source: '案例', machine: '风险判断', result: '防护' }
  }
  return labels[animationTemplate.value] || labels.flow
})
const beginnerScenesByTemplate: Record<string, BeginnerScene[]> = {
  flow: [
    {
      eyebrow: '看输入',
      title: '先把问题交给 AI',
      explain: 'AI 小课第一步不是背定义，而是看清楚：我们给了什么信息，想解决什么问题。',
      remember: '先看输入，再看处理。',
      machine: '处理'
    },
    {
      eyebrow: '看过程',
      title: 'AI 会一步步处理信息',
      explain: '它会找线索、做匹配、算关系，最后把中间结果变成答案。',
      remember: 'AI 的结果来自处理过程。',
      machine: '分析'
    },
    {
      eyebrow: '看反馈',
      title: '结果不对，就要修正',
      explain: '如果输出不符合目标，系统需要根据反馈调整下一次的处理方式。',
      remember: '反馈让 AI 变得更准。',
      machine: '修正'
    },
    {
      eyebrow: '看迁移',
      title: '换个新例子也要能用',
      explain: '如果换一个场景也能讲通，说明你真的理解了这个知识点。',
      remember: '能迁移，才是真懂。',
      machine: '检查'
    }
  ],
  compare: [
    {
      eyebrow: '看两边',
      title: '先把两种情况摆在一起',
      explain: '很多 AI 概念不是单独记，而是通过对比看出差异。',
      remember: '对比能帮你看清边界。',
      machine: '比较'
    },
    {
      eyebrow: '找差异',
      title: '关键差别在哪里？',
      explain: '看输入、目标、结果或风险哪里不同，概念就会更清楚。',
      remember: '差异就是理解入口。',
      machine: '找不同'
    },
    {
      eyebrow: '看后果',
      title: '不同做法会带来不同结果',
      explain: 'AI 学习里很多错误，都是只看一边结果，没有看另一边。',
      remember: '要同时看结果和代价。',
      machine: '判别'
    },
    {
      eyebrow: '会选择',
      title: '最后知道什么时候用哪一种',
      explain: '学完后，你要能说出在新场景里该选哪种思路。',
      remember: '会选择，比会背定义更重要。',
      machine: '选择'
    }
  ],
  network: [
    {
      eyebrow: '看节点',
      title: '先把信息拆成小点',
      explain: '网络类知识点可以想成很多小点，每个点保存一部分信息。',
      remember: '节点负责保存局部信息。',
      machine: '节点'
    },
    {
      eyebrow: '看连接',
      title: '信息会沿着连接传递',
      explain: '点和点之间的连线决定了信息怎么流动，哪些内容会互相影响。',
      remember: '连接决定信息怎么走。',
      machine: '连接'
    },
    {
      eyebrow: '看权重',
      title: '重要的连接会更亮',
      explain: 'AI 会给更重要的信息更高权重，就像你读文章会重点看关键词。',
      remember: '权重表示重要程度。',
      machine: '加权'
    },
    {
      eyebrow: '看输出',
      title: '最后汇总成一个结果',
      explain: '多个节点的信息汇合后，模型给出判断、分类或生成结果。',
      remember: '输出来自许多连接的合力。',
      machine: '汇总'
    }
  ],
  search: [
    {
      eyebrow: '定起点',
      title: '先知道现在在哪里',
      explain: '搜索和规划类知识点，第一步是确定当前位置和目标。',
      remember: '先有起点和目标。',
      machine: '起点'
    },
    {
      eyebrow: '试路线',
      title: 'AI 会尝试不同路线',
      explain: '它不会一开始就知道最优答案，而是探索多个可能方向。',
      remember: '搜索就是试可能的路。',
      machine: '探索'
    },
    {
      eyebrow: '看反馈',
      title: '好的路线会得到奖励',
      explain: '如果一步更接近目标，就保留；如果走偏了，就减少这种选择。',
      remember: '反馈帮助选择方向。',
      machine: '奖励'
    },
    {
      eyebrow: '找路径',
      title: '最后形成可执行路线',
      explain: 'AI 把尝试过的结果整理成一条更好的路径。',
      remember: '好策略来自不断试错。',
      machine: '路径'
    }
  ],
  dialogue: [
    {
      eyebrow: '看问题',
      title: '先读懂用户在问什么',
      explain: '对话类 AI 的第一步，是把你的问题和意图弄清楚。',
      remember: '问题越清楚，回答越可靠。',
      machine: '理解'
    },
    {
      eyebrow: '补上下文',
      title: '再结合前后文',
      explain: '同一句话放在不同上下文里，意思可能完全不同。',
      remember: '上下文会改变答案。',
      machine: '上下文'
    },
    {
      eyebrow: '组织回答',
      title: '模型一步步组织语言',
      explain: '它会根据问题、上下文和已有知识生成回答。',
      remember: '生成不是复制，而是组合。',
      machine: '生成'
    },
    {
      eyebrow: '查是否合适',
      title: '最后看回答有没有跑题',
      explain: '好的回答要符合问题，也要清楚、准确、可用。',
      remember: '回答要对题，也要可靠。',
      machine: '检查'
    }
  ],
  risk: [
    {
      eyebrow: '看案例',
      title: '先看发生了什么',
      explain: '风险类知识点不能只背原则，要放到真实案例里看。',
      remember: '风险来自具体场景。',
      machine: '案例'
    },
    {
      eyebrow: '找信号',
      title: '哪些地方可能出问题？',
      explain: '偏见、隐私、错误信息和不公平，都可能是风险信号。',
      remember: '先识别风险信号。',
      machine: '识别'
    },
    {
      eyebrow: '做判断',
      title: '判断要不要继续使用',
      explain: '不是所有 AI 输出都能直接相信，要看证据和影响。',
      remember: '重要场景要谨慎判断。',
      machine: '判断'
    },
    {
      eyebrow: '加护栏',
      title: '用规则保护使用者',
      explain: '好的 AI 系统要有边界、审核和解释，不能只追求自动化。',
      remember: '安全护栏让 AI 更可信。',
      machine: '护栏'
    }
  ]
}
const beginnerScene = computed(() => {
  const scenes = beginnerScenesByTemplate[animationTemplate.value] || beginnerScenesByTemplate.flow
  return scenes[Math.min(activeFrameIndex.value, scenes.length - 1)]
})
const activeStepLabel = computed(() => cleanText(activeFrame.value?.metric || (isStructuredAnimation.value ? activeFrame.value?.title : beginnerScene.value.eyebrow)))
const activeTeachingTitle = computed(() => cleanText(isStructuredAnimation.value ? activeFrame.value?.title : beginnerScene.value.title))
const activeTeachingExplain = computed(() => cleanText(isStructuredAnimation.value ? activeFrame.value?.caption : beginnerScene.value.explain))
const activeTeachingAction = computed(() => isStructuredAnimation.value ? cleanText(activeFrame.value?.action || '') : '')
const activeTeachingMisconception = computed(() => isStructuredAnimation.value ? cleanText(activeFrame.value?.misconception || '') : '')
const activeTeachingRemember = computed(() => cleanText(isStructuredAnimation.value ? activeFrame.value?.takeaway : beginnerScene.value.remember))
const rlAgentCell = computed(() => [1, 2, 5, 8][Math.min(activeFrameIndex.value, 3)])
const pathChosenNodes = computed(() => [1, 2, 5, 8, 11, 12].slice(0, activeFrameIndex.value + 3))

function beginnerStepTitle(frame: AnimationFrame, index: number) {
  if (isStructuredAnimation.value) return cleanText(frame.metric || frame.title)
  const scenes = beginnerScenesByTemplate[animationTemplate.value] || beginnerScenesByTemplate.flow
  return scenes[index]?.eyebrow || cleanText(frame.focus)
}
const animationProgressPercent = computed(() => {
  if (!animationFrames.value.length) return 0
  return Math.min(100, Math.round((animationElapsedMs.value / animationFrameDurationMs) * 100))
})
const animationDurationLabel = computed(() => {
  const totalSeconds = animationPayload.value?.duration_seconds || Math.ceil(animationFrames.value.length * animationFrameDurationMs / 1000)
  return `${totalSeconds} 秒教学动画`
})

function stopAnimationTimer() {
  if (animationTimer) window.clearInterval(animationTimer)
  animationTimer = undefined
}

function startAnimationTimer() {
  stopAnimationTimer()
  animationTimer = window.setInterval(() => {
    animationElapsedMs.value += 100
    if (animationElapsedMs.value < animationFrameDurationMs) return
    animationElapsedMs.value = 0
    activeFrameIndex.value = (activeFrameIndex.value + 1) % animationFrames.value.length
  }, 100)
}

function toggleAnimationPlayback() {
  if (!animationFrames.value.length) return
  isAnimationPlaying.value = !isAnimationPlaying.value
}

function selectAnimationFrame(index: number) {
  activeFrameIndex.value = index
  animationElapsedMs.value = 0
}

function nextAnimationFrame() {
  if (!animationFrames.value.length) return
  selectAnimationFrame((activeFrameIndex.value + 1) % animationFrames.value.length)
}

function previousAnimationFrame() {
  if (!animationFrames.value.length) return
  selectAnimationFrame((activeFrameIndex.value - 1 + animationFrames.value.length) % animationFrames.value.length)
}

watch(() => props.resource?.id, () => {
  activeFrameIndex.value = 0
  animationElapsedMs.value = 0
  isAnimationPlaying.value = false
  fullscreenPreviewType.value = null
  fullscreenPptIndex.value = 0
})

watch(isAnimationPlaying, playing => {
  if (playing) startAnimationTimer()
  else stopAnimationTimer()
})

watch(animationFrames, frames => {
  if (!frames.length) {
    isAnimationPlaying.value = false
    activeFrameIndex.value = 0
    animationElapsedMs.value = 0
    return
  }
  if (activeFrameIndex.value >= frames.length) activeFrameIndex.value = 0
})

onMounted(() => {
  window.addEventListener('keydown', handleFullscreenKeydown)
  document.addEventListener('fullscreenchange', handleFullscreenChange)
})

onBeforeUnmount(() => {
  stopAnimationTimer()
  window.removeEventListener('keydown', handleFullscreenKeydown)
  document.removeEventListener('fullscreenchange', handleFullscreenChange)
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

const htmlPptPayload = computed<HtmlPPTPayload | null>(() => {
  if (!props.resource || props.resource.type !== 'html_ppt') return null
  try {
    return JSON.parse(props.resource.content) as HtmlPPTPayload
  } catch {
    return null
  }
})

const rawHtmlPptDocument = computed(() => {
  const html = htmlPptPayload.value?.html_document
  return typeof html === 'string' && html.trim().length > 0 ? html : ''
})

const htmlPptDocument = computed(() => {
  return rawHtmlPptDocument.value ? injectPptPreviewCss(rawHtmlPptDocument.value) : ''
})

const htmlPptSlides = computed<HtmlPPTSlide[]>(() => {
  const slides = htmlPptPayload.value?.slides
  return Array.isArray(slides) ? slides.filter(slide => slide.title).slice(0, 12) : []
})

const fullscreenPptTotal = computed(() => Math.max(
  1,
  countHtmlPptSlides(rawHtmlPptDocument.value),
  htmlPptSlides.value.length,
  slideRows.value.length
))

const fullscreenPptDocument = computed(() => {
  if (rawHtmlPptDocument.value) {
    return injectPptFullscreenCss(rawHtmlPptDocument.value, fullscreenPptIndex.value)
  }
  return buildFullscreenPptSlideDocument(
    htmlPptSlides.value[fullscreenPptIndex.value],
    fullscreenPptIndex.value,
    fullscreenPptTotal.value
  )
})

const slideRows = computed<SlideRow[]>(() => {
  if (!props.resource || props.resource.type !== 'html_ppt') return []
  return parseMarkdownTable(cleanContent.value, '页码')
    .filter(parts => parts.length >= 4)
    .map(parts => ({
      page: parts[0],
      title: parts[1],
      core: parts[2],
      speaker: parts[3]
    }))
})

const htmlPptOutlineRows = computed<SlideRow[]>(() => {
  if (htmlPptSlides.value.length) {
    return htmlPptSlides.value.map((slide, index) => ({
      page: `${index + 1}`,
      title: slide.title || `第 ${index + 1} 页`,
      core: Array.isArray(slide.bullets) ? slide.bullets.join('；') : slide.subtitle || '',
      speaker: slide.speaker_note || ''
    }))
  }
  return slideRows.value
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
