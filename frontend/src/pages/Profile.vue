<template>
  <div class="page profile-center-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">我的学习档案</span>
        <h1>先看和我学习有关的事</h1>
        <p>本轮识别结果、长期画像和历史记录分开展示，当前推荐优先看本轮输入。</p>
        <div class="hero-summary-strip" aria-label="学习档案摘要">
          <span>
            <small>学习目标</small>
            <strong>{{ activeTurnProfile?.learning_goal || store.profile?.learning_goal || '未填写' }}</strong>
          </span>
          <span>
            <small>薄弱点</small>
            <strong>{{ turnWeakPointText }}</strong>
          </span>
          <span>
            <small>学习偏好</small>
            <strong>{{ turnPreferenceText }}</strong>
          </span>
        </div>
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
        <span>本轮学习目标</span>
        <strong>{{ activeTurnProfile?.learning_goal || '等待输入' }}</strong>
        <small>{{ activeTurnProfile?.course || store.profile?.course || '等待画像同步' }}</small>
      </article>
      <article class="metric-tile">
        <span>本轮困惑</span>
        <strong>{{ turnWeakPointCount }}</strong>
        <small>{{ turnWeakPointText }}</small>
      </article>
      <article class="metric-tile">
        <span>长期画像</span>
        <strong>{{ longTermWeakPointCount }}</strong>
        <small>{{ longTermWeakPointText }}</small>
      </article>
      <article class="metric-tile">
        <span>学习偏好</span>
        <strong>{{ turnPreferenceText }}</strong>
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
          <div v-if="activeTurnProfile || store.profile" class="profile-fact-list">
            <div><span>本轮目标</span><strong>{{ activeTurnProfile?.learning_goal || store.profile?.learning_goal || '未填写' }}</strong></div>
            <div><span>本轮困惑</span><strong>{{ turnWeakPointText }}</strong></div>
            <div><span>本轮偏好</span><strong>{{ turnPreferenceText }}</strong></div>
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
            <h2>本轮识别结果</h2>
            <p class="muted compact">只展示刚刚这句话抽取出的目标、困惑和偏好，不混入历史画像。</p>
          </div>
          <span class="status" :class="{ running: loading }">{{ loading ? '抽取中' : currentExtractionCount ? '已更新' : '等待输入' }}</span>
        </div>
        <div v-if="activeTurnProfile" class="profile-fact-list">
          <div><span>本轮目标</span><strong>{{ activeTurnProfile.learning_goal || '未识别' }}</strong></div>
          <div><span>本轮困惑</span><strong>{{ turnWeakPointText }}</strong></div>
          <div><span>本轮偏好</span><strong>{{ turnPreferenceText }}</strong></div>
          <div><span>不稳定信息</span><strong>{{ turnUnstableText }}</strong></div>
        </div>
        <div v-else class="empty small-empty">
          <strong>还没有本轮抽取</strong>
          <span>发送一句新的学习描述后，这里会单独显示本次识别到的目标、偏好、薄弱点或时间安排。</span>
        </div>
      </section>

      <section class="panel span-6 profile-history-card">
        <div class="panel-title">
          <div>
            <h2>长期画像与历史</h2>
            <p class="muted compact">长期画像只保留稳定偏好和已确认信息，历史记录用于回溯，不覆盖本轮。</p>
          </div>
          <div class="profile-panel-actions">
            <span class="status">{{ historicalReport ? '有历史评估' : '无历史评估' }}</span>
            <button class="btn danger compact-action" type="button" :disabled="profileDeleting || (!store.profile && !activeTurnProfile && !changeLogs.length)" @click="clearProfile">
              {{ profileDeleting ? '清空中' : '清空档案' }}
            </button>
          </div>
        </div>
        <div v-if="profileDeleteError" class="empty error-state profile-inline-error">
          <strong>学习档案清空失败</strong>
          <span>{{ profileDeleteError }}</span>
        </div>
        <div v-if="store.profile" class="profile-fact-list">
          <div>
            <span>长期目标</span>
            <strong>{{ store.profile.learning_goal || '未记录' }}</strong>
          </div>
          <div>
            <span>长期薄弱点</span>
            <strong>{{ longTermWeakPointText }}</strong>
            <small class="muted">不会直接覆盖本轮困惑</small>
          </div>
          <div>
            <span>稳定偏好</span>
            <strong>{{ longTermPreferenceText }}</strong>
          </div>
          <div>
            <span>最近历史</span>
            <strong>{{ latestHistoryText }}</strong>
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
const profileDeleting = ref(false)
const profileDeleteError = ref('')
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
const activeTurnProfile = computed(() => store.turnProfile || latestTurnFromHistory.value)
const latestTurnFromHistory = computed(() => {
  return changeLogs.value.find(log => log.turn_profile)?.turn_profile || null
})
const turnWeakPointText = computed(() => {
  const points = activeTurnProfile.value?.weak_points?.filter(Boolean) || []
  return points.length ? points.slice(0, 6).join('、') : '等待本轮输入'
})
const turnWeakPointCount = computed(() => activeTurnProfile.value?.weak_points?.filter(Boolean).length || 0)
const turnPreferenceText = computed(() => {
  const preferences = activeTurnProfile.value?.preferred_modalities?.filter(Boolean) || []
  if (preferences.length) return preferences.slice(0, 3).join('、')
  return activeTurnProfile.value?.cognitive_style || longTermPreferenceText.value
})
const longTermWeakPointCount = computed(() => store.profile?.weak_points?.filter(Boolean).length || 0)
const longTermWeakPointText = computed(() => {
  const points = store.profile?.weak_points?.filter(Boolean) || []
  return points.length ? points.slice(0, 4).join('、') : '暂无已确认薄弱点'
})
const longTermPreferenceText = computed(() => {
  const preferences = store.profile?.preferred_modalities?.filter(Boolean) || []
  if (preferences.length) return preferences.slice(0, 3).join('、')
  return store.profile?.cognitive_style || '未记录'
})
const turnUnstableText = computed(() => {
  const items = activeTurnProfile.value?.knowledge_base?.filter(Boolean) || []
  return items.length ? items.slice(0, 3).join('、') : '无本轮先修基础结论'
})
const latestHistoryText = computed(() => {
  if (historicalReport.value?.weak_points?.length) return `历史评估：${historicalReport.value.weak_points.slice(0, 2).join('、')}`
  if (changeLogs.value.length) return `最近 ${changeLogs.value.length} 条更新可追溯`
  return '暂无历史记录'
})
const primaryAdvice = computed(() => {
  if (turnWeakPointCount.value) return '按本轮困惑学习'
  if (currentReport.value?.weak_points?.length) return '先补练习薄弱点'
  if (store.profile?.learning_goal) return '按长期目标学习'
  return '先补充画像'
})
const adviceDetail = computed(() => {
  if (turnWeakPointCount.value) return `先围绕 ${turnWeakPointText.value} 生成图解、步骤和代码案例。`
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
const currentExtractionCount = computed(() => {
  if (!activeTurnProfile.value) return 0
  return [
    activeTurnProfile.value.learning_goal,
    activeTurnProfile.value.weak_points?.length,
    activeTurnProfile.value.preferred_modalities?.length,
    activeTurnProfile.value.cognitive_style,
    activeTurnProfile.value.time_budget
  ].filter(Boolean).length
})
const currentExtractionSummary = computed(() => {
  if (!activeTurnProfile.value) return '等待新的输入'
  const items = []
  if (activeTurnProfile.value.learning_goal) items.push('目标')
  if (activeTurnProfile.value.weak_points?.length) items.push('困惑')
  if (activeTurnProfile.value.preferred_modalities?.length || activeTurnProfile.value.cognitive_style) items.push('偏好')
  return items.length ? items.join('、') : '本轮未识别新字段'
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

async function clearProfile() {
  if (!store.profile && !activeTurnProfile.value && !changeLogs.value.length) return
  const confirmed = window.confirm('确定清空我的学习档案吗？这会删除长期画像、本轮识别结果和画像更新记录。')
  if (!confirmed) return
  profileDeleting.value = true
  profileDeleteError.value = ''
  try {
    await store.clearProfile()
    changeLogs.value = []
    metaError.value = ''
  } catch (error) {
    profileDeleteError.value = friendlyErrorMessage(error, '学习档案清空失败')
  } finally {
    profileDeleting.value = false
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
