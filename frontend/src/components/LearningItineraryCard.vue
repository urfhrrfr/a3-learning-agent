<template>
  <section class="itinerary-card" aria-label="学习行程单">
    <div class="itinerary-head">
      <div>
        <span class="itinerary-eyebrow">PlannerAgent 学习行程单</span>
        <h2>按你的画像编排资源路径</h2>
      </div>
      <span class="time-pill">{{ totalEstimatedTime }} 分钟 / {{ budgetLabel }}</span>
    </div>

    <div class="progress-wrap" role="img" :aria-label="`预计耗时 ${totalEstimatedTime} 分钟，总时间预算 ${budgetLabel}`">
      <div class="progress-meta">
        <span>预计耗时</span>
        <strong>{{ progressPercent }}%</strong>
      </div>
      <div class="progress-track">
        <span class="progress-fill" :style="{ width: `${progressPercent}%` }"></span>
      </div>
    </div>

    <div v-if="decisions.length" class="timeline">
      <article
        v-for="(decision, index) in decisions"
        :key="`${decision.resource_type}-${index}`"
        class="timeline-item"
      >
        <div class="timeline-marker">
          <span>{{ index + 1 }}</span>
        </div>
        <div class="timeline-content">
          <div class="resource-row">
            <div>
              <h3>{{ resourceName(decision.resource_type) }}</h3>
              <p>{{ decision.resource_type }}</p>
            </div>
            <span class="priority-chip">{{ Math.round(decision.priority * 100) }}%</span>
          </div>

          <div class="resource-meta">
            <span class="difficulty" :class="difficultyClass(decision.difficulty)">
              {{ difficultyStars(decision.difficulty) }} {{ decision.difficulty || '综合' }}
            </span>
            <span class="reason-tag">{{ reasonTag(decision.reason) }}</span>
          </div>

          <p class="reason-text">{{ decision.reason || 'PlannerAgent 将该资源纳入当前学习路径。' }}</p>
        </div>
      </article>
    </div>

    <div v-else class="empty-itinerary">
      <strong>等待 PlannerAgent 生成行程</strong>
      <span>生成资源后，这里会展示资源顺序、优先级和推荐理由。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { PlanDecision, PlanSummary } from '../types'

const props = defineProps<{
  planSummary: PlanSummary | null
  timeBudget?: string
}>()

const decisions = computed<PlanDecision[]>(() => props.planSummary?.decisions ?? [])
const totalEstimatedTime = computed(() => props.planSummary?.total_estimated_time ?? 0)
const budgetMinutes = computed(() => parseBudgetMinutes(props.timeBudget || ''))
const budgetLabel = computed(() => budgetMinutes.value ? `${budgetMinutes.value} 分钟` : '弹性预算')
const progressPercent = computed(() => {
  if (!budgetMinutes.value) return decisions.value.length ? 100 : 0
  return Math.min(100, Math.round((totalEstimatedTime.value / budgetMinutes.value) * 100))
})

const resourceLabels: Record<string, string> = {
  lecture_doc: '课程讲解文档',
  mind_map: '思维导图',
  quiz: '分层练习',
  reading: '拓展阅读',
  media_script: '视频/分镜脚本',
  animation_demo: '教学动画',
  ppt_draft: 'PPT 草稿',
  visual_card: '可视化学习卡片',
  code_case: '代码实操案例'
}

function parseBudgetMinutes(value: string): number | null {
  const match = value.match(/\d+/)
  if (!match) return null
  const amount = Number(match[0])
  if (!Number.isFinite(amount) || amount <= 0) return null
  if (value.includes('小时') || value.toLowerCase().includes('hour')) return amount * 60
  return amount
}

function resourceName(resourceType: string) {
  return resourceLabels[resourceType] || resourceType
}

function difficultyStars(difficulty: string) {
  if (difficulty.includes('提高') || difficulty.includes('应用')) return '★★★'
  if (difficulty.includes('基础')) return '★★'
  return '★'
}

function difficultyClass(difficulty: string) {
  if (difficulty.includes('提高') || difficulty.includes('应用')) return 'high'
  if (difficulty.includes('基础')) return 'medium'
  return 'low'
}

function reasonTag(reason: string) {
  if (reason.includes('薄弱') || reason.includes('混淆')) return '直击薄弱点'
  if (reason.includes('偏好') || reason.includes('图解') || reason.includes('视频')) return '匹配学习偏好'
  if (reason.includes('迁移') || reason.includes('实操')) return '强化迁移'
  if (reason.includes('考试') || reason.includes('练习')) return '巩固提分'
  return '智能推荐'
}
</script>

<style scoped>
.itinerary-card {
  display: grid;
  gap: 16px;
  overflow: hidden;
  border: 1px solid rgba(23, 108, 122, .22);
  border-radius: 8px;
  padding: 16px;
  background:
    linear-gradient(135deg, rgba(23, 108, 122, .08), rgba(123, 92, 240, .08)),
    #fff;
  box-shadow: 0 14px 34px rgba(20, 42, 65, .1);
}

.itinerary-head {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
}

.itinerary-head h2 {
  margin: 0;
  color: #17212b;
  font-size: 17px;
}

.itinerary-eyebrow {
  display: inline-flex;
  margin-bottom: 6px;
  color: #176c7a;
  font-size: 12px;
  font-weight: 800;
}

.time-pill,
.priority-chip,
.reason-tag,
.difficulty {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  border-radius: 999px;
  padding: 4px 9px;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 800;
}

.time-pill {
  color: #10535e;
  background: rgba(23, 108, 122, .12);
}

.progress-wrap {
  display: grid;
  gap: 7px;
}

.progress-meta {
  display: flex;
  justify-content: space-between;
  color: #667789;
  font-size: 12px;
}

.progress-track {
  position: relative;
  height: 9px;
  overflow: hidden;
  border-radius: 999px;
  background: #dbe5ee;
}

.progress-fill {
  position: absolute;
  inset: 0 auto 0 0;
  border-radius: inherit;
  background: linear-gradient(90deg, #176c7a, #7b5cf0);
  transition: width .28s ease;
}

.timeline {
  position: relative;
  display: grid;
  gap: 12px;
}

.timeline::before {
  content: "";
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 14px;
  width: 2px;
  background: linear-gradient(180deg, #176c7a, rgba(123, 92, 240, .35));
}

.timeline-item {
  position: relative;
  display: grid;
  grid-template-columns: 30px minmax(0, 1fr);
  gap: 12px;
}

.timeline-marker {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 2px solid #fff;
  border-radius: 999px;
  background: #176c7a;
  color: #fff;
  box-shadow: 0 0 0 3px rgba(23, 108, 122, .14);
  font-size: 12px;
  font-weight: 900;
}

.timeline-content {
  display: grid;
  gap: 10px;
  border: 1px solid rgba(199, 213, 226, .9);
  border-radius: 8px;
  padding: 12px;
  background: rgba(255, 255, 255, .9);
}

.resource-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.resource-row h3 {
  margin: 0 0 3px;
  color: #17212b;
  font-size: 15px;
}

.resource-row p,
.reason-text {
  margin: 0;
  color: #667789;
  line-height: 1.55;
}

.resource-row p {
  font-size: 12px;
}

.resource-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.priority-chip {
  color: #4632a8;
  background: rgba(123, 92, 240, .12);
}

.difficulty.low {
  color: #1f7a55;
  background: #e9f7f1;
}

.difficulty.medium {
  color: #a16207;
  background: #fff7e8;
}

.difficulty.high {
  color: #7c3aed;
  background: #f1edff;
}

.reason-tag {
  color: #10535e;
  background: #e8f6f8;
}

.empty-itinerary {
  display: grid;
  gap: 6px;
  border: 1px dashed #c7d5e2;
  border-radius: 8px;
  padding: 14px;
  color: #667789;
  background: rgba(248, 250, 252, .82);
}

.empty-itinerary strong {
  color: #17212b;
}

@media (max-width: 720px) {
  .itinerary-head,
  .resource-row {
    display: grid;
  }

  .time-pill,
  .priority-chip {
    justify-self: start;
  }
}
</style>
