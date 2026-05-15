<template>
  <section class="panel path-adjustment-panel">
    <div class="panel-title">
      <div>
        <h2>路径调整依据</h2>
        <p class="muted compact">说明评估结果如何影响后续学习路径。</p>
      </div>
      <span class="status" :class="{ completed: Boolean(report), pending: !report }">{{ report ? '已评估' : '待评估' }}</span>
    </div>

    <template v-if="report || path">
      <div class="mastery-change">
        <div>
          <span>当前掌握度</span>
          <strong>{{ path ? `${Math.round(path.mastery * 100)}%` : '-' }}</strong>
        </div>
        <div>
          <span>评估变化</span>
          <strong>{{ report ? formatDelta(report.mastery_delta) : '暂无' }}</strong>
        </div>
      </div>
      <div class="mastery-bar" aria-label="掌握度变化">
        <span :style="{ width: `${masteryPercent}%` }"></span>
      </div>

      <div class="adjustment-section">
        <b>路径调整原因</b>
        <p>{{ path?.adjustment_reason || '当前路径暂未返回调整原因。' }}</p>
      </div>

      <div v-if="report" class="adjustment-section">
        <b>评估反馈</b>
        <p>{{ report.feedback }}</p>
        <div class="chips" v-if="report.weak_points.length">
          <span class="chip warning" v-for="point in report.weak_points" :key="point">{{ point }}</span>
        </div>
      </div>
    </template>

    <div v-else class="empty small-empty">
      <strong>暂无路径调整建议</strong>
      <span>完成练习评估后生成路径调整建议。</span>
      <RouterLink class="btn ghost" to="/assessment">去做练习</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessmentReport, LearningPath } from '../types'

const props = defineProps<{
  report: AssessmentReport | null
  path: LearningPath | null
}>()

const masteryPercent = computed(() => props.path ? Math.round(props.path.mastery * 100) : 0)

function formatDelta(value: number) {
  const percent = Math.round(value * 100)
  return `${percent >= 0 ? '+' : ''}${percent}%`
}
</script>
