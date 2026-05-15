<template>
  <div class="page assessment-center-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">学习结果</span>
        <h1>先看结论，再决定怎么补</h1>
        <p>先看得分、主要薄弱点和下一步补救任务，详细分析放在下方。</p>
      </div>
      <div class="today-focus-card">
        <span>本次得分</span>
        <strong>{{ store.report ? `${store.report.score} 分` : '待提交' }}</strong>
        <p>{{ store.report ? scoreConclusion : '完成练习后生成报告' }}</p>
      </div>
    </section>

    <section class="student-summary-grid">
      <article class="metric-tile">
        <span>本次得分</span>
        <strong>{{ store.report ? store.report.score : '-' }}</strong>
        <small>{{ store.report ? scoreConclusion : '提交练习后生成' }}</small>
      </article>
      <article class="metric-tile">
        <span>你主要错在哪</span>
        <strong>{{ mainWeakPoint }}</strong>
        <small>{{ store.report?.mistake_patterns[0] || '暂无详细错误模式' }}</small>
      </article>
      <article class="metric-tile">
        <span>下一步怎么补</span>
        <strong>{{ nextRepairTask }}</strong>
        <small>{{ store.path?.steps[0]?.estimated_minutes ? `预计 ${store.path.steps[0].estimated_minutes} 分钟` : '完成评估后会推荐' }}</small>
      </article>
      <article class="metric-tile">
        <span>推荐学习任务</span>
        <strong>{{ recommendedTask }}</strong>
        <small>{{ store.path?.adjustment_reason || '根据练习结果调整' }}</small>
      </article>
    </section>

    <div v-if="store.error && !store.report" class="empty error-state">
      <strong>练习数据暂时不可用</strong>
      <span>{{ store.error }}</span>
      <div class="resource-actions">
        <button class="btn secondary" type="button" @click="store.refresh">重新同步</button>
        <RouterLink class="btn ghost" to="/generate">先生成题库</RouterLink>
      </div>
    </div>

    <div class="grid assessment-center-grid">
      <QuizPlayer
        class="span-5 assessment-quiz-panel"
        :submitting="store.assessing"
        :refreshing="store.refreshingQuiz"
        :questions="quizQuestions"
        @submit="store.submitAssessment"
        @refresh="store.refreshQuiz"
      />

      <section class="panel span-7 assessment-feedback-panel">
        <div class="panel-title">
          <div>
            <h2>评估结论</h2>
            <p class="muted compact">先看哪里需要补，再按推荐任务继续学。</p>
          </div>
          <span v-if="store.report" class="status completed">已生成</span>
        </div>
        <template v-if="store.report">
          <p class="assessment-feedback-text">{{ store.report.feedback }}</p>
          <div class="report-section">
            <b>薄弱点</b>
            <div v-if="store.report.weak_points.length" class="chips">
              <span class="chip warning" v-for="item in store.report.weak_points" :key="item">{{ item }}</span>
            </div>
            <p v-else class="muted compact">本次报告未返回结构化薄弱点。</p>
          </div>
          <div class="report-section">
            <b>下一步怎么补</b>
            <p class="muted compact">{{ nextRepairDetail }}</p>
          </div>
        </template>
        <div v-else class="empty">
          <strong>还没有反馈报告</strong>
          <span>完成左侧练习后，这里会展示评分、薄弱点、错误模式和路径调整建议。</span>
        </div>
      </section>

      <details class="system-details span-12">
        <summary>查看详细分析</summary>
        <section class="panel user-explain-panel">
          <div class="explain-grid">
            <article>
              <span>错误原因</span>
              <strong>{{ errorReasonText }}</strong>
            </article>
            <article>
              <span>掌握度变化</span>
              <strong>{{ masteryDeltaText }}</strong>
            </article>
            <article>
              <span>下一步建议</span>
              <strong>{{ nextRepairDetail }}</strong>
            </article>
          </div>
        </section>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import QuizPlayer from '../components/QuizPlayer.vue'
import type { QuizQuestion } from '../components/QuizPlayer.vue'
import { useLearningStore } from '../store'

const store = useLearningStore()
const quizQuestions = computed<QuizQuestion[]>(() => {
  const quizResource = store.resources.find(resource => resource.type === 'quiz')
  if (!quizResource) return []
  try {
    const parsed = JSON.parse(quizResource.content)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})

const profileUpdateHint = computed(() => {
  if (!store.report) return '提交练习后，系统会根据评估结果更新画像或路径。'
  const weakPoints = store.report.weak_points.length ? `识别到薄弱点：${store.report.weak_points.join('、')}` : '本次未返回新的结构化薄弱点'
  return `${weakPoints}；当前画像掌握度为 ${store.profile ? Math.round(store.profile.mastery * 100) : '-'}%。`
})
const scoreConclusion = computed(() => {
  if (!store.report) return ''
  if (store.report.score >= 85) return '整体掌握较好，继续做迁移练习'
  if (store.report.score >= 60) return '基础可继续巩固，优先补薄弱点'
  return '建议先回到讲解材料，再做基础练习'
})
const mainWeakPoint = computed(() => store.report?.weak_points[0] || '暂无')
const nextRepairTask = computed(() => store.path?.steps[0]?.title || '先完成一组练习')
const recommendedTask = computed(() => store.path?.steps[0]?.objective || '等待路径推荐')
const nextRepairDetail = computed(() => {
  if (store.path?.steps[0]) return `${store.path.steps[0].title}：${store.path.steps[0].objective}`
  return profileUpdateHint.value
})
const errorReasonText = computed(() => {
  if (store.report?.mistake_patterns?.length) return store.report.mistake_patterns.slice(0, 2).join('、')
  if (store.report?.weak_points?.length) return `主要需要加强：${store.report.weak_points.slice(0, 2).join('、')}`
  return '完成练习后会显示'
})
const masteryDeltaText = computed(() => {
  if (!store.report) return '完成练习后会显示'
  const percent = Math.round(store.report.mastery_delta * 100)
  return `${percent >= 0 ? '+' : ''}${percent}%`
})

onMounted(store.ensureReady)
</script>
