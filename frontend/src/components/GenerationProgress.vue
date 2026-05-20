<template>
  <section class="generation-flow" aria-label="生成进度">
    <div class="generation-flow-summary">
      <span class="eyebrow">生成流水线</span>
      <h2>{{ headline }}</h2>
      <p>{{ helperText }}</p>
    </div>

    <div class="generation-flow-track">
      <div class="generation-flow-rail" aria-hidden="true">
        <div :style="{ width: `${safeProgress}%` }"></div>
      </div>
      <ol class="generation-steps">
        <li
          v-for="(step, index) in steps"
          :key="step.label"
          :class="{ active: index === activeIndex, done: index < activeIndex || complete }"
        >
          <span>{{ index + 1 }}</span>
          <strong>{{ step.label }}</strong>
          <small>{{ step.hint }}</small>
        </li>
      </ol>
    </div>

    <div class="generation-flow-meter">
      <span>{{ Math.round(safeProgress) }}%</span>
      <strong>{{ statusText }}</strong>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ progress: number; loading: boolean; currentStep: string; complete?: boolean }>()

const steps = [
  { label: '理解需求', hint: '读取目标与画像' },
  { label: '组织内容', hint: '生成讲解与导图' },
  { label: '补齐练习', hint: '准备题目和案例' },
  { label: '整理资源包', hint: '检查后放入结果区' }
]

const safeProgress = computed(() => {
  if (props.complete) return 100
  return Math.max(0, Math.min(100, props.progress || 0))
})

const activeIndex = computed(() => {
  if (props.complete) return steps.length - 1
  if (!props.loading) return 0
  return Math.min(steps.length - 1, Math.floor(safeProgress.value / 25))
})

const headline = computed(() => {
  if (props.loading) return '正在把需求变成学习资料'
  if (props.complete) return '资源包已生成完成'
  return '提交后会在这里展示进度'
})

const helperText = computed(() => {
  if (props.loading) return props.currentStep || '系统正在生成讲解、导图、练习和案例。'
  if (props.complete) return '可以在下方查看本轮结果，也可以调整需求后重新生成。'
  return '先填写学习需求，系统会按步骤生成并整理成资源包。'
})

const statusText = computed(() => {
  if (props.loading) return props.currentStep || '正在生成'
  if (props.complete) return '已完成'
  return '等待开始'
})
</script>
