<template>
  <section class="panel error-pattern-panel">
    <div class="panel-title">
      <div>
        <h2>错误模式分析</h2>
        <p class="muted compact">优先展示评估报告中的结构化错误模式。</p>
      </div>
      <span class="status">{{ patternItems.length }} 项</span>
    </div>

    <div v-if="patternItems.length" class="error-pattern-list">
      <article v-for="item in patternItems" :key="item.title" class="error-pattern-card">
        <span>{{ item.source }}</span>
        <strong>{{ item.title }}</strong>
        <p>{{ item.detail }}</p>
      </article>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂无结构化错误模式</strong>
      <span>提交练习后，如果报告返回 mistake_patterns、weak_points 或反馈文本，将在这里展示。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessmentReport } from '../types'

const props = defineProps<{ report: AssessmentReport | null }>()

const patternItems = computed(() => {
  const report = props.report
  if (!report) return []
  const items: Array<{ source: string; title: string; detail: string }> = []
  for (const pattern of report.mistake_patterns || []) {
    items.push({ source: '错误模式', title: pattern, detail: report.feedback || '报告未返回更多解释。' })
  }
  for (const point of report.weak_points || []) {
    items.push({ source: '薄弱点', title: point, detail: '该知识点在本次评估中需要继续巩固。' })
  }
  if (!items.length && report.feedback) {
    items.push({ source: '反馈文本', title: '评估反馈摘要', detail: report.feedback })
  }
  return items.slice(0, 8)
})
</script>
