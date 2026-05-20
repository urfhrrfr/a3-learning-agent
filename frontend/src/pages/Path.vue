<template>
  <div class="page path-center-page">
    <section class="student-hero path-task-hero">
      <div>
        <span class="eyebrow">我的学习任务</span>
        <h1>按顺序完成三步就好</h1>
        <p>先看下一步学什么、练什么、做什么，按顺序完成即可。</p>
      </div>
      <div class="path-hero-visual-card" aria-label="三步学习任务路线">
        <img class="path-hero-visual-image" :src="learningPathHero" alt="按三步完成学习任务的路线示意图" />
        <div class="path-hero-progress">
          <div>
            <span>路径完成度</span>
            <strong>{{ completionPercent }}%</strong>
            <small>{{ completedSteps }}/{{ totalSteps }} 个阶段已完成</small>
          </div>
          <div class="home-progress" aria-label="路径完成度">
            <div :style="{ width: `${completionPercent}%` }"></div>
          </div>
        </div>
      </div>
    </section>

    <section class="student-summary-grid">
      <article class="metric-tile">
        <span>第一步学什么</span>
        <strong>{{ store.profile?.learning_goal || '未设置' }}</strong>
        <small>{{ firstStepLabel }}</small>
      </article>
      <article class="metric-tile">
        <span>第二步做什么</span>
        <strong>{{ totalSteps }}</strong>
        <small>{{ secondStepLabel }}</small>
      </article>
      <article class="metric-tile">
        <span>第三步练什么</span>
        <strong>{{ totalMinutes }}</strong>
        <small>{{ thirdStepLabel }}</small>
      </article>
      <article class="metric-tile">
        <span>为什么推荐</span>
        <strong>{{ store.path ? `${Math.round(store.path.mastery * 100)}%` : '-' }}</strong>
        <small>{{ store.path?.adjustment_reason || '根据画像、资源和练习结果安排' }}</small>
      </article>
    </section>

    <div v-if="store.error && !store.path" class="empty error-state">
      <strong>学习计划暂时无法同步</strong>
      <span>{{ store.error }}</span>
      <div class="resource-actions">
        <button class="btn secondary" type="button" @click="store.refresh">重新同步</button>
        <RouterLink class="btn ghost" to="/generate">先生成资源</RouterLink>
      </div>
    </div>

    <div v-else class="grid path-center-grid">
      <section class="panel span-12 path-stage-panel">
        <div class="panel-title">
          <div>
            <h2>本轮任务清单</h2>
            <p class="muted compact">每一步都包含预计时间和推荐原因。</p>
          </div>
          <button class="btn secondary" :disabled="store.refreshing" @click="store.refresh">
            {{ store.refreshing ? '同步中...' : '同步路径' }}
          </button>
        </div>

        <div v-if="store.path?.steps.length" class="path-stage-list">
          <LearningPathStageCard
            v-for="(step, index) in store.path.steps"
            :key="step.id"
            :step="step"
            :index="index"
            :resource-map="resourceMap"
          />
        </div>

        <div v-else class="empty">
          <strong>还没有学习路径</strong>
          <span>这是因为系统还缺少学习目标、资源或练习反馈。先生成一组材料，或完成一次练习。</span>
          <div class="resource-actions">
            <RouterLink class="btn secondary" to="/generate">生成资源</RouterLink>
            <RouterLink class="btn ghost" to="/assessment">做一次练习</RouterLink>
          </div>
        </div>
      </section>

      <details class="system-details span-12">
        <summary>系统怎么安排下一步？</summary>
        <section class="panel user-explain-panel">
          <div class="explain-grid">
            <article>
              <span>学习目标</span>
              <strong>{{ store.profile?.learning_goal || '还没有填写学习目标' }}</strong>
            </article>
            <article>
              <span>练习反馈</span>
              <strong>{{ store.report ? `最近得分 ${store.report.score}` : '完成练习后会更准确' }}</strong>
            </article>
            <article>
              <span>推荐原因</span>
              <strong>{{ store.path?.adjustment_reason || '根据当前学习资料和学习状态安排' }}</strong>
            </article>
          </div>
        </section>
      </details>

      <section class="panel span-12 history-panel">
        <div class="panel-title">
          <div>
            <h2>历史学习任务</h2>
            <p class="muted compact">本轮任务清单在上方，历史路径按生成时间归档。</p>
          </div>
          <span class="status pending">{{ historicalPaths.length }} 条历史</span>
        </div>
        <div v-if="historicalPaths.length" class="history-record-list">
          <article v-for="path in historicalPaths" :key="path.id" class="history-record">
            <div class="history-record-head">
              <div>
                <strong>{{ path.steps[0]?.title || '历史学习路径' }}</strong>
                <small>{{ formatDate(path.updated_at) }} · {{ path.steps.length }} 个任务 · 掌握度 {{ Math.round(path.mastery * 100) }}%</small>
              </div>
            </div>
            <div class="history-chip-row">
              <span v-for="step in path.steps.slice(0, 4)" :key="step.id">{{ step.title }}</span>
            </div>
          </article>
        </div>
        <div v-else class="empty small-empty">
          <strong>暂无历史任务</strong>
          <span>后续生成新任务后，旧任务会留在这里，便于区分本轮和历史。</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import learningPathHero from '../assets/learning-path-hero.png'
import LearningPathStageCard from '../components/LearningPathStageCard.vue'
import { useLearningStore } from '../store'

const store = useLearningStore()
onMounted(store.ensureReady)

const resourceMap = computed(() => Object.fromEntries(store.resources.map(resource => [resource.id, resource])))
const totalSteps = computed(() => store.path?.steps.length || 0)
const completedSteps = computed(() => store.path?.steps.filter(step => step.status === 'done').length || 0)
const completionPercent = computed(() => totalSteps.value ? Math.round((completedSteps.value / totalSteps.value) * 100) : 0)
const totalMinutes = computed(() => store.path?.steps.reduce((sum, step) => sum + step.estimated_minutes, 0) || 0)
const firstStepLabel = computed(() => store.path?.steps[0]?.title || '先生成学习资料')
const secondStepLabel = computed(() => store.path?.steps[1]?.title || '按推荐资源学习')
const thirdStepLabel = computed(() => store.path?.steps[2]?.title || '完成练习并复盘')
const historicalPaths = computed(() => store.pathHistory.filter(path => !path.is_current))

function formatDate(value?: string | null) {
  if (!value) return '时间未知'
  return new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

</script>
