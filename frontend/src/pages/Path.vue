<template>
  <div class="page">
    <div class="header">
      <div><h1>学习路径</h1><p class="muted">路径会跟随画像和练习结果动态调整。</p></div>
      <button class="btn" @click="store.refresh">刷新路径</button>
    </div>
    <LearningPathTimeline v-if="store.path" :path="store.path" />
    <div v-else class="empty">暂无学习路径，请先在【资源生成】中生成资源。</div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import { useLearningStore } from '../store'
const store = useLearningStore()
onMounted(store.ensureReady)
</script>
