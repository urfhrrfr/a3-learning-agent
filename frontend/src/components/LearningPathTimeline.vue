<template>
  <section class="panel">
    <div class="panel-title">
      <h2>接下来怎么学</h2>
      <span v-if="path" class="status">掌握度 {{ Math.round(path.mastery * 100) }}%</span>
    </div>
    <template v-if="path?.steps?.length">
      <p class="muted">{{ path.adjustment_reason }}</p>
      <div class="path-summary">
        <span>画像版本 v{{ path.profile_version }}</span>
        <span>{{ path.steps.length }} 个阶段</span>
        <span>{{ totalMinutes }} 分钟</span>
      </div>
      <div class="path-list">
        <div v-for="(step, index) in path.steps" :key="step.id" class="path-item">
          <div class="path-index">{{ index + 1 }}</div>
          <div class="path-body">
            <div class="split">
              <b>{{ step.title }}</b>
              <span class="status">{{ step.status }}</span>
            </div>
            <p>{{ step.objective }}</p>
            <p class="muted compact">{{ step.reason }}</p>
            <div class="meta-row">
              <span>预计 {{ step.estimated_minutes }} 分钟</span>
              <span>{{ step.recommended_resource_ids.length }} 份推荐资源</span>
            </div>
            <div class="chips">
              <span class="chip" v-for="id in step.recommended_resource_ids" :key="id">{{ id }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
    <div v-else class="empty">
      <strong>{{ path ? '学习路径暂无阶段' : '学习路径尚未生成' }}</strong>
      <span>先生成材料或做一次练习，系统就会按你的掌握度安排下一步。</span>
      <RouterLink class="btn ghost" to="/generate">生成学习材料</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { LearningPath } from '../types'

const props = defineProps<{ path: LearningPath | null }>()
const totalMinutes = computed(() => props.path?.steps.reduce((sum, step) => sum + step.estimated_minutes, 0) || 0)
</script>
