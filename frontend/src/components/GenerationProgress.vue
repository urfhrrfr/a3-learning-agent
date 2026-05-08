<template>
  <section class="panel">
    <h2>生成进度</h2>
    <div class="progress"><div :style="{ width: `${progress}%` }"></div></div>
    <p class="muted">{{ loading ? '多智能体正在协同生成资源...' : `当前进度 ${progress}%` }}</p>
  </section>
</template>

<script setup lang="ts">
defineProps<{ progress: number; loading: boolean }>()
</script>
