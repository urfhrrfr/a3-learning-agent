<template>
  <div class="page">
    <div class="header resources-header">
      <div>
        <span class="eyebrow">我的学习资料</span>
        <h1>查看生成好的多模态学习材料</h1>
        <p class="muted">讲义、导图、练习、视频脚本、动画演示和代码案例都放在这里。先选一份打开，学完再收藏或屏蔽。</p>
      </div>
      <select v-model="filter" :disabled="!types.length" aria-label="筛选资源类型">
        <option value="">全部资源</option>
        <option v-for="t in types" :key="t" :value="t">{{ typeLabel(t) }}</option>
      </select>
    </div>

    <div class="resource-workspace">
      <section class="resource-sidebar">
        <div v-if="store.error && !store.resources.length" class="empty error-state">
          <strong>资源库暂时无法同步</strong>
          <span>{{ store.error }}</span>
          <button class="btn secondary" type="button" @click="store.refresh">重新同步</button>
        </div>

        <div class="resource-summary">
          <div>
            <span>可学习</span>
            <strong>{{ store.resources.length }}</strong>
          </div>
          <div>
            <span>已收藏</span>
            <strong>{{ favoriteCount }}</strong>
          </div>
          <div>
            <span>不适合</span>
            <strong>{{ hiddenCount }}</strong>
          </div>
        </div>

        <section class="panel compact-panel">
          <div class="panel-title">
            <div>
              <h2>材料类型</h2>
              <p class="muted compact">按生成结果真实统计，不补写空数据。</p>
            </div>
          </div>
          <div v-if="resourceTypeCounts.length" class="multimodal-list">
            <div v-for="item in resourceTypeCounts" :key="item.type">
              <span>{{ typeLabel(item.type) }}</span>
              <strong>{{ item.count }}</strong>
            </div>
          </div>
          <div v-else class="empty small-empty">
            <strong>暂无材料类型</strong>
            <span>生成材料后会显示类型分布。</span>
          </div>
        </section>

        <div class="cards resource-list">
          <ResourceCard
            v-for="r in filtered"
            :key="r.id"
            :resource="r"
            @select="selected = $event"
            @feedback="handleFeedback"
          />
          <div v-if="!filtered.length" class="empty">
            <strong>{{ store.resources.length ? '这个分类暂时没有材料' : '还没有学习材料' }}</strong>
            <span>{{ store.resources.length ? '这是因为当前筛选条件下没有匹配内容。切回“全部资源”，或重新生成一组更偏这个类型的材料。' : '这是因为你还没有生成材料。先去描述学习目标，系统会把内容整理成可阅读、可练习的材料包。' }}</span>
            <RouterLink v-if="!store.resources.length" class="btn secondary" to="/generate">生成第一套材料</RouterLink>
            <button v-else class="btn ghost" type="button" @click="filter = ''">查看全部资源</button>
          </div>
        </div>
      </section>

      <ResourceContent v-if="selected" :resource="selected" />
      <section v-else class="panel resource-content resource-placeholder">
        <span class="resource-kind">预览</span>
        <h2>选择左侧材料开始学习</h2>
        <p class="muted">打开后会看到正文、导图、练习、脚本、动画场景或代码案例。来源和审核说明收纳在详情底部。</p>
        <RouterLink v-if="!store.resources.length" class="btn secondary" to="/generate">先生成材料</RouterLink>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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
const resourceTypeCounts = computed(() => {
  const counts = new Map<string, number>()
  for (const resource of store.resources) counts.set(resource.type, (counts.get(resource.type) || 0) + 1)
  return [...counts.entries()].map(([type, count]) => ({ type, count }))
})

function typeLabel(type: string) {
  return typeLabels[type] || type
}

onMounted(async () => {
  await store.ensureReady()
  if (!selected.value && filtered.value.length) {
    selected.value = filtered.value[0]
  }
})

watch(filtered, (resources) => {
  if (!resources.length) {
    selected.value = null
    return
  }
  if (!selected.value || !resources.some(resource => resource.id === selected.value?.id)) {
    selected.value = resources[0]
  }
})

async function handleFeedback(resource: Resource, action: Resource['user_feedback']) {
  await store.submitResourceFeedback(resource.id, action)
  if (selected.value?.id === resource.id) {
    selected.value = store.resources.find(r => r.id === resource.id) || selected.value
  }
}
</script>
