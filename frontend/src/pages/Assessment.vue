<template>
  <div class="page">
    <div class="header"><h1>练习评估</h1></div>
    <div class="grid">
      <QuizPlayer class="span-5" @submit="store.submitAssessment" />
      <AssessmentReport class="span-7" :report="store.report" />
      <LearningPathTimeline class="span-12" :path="store.path" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import QuizPlayer from '../components/QuizPlayer.vue'
import AssessmentReport from '../components/AssessmentReport.vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import { useLearningStore } from '../store'
const store = useLearningStore()
onMounted(store.refresh)
</script>
