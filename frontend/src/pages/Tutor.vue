<template>
  <div class="page">
    <div class="header"><h1>智能辅导</h1></div>
    <div class="grid">
      <section class="panel span-5">
        <h2>提问</h2>
        <textarea rows="5" v-model="question"></textarea>
        <div class="split">
          <button class="btn" :disabled="asking || !question.trim()" @click="ask">
            {{ asking ? '思考中...' : '发送' }}
          </button>
          <span v-if="asking" class="inline-state">正在结合画像和课程资源生成回答</span>
        </div>
      </section>
      <section class="panel span-7">
        <div class="panel-title">
          <h2>回答</h2>
          <div class="trace-badges">
            <span class="chip provider">{{ providerLabel }}</span>
            <span class="chip" :class="usedFallback ? 'warning' : 'success'">{{ usedFallback ? '模板兜底' : '大模型回答' }}</span>
          </div>
        </div>
        <div v-if="localError" class="empty">{{ localError }}</div>
        <MarkdownRenderer :content="answer" />
        <p v-if="fallbackReason" class="review-note">兜底原因：{{ fallbackReason }}</p>
        <p v-if="sourceRefs.length" class="muted compact">下方是知识库引用标签，用于说明回答依据的课程片段，当前不是可点击链接。</p>
        <div class="chips" v-if="sourceRefs.length">
          <span v-for="ref in sourceRefs" :key="ref" class="chip">{{ ref }}</span>
        </div>
        <MermaidRenderer v-if="mermaid" :content="mermaid" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { api } from '../api'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'

const question = ref('为什么训练准确率高，测试效果仍然可能不好？')
const answer = ref('等待提问...')
const mermaid = ref('')
const provider = ref('')
const usedFallback = ref(false)
const fallbackReason = ref('')
const sourceRefs = ref<string[]>([])
const asking = ref(false)
const localError = ref('')

const providerLabel = computed(() => {
  if (provider.value === 'spark') return '星火模型'
  if (provider.value === 'mock') return 'Mock'
  return provider.value || '未提问'
})

async function ask() {
  asking.value = true
  localError.value = ''
  try {
    const data = await api.tutor(question.value)
    answer.value = data.answer
    mermaid.value = data.mermaid
    provider.value = data.llm_provider || ''
    usedFallback.value = Boolean(data.used_fallback)
    fallbackReason.value = data.fallback_reason || ''
    sourceRefs.value = data.source_refs || []
  } catch (error) {
    localError.value = error instanceof Error ? error.message : String(error)
  } finally {
    asking.value = false
  }
}
</script>
