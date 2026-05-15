<template>
  <div class="page profile-center-page">
    <section class="student-hero">
      <div>
        <span class="eyebrow">我的学习档案</span>
        <h1>先看和我学习有关的事</h1>
        <p>这里展示我的学习目标、薄弱点、学习偏好和系统建议。</p>
      </div>
      <div class="today-focus-card">
        <span>系统给我的建议</span>
        <strong>{{ primaryAdvice }}</strong>
        <p>{{ adviceDetail }}</p>
      </div>
    </section>

    <section class="student-summary-grid">
      <article class="metric-tile">
        <span>我的学习目标</span>
        <strong>{{ store.profile?.learning_goal || '未填写' }}</strong>
        <small>{{ store.profile?.course || '等待画像同步' }}</small>
      </article>
      <article class="metric-tile">
        <span>我的薄弱点</span>
        <strong>{{ weakPointCount }}</strong>
        <small>{{ weakPointText }}</small>
      </article>
      <article class="metric-tile">
        <span>学习偏好</span>
        <strong>{{ preferenceText }}</strong>
        <small>{{ store.profile?.time_budget || '时间安排未记录' }}</small>
      </article>
      <article class="metric-tile">
        <span>当前章节</span>
        <strong>{{ courseChapter }}</strong>
        <small>雷达图仅表示画像信息完整度</small>
      </article>
    </section>

    <div class="grid profile-center-grid">
      <section class="panel span-5 profile-facts-card">
        <div class="panel-title">
          <div>
            <h2>我现在适合怎么学</h2>
            <p class="muted compact">这些建议来自已有画像字段，不补写后端没有的数据。</p>
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

      <ProfileRadar
        class="span-7"
        :profile="store.profile"
        :latest-confidence="latestConfidence"
        :change-logs="changeLogs"
      />

      <WeakPointCloud class="span-7" :profile="store.profile" :report="store.report" :path="store.path" />
      <ChatPanel class="span-5" :loading="loading" @send="send" />

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
import ChatPanel from '../components/ChatPanel.vue'
import ProfileRadar from '../components/ProfileRadar.vue'
import WeakPointCloud from '../components/WeakPointCloud.vue'
import { friendlyErrorMessage, useLearningStore } from '../store'
import type { ProfileChangeLog } from '../types'

const store = useLearningStore()
const changeLogs = ref<ProfileChangeLog[]>([])
const metaLoading = ref(false)
const metaError = ref('')
const loading = ref(false)

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

const confidenceLabel = computed(() => {
  if (typeof latestConfidence.value !== 'number') return '未记录'
  return `${Math.round(latestConfidence.value * 100)}%`
})

const courseChapter = computed(() => {
  if (!store.profile) return '未同步'
  return `${store.profile.course} / ${store.profile.current_chapter}`
})

const weakPointCount = computed(() => {
  const points = new Set<string>()
  for (const point of store.profile?.weak_points || []) points.add(point)
  for (const point of store.report?.weak_points || []) points.add(point)
  return points.size
})
const weakPointText = computed(() => {
  const points = [...new Set([...(store.profile?.weak_points || []), ...(store.report?.weak_points || [])])]
  return points.length ? points.slice(0, 3).join('、') : '暂未识别'
})
const preferenceText = computed(() => {
  const preferences = store.profile?.preferred_modalities?.filter(Boolean) || []
  if (preferences.length) return preferences.slice(0, 3).join('、')
  return store.profile?.cognitive_style || '未记录'
})
const primaryAdvice = computed(() => {
  if (store.report?.weak_points?.length) return '先补薄弱点'
  if (store.profile?.learning_goal) return '按目标学习'
  return '先补充画像'
})
const adviceDetail = computed(() => {
  if (store.report?.weak_points?.length) return `优先复习 ${store.report.weak_points.slice(0, 2).join('、')}，再做一次练习确认。`
  if (store.profile?.weak_points?.length) return `先从 ${store.profile.weak_points.slice(0, 2).join('、')} 开始巩固。`
  if (store.profile?.learning_goal) return '先生成一组学习资料，再按路径完成练习。'
  return '填写学习目标和当前困惑后，系统会给出更具体建议。'
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
</script>
