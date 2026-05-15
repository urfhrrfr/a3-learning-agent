<template>
  <section class="assessment-summary-grid">
    <article class="metric-tile">
      <span>本次得分</span>
      <strong>{{ report ? report.score : '-' }}</strong>
      <small>{{ report ? '来自练习评估报告' : '提交练习后生成' }}</small>
    </article>
    <article class="metric-tile">
      <span>掌握度变化</span>
      <strong>{{ report ? formatDelta(report.mastery_delta) : '-' }}</strong>
      <small>{{ profile ? `当前画像掌握度 ${Math.round(profile.mastery * 100)}%` : '等待画像同步' }}</small>
    </article>
    <article class="metric-tile">
      <span>薄弱点数量</span>
      <strong>{{ report?.weak_points.length || 0 }}</strong>
      <small>{{ report?.weak_points.length ? '已识别待巩固点' : '暂无结构化薄弱点' }}</small>
    </article>
    <article class="metric-tile">
      <span>路径调整</span>
      <strong>{{ path?.steps.length ? '已触发' : '待生成' }}</strong>
      <small>{{ path?.adjustment_reason || '完成评估后更新路径建议' }}</small>
    </article>
  </section>
</template>

<script setup lang="ts">
import type { AssessmentReport, LearningPath, Profile } from '../types'

defineProps<{
  report: AssessmentReport | null
  path: LearningPath | null
  profile: Profile | null
}>()

function formatDelta(value: number) {
  const percent = Math.round(value * 100)
  return `${percent >= 0 ? '+' : ''}${percent}%`
}
</script>
