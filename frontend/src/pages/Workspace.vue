<template>
  <div class="page demo-home-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">今日学习中心</span>
        <h1>今天先把下一步学扎实</h1>
        <p>{{ todaySummary }}</p>
        <div class="hero-actions">
          <RouterLink class="btn hero-primary" to="/profile">先构建画像</RouterLink>
          <RouterLink class="btn ghost" to="/generate">生成资料</RouterLink>
          <RouterLink class="btn ghost" to="/tutor">问智能导师</RouterLink>
        </div>
      </div>

      <div class="resource-visual-card" aria-label="资源生成入口">
        <img class="resource-visual-image" :src="resourceGenerationHero" alt="智能体生成讲义、导图、练习和代码案例的示意图" />
        <div>
          <span>今天该学什么</span>
          <strong>{{ nextAction.title }}</strong>
          <p>{{ nextAction.description }}</p>
        </div>
      </div>
    </section>

    <div class="grid student-home-grid">
      <section class="panel span-12 home-start-panel">
        <div class="home-start-main">
          <span class="eyebrow">推荐学习任务</span>
          <h2>先完成一件最重要的事</h2>
          <p>学习会轻很多。系统会根据画像、资源和练习结果，把当前最该做的入口放在这里。</p>
          <div class="home-action-card">
            <div>
              <span>当前建议</span>
              <strong>{{ nextAction.title }}</strong>
              <small>{{ nextAction.description }}</small>
            </div>
            <RouterLink class="btn hero-primary" :to="nextAction.path">{{ nextAction.label }}</RouterLink>
          </div>
          <div class="task-hint">
            <span>当前薄弱点</span>
            <strong>{{ weakPointSummary }}</strong>
          </div>
        </div>

        <div class="home-guide-panel">
          <div class="panel-title">
            <div>
              <h2>使用导航</h2>
              <p class="muted compact">按这个顺序使用系统，先让系统认识你，再生成和练习。</p>
            </div>
          </div>
          <div class="suggestion-list">
            <RouterLink class="suggestion-item" to="/profile">
              <span>01 构建画像</span>
              <strong>先告诉系统你的基础、目标和困惑</strong>
              <small>{{ store.profile ? `已建立画像 v${store.profile.version}` : '建议先完成这一步' }}</small>
            </RouterLink>
            <RouterLink class="suggestion-item" to="/generate">
              <span>02 学习资料</span>
              <strong>生成或查看适合我的材料</strong>
              <small>{{ resourceSummary }}</small>
            </RouterLink>
            <RouterLink class="suggestion-item" to="/tutor">
              <span>03 智能导师</span>
              <strong>把没懂的问题直接问清楚</strong>
              <small>{{ store.profile?.current_chapter || '可结合当前画像回答' }}</small>
            </RouterLink>
            <RouterLink class="suggestion-item" to="/assessment">
              <span>04 练习评估</span>
              <strong>做几道题，看看哪里还不稳</strong>
              <small>{{ hasRealAssessment ? `上次得分 ${store.report?.score}` : '完成后会生成反馈' }}</small>
            </RouterLink>
          </div>
        </div>
      </section>

      <section class="panel span-12 stage-panel">
        <div class="panel-title">
          <div>
            <h2>最近生成资源</h2>
            <p class="muted compact">{{ store.resources.length ? '先展示少量可立即学习的材料。' : '生成后这里会出现学习材料。' }}</p>
          </div>
          <RouterLink class="btn ghost" to="/resources">材料库</RouterLink>
        </div>
        <div v-if="store.resources.length" class="cards quiet-card-grid">
          <ResourceCard
            v-for="resource in store.resources.slice(0, 2)"
            :key="resource.id"
            :resource="resource"
            compact
            @select="selected = $event"
            @feedback="handleFeedback"
          />
        </div>
        <div v-else class="empty">
          <strong>还没有学习资源</strong>
          <span>先描述你想学什么，系统会生成一套可学习材料。</span>
          <RouterLink class="btn secondary" to="/generate">生成学习资料</RouterLink>
        </div>
      </section>
    </div>

    <details class="system-details">
      <summary>为什么这样安排？</summary>
      <section class="panel user-explain-panel">
        <div class="explain-grid">
          <article>
            <span>学习目标</span>
            <strong>{{ store.profile?.learning_goal || '还没有填写学习目标' }}</strong>
          </article>
          <article>
            <span>薄弱点</span>
            <strong>{{ weakPointSummary }}</strong>
          </article>
          <article>
            <span>学习资料</span>
            <strong>{{ store.resources.length ? `已有 ${store.resources.length} 份资料可用` : '还没有生成学习资料' }}</strong>
          </article>
        </div>
      </section>
    </details>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import resourceGenerationHero from '../assets/resource-generation-hero.png'
import { isDemoAssessmentReport, useLearningStore } from '../store'
import type { Resource } from '../types'
import ResourceCard from '../components/ResourceCard.vue'

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const hasRealAssessment = computed(() => Boolean(store.report && !isDemoAssessmentReport(store.report)))

const loopSteps = computed(() => [
  {
    key: 'profile',
    index: '01',
    title: '学生画像',
    description: store.profile ? `已建立画像 v${store.profile.version}，当前章节：${store.profile.current_chapter}` : '采集基础、目标、偏好和薄弱点。',
    path: '/profile',
    done: Boolean(store.profile),
    label: '完善画像'
  },
  {
    key: 'resources',
    index: '02',
    title: '资源生成',
    description: store.resources.length ? `已有 ${store.resources.length} 份多格式资源。` : '由智能体生成讲解、导图、练习和案例。',
    path: '/generate',
    done: store.resources.length > 0,
    label: '生成资源'
  },
  {
    key: 'path',
    index: '03',
    title: '学习路径',
    description: store.path?.steps.length ? `已规划 ${store.path.steps.length} 个学习阶段。` : '按掌握度和资源推荐学习顺序。',
    path: '/path',
    done: Boolean(store.path?.steps?.length),
    label: '查看路径'
  },
  {
    key: 'tutor',
    index: '04',
    title: '智能辅导',
    description: '结合你的学习目标和资料回答问题。',
    path: '/tutor',
    done: false,
    label: '问导师'
  },
  {
    key: 'assessment',
    index: '05',
    title: '效果评估',
    description: hasRealAssessment.value ? `最近练习得分 ${store.report?.score}，路径已反馈调整。` : '练习后形成反馈报告并更新路径。',
    path: '/assessment',
    done: hasRealAssessment.value,
    label: '做评估'
  }
])

const completedLoopCount = computed(() => loopSteps.value.filter(step => step.done).length)
const loopPercent = computed(() => Math.round((completedLoopCount.value / loopSteps.value.length) * 100))
const nextAction = computed(() => loopSteps.value.find(step => !step.done) || {
  key: 'tutor',
  title: '继续智能辅导',
  description: '闭环已跑通，可以继续追问、练习和迭代学习路径。',
  path: '/tutor',
  done: false,
  label: '继续追问'
})
const resourceSummary = computed(() => {
  if (!store.resources.length) return '等待生成'
  return `${store.resources.length} 份资料可学习`
})
const weakPointSummary = computed(() => {
  const points = [...new Set([...(store.report?.weak_points || []), ...(store.profile?.weak_points || [])])]
  return points.length ? points.slice(0, 3).join('、') : '暂未识别薄弱点，先做一次练习会更准确'
})
const todaySummary = computed(() => {
  if (store.profile?.current_chapter) return `围绕「${store.profile.current_chapter}」，先完成推荐任务，再用练习确认掌握情况。`
  return '先建立画像或生成材料，系统会把今天最适合的学习任务放在这里。'
})

onMounted(async () => {
  await store.ensureReady()
  selected.value = store.resources[0] || null
})

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  await store.submitResourceFeedback(resource.id, action)
  selected.value = store.resources.find(item => item.id === resource.id) || selected.value
}
</script>
