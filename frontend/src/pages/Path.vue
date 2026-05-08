<template>
  <div class="page">
    <div class="header">
      <div><h1>学习路径</h1><p class="muted">路径会跟随画像和练习结果动态调整。</p></div>
      <button class="btn" @click="store.refresh">刷新路径</button>
    </div>
    <LearningPathTimeline :path="store.path" />
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import { useLearningStore } from '../store'
const store = useLearningStore()
onMounted(store.refresh)
</script>
