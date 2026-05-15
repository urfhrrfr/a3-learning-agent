<template>
  <section class="panel">
    <div class="panel-title">
      <h2>练习反馈</h2>
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
        <div v-if="report.strengths.length" class="chips"><span class="chip" v-for="item in report.strengths" :key="item">{{ item }}</span></div>
        <p v-else class="muted compact">本次报告暂未返回优势标签。</p>
      </div>
      <div class="report-section">
        <b>薄弱点</b>
        <div v-if="report.weak_points.length" class="chips"><span class="chip warning" v-for="item in report.weak_points" :key="item">{{ item }}</span></div>
        <p v-else class="muted compact">暂未识别到新的薄弱点，可以继续提交练习获得更明确的诊断。</p>
      </div>
      <div class="report-section">
        <b>错误模式</b>
        <div v-if="report.mistake_patterns.length" class="chips"><span class="chip" v-for="item in report.mistake_patterns" :key="item">{{ item }}</span></div>
        <p v-else class="muted compact">本次没有明显错误模式。</p>
      </div>
    </template>
    <div v-else class="empty">
      <strong>还没有反馈报告</strong>
      <span>这是因为你还没有提交练习。完成左侧题目后，这里会展示评分、掌握度变化、薄弱点和路径调整建议。</span>
      <RouterLink class="btn ghost" to="/assessment">完成一次练习</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { AssessmentReport } from '../types'
defineProps<{ report: AssessmentReport | null }>()
</script>
