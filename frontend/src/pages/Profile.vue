<template>
  <div class="page">
    <div class="header"><h1>学习画像</h1></div>
    <div class="grid">
      <ChatPanel class="span-7" @send="send" />
      <ProfileInsightPanel class="span-5" :profile="store.profile" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import ChatPanel from '../components/ChatPanel.vue'
import ProfileInsightPanel from '../components/ProfileInsightPanel.vue'
import { useLearningStore } from '../store'
const store = useLearningStore()
onMounted(store.refresh)
async function send(message: string) {
  await store.sendProfileMessage(message)
}
</script>
