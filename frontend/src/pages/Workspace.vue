<template>
  <div class="page">
    <div class="header">
      <div>
        <h1>学习工作台</h1>
        <p class="muted">从画像、资源、路径到评估的完整演示闭环。</p>
      </div>
      <button class="btn" @click="store.generateResources" :disabled="store.loading">
        {{ store.loading ? '生成中...' : '生成个性化资源' }}
      </button>
    </div>

    <section class="overview-band">
      <div class="metric">
        <span>画像版本</span>
        <strong>v{{ store.profile?.version || '-' }}</strong>
      </div>
      <div class="metric">
        <span>掌握度</span>
        <strong>{{ masteryText }}</strong>
      </div>
      <div class="metric">
        <span>资源数量</span>
        <strong>{{ store.resources.length }}</strong>
      </div>
      <div class="metric">
        <span>路径步骤</span>
        <strong>{{ store.path?.steps.length || 0 }}</strong>
      </div>
    </section>

    <section class="panel flow-panel">
      <h2>演示闭环</h2>
      <div class="flow-strip">
        <span>画像诊断</span>
        <span>资源生成</span>
        <span>路径推荐</span>
        <span>智能辅导</span>
        <span>练习评估</span>
      </div>
    </section>

    <div class="grid">
      <ProfileInsightPanel class="span-4" :profile="store.profile" />
      <LearningPathTimeline class="span-8" :path="store.path" />
      <GenerationProgress class="span-4" :progress="store.progress" :loading="store.loading" :current-step="store.currentStep" />
      <section class="panel span-8">
        <div class="panel-title">
          <h2>最近资源</h2>
          <span class="muted">{{ store.resources.length ? '展示最近 3 份生成材料' : '等待生成' }}</span>
        </div>
        <div v-if="store.resources.length" class="cards">
          <ResourceCard
            v-for="r in store.resources.slice(0, 3)"
            :key="r.id"
            :resource="r"
            @select="selected = $event"
            @feedback="handleFeedback"
          />
        </div>
        <div v-else class="empty">还没有生成资源。点击右上角按钮后，这里会展示最近生成的学习材料。</div>
      </section>
      <ResourceContent v-if="selected" class="span-12" :resource="selected" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useLearningStore } from '../store'
import type { Resource } from '../types'
import ProfileInsightPanel from '../components/ProfileInsightPanel.vue'
import LearningPathTimeline from '../components/LearningPathTimeline.vue'
import GenerationProgress from '../components/GenerationProgress.vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'

const store = useLearningStore()
const selected = ref<Resource | null>(null)
const masteryText = computed(() => store.profile ? `${Math.round(store.profile.mastery * 100)}%` : '-')
onMounted(store.ensureReady)

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  await store.submitResourceFeedback(resource.id, action)
}
</script>
