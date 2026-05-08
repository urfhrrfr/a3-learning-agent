<template>
  <section class="panel">
    <h2>评估报告</h2>
    <div v-if="report" class="timeline">
      <div><b>得分：</b>{{ report.score }}</div>
      <div><b>掌握度变化：</b>+{{ Math.round(report.mastery_delta * 100) }}%</div>
      <p>{{ report.feedback }}</p>
      <div class="chips"><span class="chip" v-for="item in report.strengths" :key="item">{{ item }}</span></div>
      <div class="chips"><span class="chip" v-for="item in report.weak_points" :key="item">{{ item }}</span></div>
    </div>
    <p v-else class="muted">提交练习后展示评分、弱点和路径调整。</p>
  </section>
</template>

<script setup lang="ts">
import type { AssessmentReport } from '../types'
defineProps<{ report: AssessmentReport | null }>()
</script>
