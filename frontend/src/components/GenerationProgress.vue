<template>
  <section class="panel progress-panel">
    <div class="panel-title">
      <div>
        <h2>生成进度</h2>
        <p class="muted compact">{{ loading ? '正在为你准备学习资料' : statusText }}</p>
      </div>
      <span class="status" :class="{ running: loading }">{{ loading ? '生成中' : '待命' }}</span>
    </div>
    <div class="progress" aria-label="生成进度">
      <div :style="{ width: `${progress}%` }"></div>
    </div>
    <div class="progress-meta">
      <span>{{ Math.round(progress) }}%</span>
      <span>{{ loading ? currentStep : '等待任务启动' }}</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ progress: number; loading: boolean; currentStep: string }>()
const statusText = computed(() => props.progress > 0 ? '上一次生成已完成' : '提交任务后展示实时进度')
</script>
