<template>
  <section class="panel">
    <h2>个性化学习路径</h2>
    <p v-if="path" class="muted">{{ path.adjustment_reason }} / 掌握度 {{ Math.round(path.mastery * 100) }}%</p>
    <div v-if="path" class="timeline">
      <div v-for="step in path.steps" :key="step.id" class="timeline-item">
        <div class="split"><b>{{ step.title }}</b><span class="status">{{ step.status }}</span></div>
        <p>{{ step.objective }}</p>
        <p class="muted">{{ step.reason }}，预计 {{ step.estimated_minutes }} 分钟</p>
        <div class="chips"><span class="chip" v-for="id in step.recommended_resource_ids" :key="id">{{ id }}</span></div>
      </div>
    </div>
    <p v-else class="muted">生成资源后会形成路径。</p>
  </section>
</template>

<script setup lang="ts">
import type { LearningPath } from '../types'
defineProps<{ path: LearningPath | null }>()
</script>
