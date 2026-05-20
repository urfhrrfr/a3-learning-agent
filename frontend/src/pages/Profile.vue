<template>
  <div class="page profile-center-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">我的学习档案</span>
        <h1>先看和我学习有关的事</h1>
        <p>这里展示我的学习目标、薄弱点、学习偏好和系统建议。</p>
      </div>
      <div class="profile-hero-visual-card" aria-label="学习画像生成个性化建议">
        <img class="profile-hero-visual-image" :src="profileRecommendationHero" alt="学习画像生成个性化建议的示意图" />
        <div>
          <span>系统给我的建议</span>
          <strong>{{ primaryAdvice }}</strong>
          <p>{{ adviceDetail }}</p>
        </div>
      </div>
    </section>

    <section class="student-summary-grid">
      <article class="metric-tile">
        <span>我的学习目标</span>
        <strong>{{ store.profile?.learning_goal || '未填写' }}</strong>
        <small>{{ store.profile?.course || '等待画像同步' }}</small>
      </article>
      <article class="metric-tile">
        <span>档案薄弱点</span>
        <strong>{{ weakPointCount }}</strong>
        <small>{{ weakPointText }}</small>
      </article>
      <article class="metric-tile">
        <span>本轮抽取</span>
        <strong>{{ currentExtractionCount }}</strong>
        <small>{{ currentExtractionSummary }}</small>
      </article>
      <article class="metric-tile">
        <span>学习偏好</span>
        <strong>{{ preferenceText }}</strong>
        <small>{{ store.profile?.time_budget || '时间安排未记录' }}</small>
      </article>
    </section>

    <div class="grid profile-center-grid">
      <ChatPanel class="span-12" featured :loading="loading" @send="send" />

      <div class="profile-advice-pair span-12">
        <section class="panel profile-facts-card">
          <div class="panel-title">
            <div>
              <h2>我现在适合怎么学</h2>
              <p class="muted compact">根据你已经告诉我的目标、薄弱点和学习偏好，整理出当前最适合的学习建议。</p>
            </div>
          </div>
          <div v-if="store.profile" class="profile-fact-list">
            <div><span>学习目标</span><strong>{{ store.profile.learning_goal || '未填写' }}</strong></div>
            <div><span>薄弱点</span><strong>{{ weakPointText }}</strong></div>
            <div><span>喜欢的材料</span><strong>{{ preferenceText }}</strong></div>
            <div><span>建议</span><strong>{{ adviceDetail }}</strong></div>
          </div>
          <div v-else class="empty small-empty">
            <strong>画像尚未同步</strong>
            <span>可以先通过对话补充学习目标和薄弱点。</span>
          </div>
        </section>

        <WeakPointCloud :profile="store.profile" :report="currentReport" :path="currentPath" />
      </div>

      <ProfileRadar
        class="span-12"
        :profile="store.profile"
        :latest-confidence="latestConfidence"
        :change-logs="changeLogs"
      />

      <section class="panel span-6 profile-extraction-card">
        <div class="panel-title">
          <div>
            <h2>本轮抽取结果</h2>
            <p class="muted compact">只展示刚刚这句话带来的字段变化，不混入历史评估。</p>
          </div>
          <span class="status" :class="{ running: loading }">{{ loading ? '抽取中' : currentExtractionCount ? '已更新' : '等待输入' }}</span>
        </div>
        <div v-if="currentFieldItems.length" class="profile-fact-list">
          <div v-for="item in currentFieldItems" :key="item.key">
            <span>{{ item.label }}</span>
            <strong>{{ item.after }}</strong>
            <small class="muted">之前：{{ item.before }}</small>
          </div>
        </div>
        <div v-else class="empty small-empty">
          <strong>还没有本轮抽取</strong>
          <span>发送一句新的学习描述后，这里会单独显示本次识别到的目标、偏好、薄弱点或时间安排。</span>
        </div>
      </section>

      <section class="panel span-6 profile-history-card">
        <div class="panel-title">
          <div>
            <h2>历史学习档案</h2>
            <p class="muted compact">这些内容来自之前的练习、资源或路径记录，不代表本句话新抽取。</p>
          </div>
          <span class="status">{{ historicalReport ? '有历史评估' : '无历史评估' }}</span>
        </div>
        <div v-if="historicalReport" class="profile-fact-list">
          <div>
            <span>历史评估薄弱点</span>
            <strong>{{ historicalReport.weak_points.length ? historicalReport.weak_points.slice(0, 4).join('、') : '暂未发现新的薄弱点' }}</strong>
          </div>
          <div>
            <span>历史得分</span>
            <strong>{{ historicalReport.score }} 分</strong>
            <small class="muted">{{ historicalReport.created_at }}</small>
          </div>
        </div>
        <div v-else class="empty small-empty">
          <strong>暂无需要区分的历史评估</strong>
          <span>完成练习后，历史评估会放在这里，避免和本轮画像抽取混在一起。</span>
        </div>
      </section>

      <details class="system-details span-12">
        <summary>查看更新记录</summary>
        <section class="panel">
          <div class="panel-title">
            <div>
              <h2>最近学习档案更新</h2>
              <p class="muted compact">只展示学生能理解的更新时间、更新原因和变化内容。</p>
            </div>
            <span class="status" :class="{ running: metaLoading, failed: Boolean(metaError) }">
              {{ metaLoading ? '加载中' : metaError ? '加载受限' : `${changeLogs.length} 条` }}
            </span>
          </div>
          <div v-if="metaError" class="empty error-state">
            <strong>更新记录暂时不可用</strong>
            <span>{{ metaError }}</span>
            <button class="btn secondary" type="button" @click="loadProfileMeta">重试加载</button>
          </div>
          <div v-else-if="changeLogs.length" class="simple-update-list">
            <article v-for="log in changeLogs.slice(0, 5)" :key="`${log.version}-${log.updated_at}`" class="simple-update-card">
              <span>第 {{ log.version }} 次更新</span>
              <strong>{{ log.fusion_reason || '根据最近对话更新学习档案' }}</strong>
              <p>{{ log.trigger_message || '系统根据学习过程记录了新的信息。' }}</p>
              <div class="chips" v-if="changedFieldLabels(log).length">
                <span v-for="field in changedFieldLabels(log)" :key="field" class="chip">{{ field }}</span>
              </div>
              <small>{{ log.updated_at }}</small>
            </article>
          </div>
          <div v-else-if="!metaLoading" class="empty small-empty">
            <strong>暂无更新记录</strong>
            <span>补充学习目标或完成练习后，这里会显示学习档案的更新。</span>
          </div>
        </section>
      </details>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '../api'
import profileRecommendationHero from '../assets/profile-recommendation-hero.png'
import ChatPanel from '../components/ChatPanel.vue'
import ProfileRadar from '../components/ProfileRadar.vue'
import WeakPointCloud from '../components/WeakPointCloud.vue'
import { friendlyErrorMessage, isDemoAssessmentReport, useLearningStore } from '../store'
import type { ProfileChangeLog } from '../types'

const store = useLearningStore()
const changeLogs = ref<ProfileChangeLog[]>([])
const metaLoading = ref(false)
const metaError = ref('')
const loading = ref(false)
const realReport = computed(() => isDemoAssessmentReport(store.report) ? null : store.report)

const fieldLabels: Record<string, string> = {
  major: '专业',
  education_level: '层次',
  course: '课程',
  current_chapter: '当前章节',
  knowledge_base: '知识基础',
  learning_goal: '学习目标',
  cognitive_style: '认知风格',
  preferred_modalities: '资源偏好',
  time_budget: '时间安排',
  weak_points: '薄弱点',
  mistake_patterns: '错误模式',
  interests: '兴趣方向',
  mastery: '掌握度'
}

const latestConfidence = computed(() => {
  const latest = changeLogs.value
    .map(log => log.fusion_meta?.confidence ?? log.extraction_confidence)
    .find(value => typeof value === 'number')
  return typeof latest === 'number' ? latest : undefined
})

const currentReport = computed(() => {
  if (!realReport.value || !store.profile?.updated_at) return null
  return Date.parse(realReport.value.created_at) >= Date.parse(store.profile.updated_at) ? realReport.value : null
})
const historicalReport = computed(() => realReport.value && realReport.value !== currentReport.value ? realReport.value : null)
const currentPath = computed(() => {
  if (!store.path || !store.profile?.updated_at) return null
  return Date.parse(store.path.updated_at) >= Date.parse(store.profile.updated_at) ? store.path : null
})
const weakPointCount = computed(() => {
  const points = new Set<string>()
  for (const point of store.profile?.weak_points || []) points.add(point)
  for (const point of currentReport.value?.weak_points || []) points.add(point)
  return points.size
})
const weakPointText = computed(() => {
  const points = [...new Set([...(store.profile?.weak_points || []), ...(currentReport.value?.weak_points || [])])]
  return points.length ? points.slice(0, 3).join('、') : '暂未识别'
})
const preferenceText = computed(() => {
  const preferences = store.profile?.preferred_modalities?.filter(Boolean) || []
  if (preferences.length) return preferences.slice(0, 3).join('、')
  return store.profile?.cognitive_style || '未记录'
})
const primaryAdvice = computed(() => {
  if (currentReport.value?.weak_points?.length) return '先补薄弱点'
  if (store.profile?.learning_goal) return '按目标学习'
  return '先补充画像'
})
const adviceDetail = computed(() => {
  if (currentReport.value?.weak_points?.length) return `优先复习 ${currentReport.value.weak_points.slice(0, 2).join('、')}，再做一次练习确认。`
  if (store.profile?.weak_points?.length) return `先从 ${store.profile.weak_points.slice(0, 2).join('、')} 开始巩固。`
  if (store.profile?.learning_goal) return '先生成一组学习资料，再按路径完成练习。'
  return '填写学习目标和当前困惑后，系统会给出更具体建议。'
})

const currentFieldItems = computed(() => {
  const changedFields = store.lastProfileUpdate?.changed_fields || {}
  return Object.entries(changedFields).map(([key, value]: [string, { before: unknown; after: unknown }]) => ({
    key,
    label: fieldLabels[key] || key,
    before: formatProfileValue(value.before),
    after: formatProfileValue(value.after)
  }))
})
const currentExtractionCount = computed(() => currentFieldItems.value.length)
const currentExtractionSummary = computed(() => {
  if (!currentFieldItems.value.length) return '等待新的输入'
  return currentFieldItems.value.map(item => item.label).slice(0, 3).join('、')
})

async function loadProfileMeta() {
  metaLoading.value = true
  metaError.value = ''
  try {
    changeLogs.value = await api.profileChangeLog()
  } catch (error) {
    metaError.value = friendlyErrorMessage(error, '学习档案更新记录加载失败')
  } finally {
    metaLoading.value = false
  }
}

onMounted(async () => {
  await store.ensureReady()
  await loadProfileMeta()
})

async function send(message: string) {
  loading.value = true
  try {
    await store.sendProfileMessage(message)
    await loadProfileMeta()
  } finally {
    loading.value = false
  }
}

function changedFieldLabels(log: ProfileChangeLog) {
  return Object.keys(log.changed_fields || {})
    .map(key => fieldLabels[key] || key)
    .slice(0, 5)
}

function formatProfileValue(value: unknown) {
  if (Array.isArray(value)) return value.length ? value.join('、') : '空'
  if (value === null || value === undefined || value === '') return '空'
  if (typeof value === 'number') return Number.isInteger(value) ? String(value) : value.toFixed(2)
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
</script>
