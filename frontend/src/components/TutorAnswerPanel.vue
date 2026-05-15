<template>
  <section class="panel tutor-answer-panel">
    <div class="panel-title">
      <div>
        <h2>导师回答</h2>
        <p class="muted compact">{{ answer ? '回答正文、下一步建议和小练习都在这里汇总。' : '发送问题后展示个性化辅导结果。' }}</p>
      </div>
      <span class="status" :class="{ running: loading }">{{ loading ? '生成中' : answer ? '已回答' : '等待提问' }}</span>
    </div>

    <template v-if="answer">
      <div class="answer-body">
        <MarkdownRenderer :content="answer" />
      </div>

      <div v-if="keyPoints.length" class="answer-keypoints">
        <b>重点解释</b>
        <div class="chips">
          <span v-for="point in keyPoints" :key="point" class="chip">{{ point }}</span>
        </div>
      </div>

      <article v-if="nextStep" class="next-step-card">
        <span>下一步建议</span>
        <strong>{{ nextStep.title }}</strong>
        <p>{{ nextStep.objective }}</p>
        <small>{{ nextStep.estimated_minutes }} 分钟 · {{ nextStep.reason }}</small>
      </article>

      <article v-if="exercise" class="inline-exercise-card">
        <div class="panel-title">
          <div>
            <h3>针对当前困惑的小练习</h3>
            <p class="muted compact">{{ exercise.hint }}</p>
          </div>
        </div>
        <p>{{ exercise.prompt }}</p>
        <textarea
          :value="exerciseAnswer"
          rows="4"
          placeholder="写下你的理解，导师会即时评估"
          @input="$emit('update:exerciseAnswer', ($event.target as HTMLTextAreaElement).value)"
        ></textarea>
        <button class="btn" type="button" :disabled="submittingExercise || !exerciseAnswer.trim()" @click="$emit('submitExercise')">
          {{ submittingExercise ? '评估中...' : '提交小练习' }}
        </button>
      </article>

      <article v-if="exerciseResult" class="exercise-result-card">
        <span>小练习反馈</span>
        <strong>{{ exerciseResult.score }} 分</strong>
        <p>{{ exerciseResult.feedback }}</p>
        <small>掌握度变化：{{ Math.round(exerciseResult.mastery_delta * 100) }}%</small>
      </article>
    </template>

    <div v-else class="empty">
      <strong>还没有导师回答</strong>
      <span>可以问概念、题目、材料片段。若已生成资源，回答会尽量结合引用来源。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownRenderer from './MarkdownRenderer.vue'
import type { TutorExercise, TutorExerciseResult, TutorNextStep } from '../types'

const props = defineProps<{
  answer: string
  loading?: boolean
  nextStep?: TutorNextStep | null
  exercise?: TutorExercise | null
  exerciseAnswer: string
  exerciseResult?: TutorExerciseResult | null
  submittingExercise?: boolean
}>()

defineEmits<{
  'update:exerciseAnswer': [value: string]
  submitExercise: []
}>()

const keyPoints = computed(() => {
  const lines = props.answer
    .split(/\r?\n/)
    .map(line => line.replace(/^[-#*\d.\s]+/, '').trim())
    .filter(line => line.length >= 6)
  return lines.slice(0, 4)
})
</script>
