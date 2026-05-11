<template>
  <section class="panel">
    <div class="panel-title">
      <h2>评估报告</h2>
      <span v-if="report" class="status">{{ report.created_at }}</span>
    </div>
    <template v-if="report">
      <div class="score-board">
        <div>
          <span>得分</span>
          <strong>{{ report.score }}</strong>
        </div>
        <div>
          <span>掌握度变化</span>
          <strong>+{{ Math.round(report.mastery_delta * 100) }}%</strong>
        </div>
      </div>
      <p>{{ report.feedback }}</p>
      <div class="report-section">
        <b>优势表现</b>
        <div class="chips"><span class="chip" v-for="item in report.strengths" :key="item">{{ item }}</span></div>
      </div>
      <div class="report-section">
        <b>薄弱点</b>
        <div class="chips"><span class="chip warning" v-for="item in report.weak_points" :key="item">{{ item }}</span></div>
      </div>
      <div class="report-section">
        <b>错误模式</b>
        <div class="chips"><span class="chip" v-for="item in report.mistake_patterns" :key="item">{{ item }}</span></div>
      </div>
    </template>
    <div v-else class="empty">提交练习后展示评分、掌握度变化、薄弱点和路径调整建议。</div>
  </section>
</template>

<script setup lang="ts">
import type { AssessmentReport } from '../types'
defineProps<{ report: AssessmentReport | null }>()
</script>
