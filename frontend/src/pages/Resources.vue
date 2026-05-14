<template>
  <div class="page">
    <div class="header resources-header">
      <div>
        <h1>资源库</h1>
        <p class="muted">按学习资源浏览内容，默认隐藏技术来源和审核细节。</p>
      </div>
      <select v-model="filter" :disabled="!types.length" aria-label="筛选资源类型">
        <option value="">全部资源</option>
        <option v-for="t in types" :key="t" :value="t">{{ typeLabel(t) }}</option>
      </select>
    </div>

    <div class="resource-workspace">
      <section class="resource-sidebar">
        <div class="resource-summary">
          <div>
            <span>全部</span>
            <strong>{{ store.resources.length }}</strong>
          </div>
          <div>
            <span>收藏</span>
            <strong>{{ favoriteCount }}</strong>
          </div>
          <div>
            <span>屏蔽</span>
            <strong>{{ hiddenCount }}</strong>
          </div>
        </div>

        <div class="cards resource-list">
          <ResourceCard
            v-for="r in filtered"
            :key="r.id"
            :resource="r"
            @select="selected = $event"
            @feedback="handleFeedback"
          />
          <div v-if="!filtered.length" class="empty">暂无资源。请先到“资源生成”页面启动一次生成任务。</div>
        </div>
      </section>

      <ResourceContent v-if="selected" :resource="selected" />
      <section v-else class="panel resource-content resource-placeholder">
        <span class="resource-kind">预览</span>
        <h2>选择一个资源开始查看</h2>
        <p class="muted">这里会展示干净的学习内容；来源、审核说明等信息会收纳在详情底部。</p>
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

const typeLabels: Record<string, string> = {
  lecture_doc: '图文讲解',
  mind_map: '思维导图',
  quiz: '互动练习',
  reading: '拓展阅读',
  media_script: '视频脚本',
  animation_demo: '动画演示',
  ppt_draft: 'PPT 草稿',
  visual_card: '学习卡片',
  code_case: '代码实验'
}

const types = computed(() => [...new Set(store.resources.map(r => r.type))])
const filtered = computed(() => filter.value ? store.resources.filter(r => r.type === filter.value) : store.resources)
const favoriteCount = computed(() => store.resources.filter(r => r.user_feedback === 'favorite').length)
const hiddenCount = computed(() => store.resources.filter(r => r.user_feedback === 'hidden').length)

function typeLabel(type: string) {
  return typeLabels[type] || type
}

onMounted(async () => {
  await store.ensureReady()
  if (!selected.value && filtered.value.length) {
    selected.value = filtered.value[0]
  }
})

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  await store.submitResourceFeedback(resource.id, action)
  if (selected.value?.id === resource.id) {
    selected.value = store.resources.find(r => r.id === resource.id) || selected.value
  }
}
</script>
