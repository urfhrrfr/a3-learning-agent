<template>
  <div class="page">
    <div class="header"><h1>练习评估</h1></div>
    <div class="grid">
      <QuizPlayer
        class="span-5"
        :submitting="store.assessing"
        :refreshing="store.refreshingQuiz"
        :questions="quizQuestions"
        @submit="store.submitAssessment"
        @refresh="store.refreshQuiz"
      />
      <AssessmentReport class="span-7" :report="store.report" />
      <LearningPathTimeline class="span-12" :path="store.path" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import QuizPlayer from '../components/QuizPlayer.vue'
import type { QuizQuestion } from '../components/QuizPlayer.vue'
import AssessmentReport from '../components/AssessmentReport.vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import { useLearningStore } from '../store'
const store = useLearningStore()
const quizQuestions = computed<QuizQuestion[]>(() => {
  const quizResource = store.resources.find(resource => resource.type === 'quiz')
  if (!quizResource) return []
  try {
    const parsed = JSON.parse(quizResource.content)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
})
onMounted(store.ensureReady)
</script>
