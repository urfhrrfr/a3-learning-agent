<template>
  <section class="panel weak-cloud-card">
    <div class="panel-title">
      <div>
        <h2>当前档案薄弱点</h2>
        <p class="muted compact">只展示当前画像和本轮之后的评估信息，历史评估会在画像页单独说明。</p>
      </div>
      <span class="status">{{ items.length }} 个</span>
    </div>

    <div v-if="items.length" class="weak-cloud">
      <span
        v-for="item in items"
        :key="item.label"
        class="weak-tag"
        :class="item.source"
        :style="{ '--weight': String(item.weight) }"
      >
        {{ item.label }}
        <small>{{ sourceLabel(item.source) }}</small>
      </span>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂未识别薄弱知识点</strong>
      <span>输入学习困惑或完成一次练习评估后，系统将自动识别薄弱知识点。</span>
      <RouterLink class="btn ghost" to="/assessment">去做练习</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AssessmentReport, LearningPath, Profile } from '../types'

const props = defineProps<{
  profile: Profile | null
  report: AssessmentReport | null
  path: LearningPath | null
}>()

type Source = 'profile' | 'report' | 'path'

const items = computed(() => {
  const map = new Map<string, { label: string; source: Source; weight: number }>()
  for (const point of props.profile?.weak_points || []) {
    add(point, 'profile', 2)
  }
  for (const point of props.report?.weak_points || []) {
    add(point, 'report', 3)
  }
  const reason = props.path?.adjustment_reason || ''
  for (const point of props.profile?.weak_points || []) {
    if (point && reason.includes(point)) add(point, 'path', 3)
  }
  return [...map.values()].sort((a, b) => b.weight - a.weight)

  function add(label: string, source: Source, weight: number) {
    const normalized = label.trim()
    if (!normalized) return
    const existing = map.get(normalized)
    if (!existing || weight > existing.weight) {
      map.set(normalized, { label: normalized, source, weight })
    }
  }
})

function sourceLabel(source: Source) {
  if (source === 'report') return '评估'
  if (source === 'path') return '路径'
  return '画像'
}
</script>
