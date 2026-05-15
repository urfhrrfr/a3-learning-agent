<template>
  <section class="panel mastery-chart-panel">
    <div class="panel-title">
      <div>
        <h2>掌握度变化</h2>
        <p class="muted compact">用现有画像 mastery 和评估 mastery_delta 估算前后变化。</p>
      </div>
      <span class="status">{{ report ? formatDelta(report.mastery_delta) : '待评估' }}</span>
    </div>

    <template v-if="profile || report">
      <div class="mastery-bars">
        <div class="mastery-bar-row">
          <span>评估前</span>
          <div><i :style="{ width: `${beforeMastery}%` }"></i></div>
          <strong>{{ beforeMastery }}%</strong>
        </div>
        <div class="mastery-bar-row after">
          <span>评估后</span>
          <div><i :style="{ width: `${afterMastery}%` }"></i></div>
          <strong>{{ afterMastery }}%</strong>
        </div>
      </div>
      <p class="muted compact">如果缺少完整评估前数据，则以前端可获得的当前掌握度和变化量反推展示。</p>
    </template>

    <div v-else class="empty small-empty">
      <strong>暂无掌握度数据</strong>
      <span>完成画像同步和练习评估后，这里会展示变化趋势。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessmentReport, Profile } from '../types'

const props = defineProps<{
  report: AssessmentReport | null
  profile: Profile | null
}>()

const afterMastery = computed(() => Math.round((props.profile?.mastery || 0) * 100))
const beforeMastery = computed(() => {
  if (!props.report) return afterMastery.value
  return Math.max(0, Math.min(100, afterMastery.value - Math.round(props.report.mastery_delta * 100)))
})

function formatDelta(value: number) {
  const percent = Math.round(value * 100)
  return `${percent >= 0 ? '+' : ''}${percent}%`
}
</script>
