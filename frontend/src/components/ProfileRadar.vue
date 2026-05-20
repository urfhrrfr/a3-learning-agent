<template>
  <section class="panel profile-radar-card">
    <div class="panel-title">
      <div>
        <h2>画像完整度雷达</h2>
        <p class="muted compact">基于画像字段完整度和更新可信度估算，不代表考试能力分。</p>
      </div>
      <span class="status">{{ overallScore }}%</span>
    </div>

    <div v-if="profile" class="radar-layout">
      <div class="radar-stage">
        <div class="radar-score-orb">
          <strong>{{ overallScore }}%</strong>
          <span>完整度</span>
        </div>
        <svg class="radar-svg" viewBox="0 0 240 240" role="img" aria-label="画像完整度雷达图">
          <polygon
            v-for="ring in rings"
            :key="ring"
            class="radar-ring"
            :points="polygonPoints(ring)"
          />
          <line
            v-for="axis in axes"
            :key="axis.label"
            class="radar-axis"
            :x1="center"
            :y1="center"
            :x2="axisPoint(axis.index, maxRadius).x"
            :y2="axisPoint(axis.index, maxRadius).y"
          />
          <polygon class="radar-area" :points="valuePoints" />
          <circle
            v-for="axis in axes"
            :key="`${axis.label}-dot`"
            class="radar-dot"
            :cx="axisPoint(axis.index, scoreRadius(axis.score)).x"
            :cy="axisPoint(axis.index, scoreRadius(axis.score)).y"
            r="4"
          />
        </svg>
      </div>

      <div class="radar-legend">
        <div v-for="axis in axes" :key="axis.label" class="radar-legend-row">
          <div>
            <span>{{ axis.label }}</span>
            <small>{{ axis.reason }}</small>
          </div>
          <strong>{{ axis.score }}%</strong>
          <div class="radar-meter" aria-hidden="true">
            <i :style="{ width: `${axis.score}%` }"></i>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty small-empty">
      <strong>画像尚未建立</strong>
      <span>完成一次画像对话后，这里会显示画像完整度雷达。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Profile, ProfileChangeLog } from '../types'

const props = defineProps<{
  profile: Profile | null
  latestConfidence?: number
  changeLogs?: ProfileChangeLog[]
}>()

const center = 120
const maxRadius = 82
const rings = [0.25, 0.5, 0.75, 1]

const axes = computed(() => {
  const profile = props.profile
  const confidence = typeof props.latestConfidence === 'number' ? props.latestConfidence : fallbackConfidence.value
  return [
    {
      label: '知识基础',
      score: profile ? scoreList(profile.knowledge_base, 4) : 0,
      reason: profile?.knowledge_base.length ? `${profile.knowledge_base.length} 条基础信息` : '缺少知识基础描述'
    },
    {
      label: '目标清晰度',
      score: profile ? scoreText(profile.learning_goal, 24) : 0,
      reason: profile?.learning_goal ? '已有学习目标' : '尚未填写学习目标'
    },
    {
      label: '风格匹配度',
      score: profile ? Math.round((scoreText(profile.cognitive_style, 8) + scoreList(profile.preferred_modalities, 3)) / 2) : 0,
      reason: profile?.cognitive_style ? '已有认知风格和资源偏好' : '偏好信息不足'
    },
    {
      label: '薄弱点明确度',
      score: profile ? scoreList(profile.weak_points, 4) : 0,
      reason: profile?.weak_points.length ? `${profile.weak_points.length} 个薄弱点` : '等待练习或对话识别'
    },
    {
      label: '资源偏好',
      score: profile ? scoreList(profile.preferred_modalities, 4) : 0,
      reason: profile?.preferred_modalities.length ? profile.preferred_modalities.join('、') : '未形成资源偏好'
    },
    {
      label: '节奏稳定度',
      score: profile ? Math.round((scoreText(profile.time_budget, 6) * 0.7) + (confidence * 100 * 0.3)) : 0,
      reason: profile?.time_budget ? `时间预算：${profile.time_budget}` : '缺少学习时间预算'
    }
  ].map((axis, index) => ({ ...axis, index }))
})

const fallbackConfidence = computed(() => {
  const values = (props.changeLogs || [])
    .map(log => log.fusion_meta?.confidence ?? log.extraction_confidence)
    .filter((value): value is number => typeof value === 'number')
  if (!values.length) return 0.65
  return values[0]
})

const overallScore = computed(() => {
  if (!axes.value.length) return 0
  return Math.round(axes.value.reduce((sum, axis) => sum + axis.score, 0) / axes.value.length)
})

const valuePoints = computed(() => axes.value.map(axis => {
  const point = axisPoint(axis.index, scoreRadius(axis.score))
  return `${point.x},${point.y}`
}).join(' '))

function scoreList(items: unknown[] | undefined, target: number) {
  return Math.min(100, Math.round(((items?.filter(Boolean).length || 0) / target) * 100))
}

function scoreText(value: string | undefined, targetLength: number) {
  return Math.min(100, Math.round(((value || '').trim().length / targetLength) * 100))
}

function scoreRadius(score: number) {
  return maxRadius * (Math.max(0, Math.min(100, score)) / 100)
}

function axisPoint(index: number, radius: number) {
  const angle = (-90 + index * (360 / axes.value.length)) * Math.PI / 180
  return {
    x: center + Math.cos(angle) * radius,
    y: center + Math.sin(angle) * radius
  }
}

function polygonPoints(scale: number) {
  return axes.value.map(axis => {
    const point = axisPoint(axis.index, maxRadius * scale)
    return `${point.x},${point.y}`
  }).join(' ')
}
</script>
