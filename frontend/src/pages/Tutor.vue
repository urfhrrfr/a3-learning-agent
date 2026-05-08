<template>
  <div class="page">
    <div class="header"><h1>智能辅导</h1></div>
    <div class="grid">
      <section class="panel span-5">
        <h2>提问</h2>
        <textarea rows="5" v-model="question"></textarea>
        <button class="btn" @click="ask">发送</button>
      </section>
      <section class="panel span-7">
        <h2>回答</h2>
        <MarkdownRenderer :content="answer" />
        <MermaidRenderer v-if="mermaid" :content="mermaid" />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { api } from '../api'
import MarkdownRenderer from '../components/MarkdownRenderer.vue'
import MermaidRenderer from '../components/MermaidRenderer.vue'
const question = ref('为什么训练准确率高，测试效果仍然可能不好？')
const answer = ref('等待提问...')
const mermaid = ref('')
async function ask() {
  const data = await api.tutor(question.value) as { answer: string; mermaid: string }
  answer.value = data.answer
  mermaid.value = data.mermaid
}
</script>
