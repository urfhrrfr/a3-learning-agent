<template>
  <div class="page">
    <div class="header">
      <div><h1>资源库</h1><p class="muted">所有资源都展示来源、难度、审核状态和创建智能体。</p></div>
      <select v-model="filter" :disabled="!types.length">
        <option value="">全部</option>
        <option v-for="t in types" :key="t">{{ t }}</option>
      </select>
    </div>
    <div class="grid">
      <section class="panel span-12">
        <div class="panel-title">
          <h2>推送策略反馈</h2>
          <span class="muted">收藏 {{ favoriteCount }} 份 / 屏蔽 {{ hiddenCount }} 份</span>
        </div>
        <p class="compact muted">收藏会提高后续路径推荐优先级，屏蔽会从推荐池移除并触发路径重排。</p>
      </section>
      <section class="span-5 cards">
        <ResourceCard
          v-for="r in filtered"
          :key="r.id"
          :resource="r"
          @select="selected = $event"
          @feedback="handleFeedback"
        />
        <div v-if="!filtered.length" class="empty">暂无资源。请先到“资源生成”页面启动一次生成任务。</div>
      </section>
      <ResourceContent v-if="selected" class="span-7" :resource="selected" />
      <section v-else class="panel span-7 resource-content">
        <p class="muted">请选择一个资源查看详情。</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import ResourceCard from '../components/ResourceCard.vue'
import ResourceContent from '../components/ResourceContent.vue'
import { useLearningStore } from '../store'
import type { Resource } from '../types'
const store = useLearningStore()
const selected = ref<Resource | null>(null)
const filter = ref('')
const types = computed(() => [...new Set(store.resources.map(r => r.type))])
const filtered = computed(() => filter.value ? store.resources.filter(r => r.type === filter.value) : store.resources)
const favoriteCount = computed(() => store.resources.filter(r => r.user_feedback === 'favorite').length)
const hiddenCount = computed(() => store.resources.filter(r => r.user_feedback === 'hidden').length)
onMounted(store.ensureReady)

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  await store.submitResourceFeedback(resource.id, action)
  if (selected.value?.id === resource.id) selected.value = store.resources.find(r => r.id === resource.id) || selected.value
}
</script>
