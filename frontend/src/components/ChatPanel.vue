<template>
  <section class="panel">
    <h2>对话式画像构建</h2>
    <div class="timeline">
      <div v-for="item in messages" :key="item" class="timeline-item">{{ item }}</div>
    </div>
    <textarea v-model="message" rows="4" placeholder="例如：我线性代数比较薄弱，希望多给代码案例和动画解释"></textarea>
    <div class="split">
      <button class="btn" :disabled="!message.trim() || sending" @click="send">发送并更新画像</button>
      <span class="muted" v-if="sending">正在抽取画像...</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const emit = defineEmits<{ send: [message: string] }>()
const message = ref('我线性代数比较薄弱，希望多给 Python 代码案例和动画解释')
const sending = ref(false)
const messages = ref(['系统：告诉我你的基础、目标、困惑和偏好的学习方式。'])

async function send() {
  sending.value = true
  messages.value.push(`学生：${message.value}`)
  emit('send', message.value)
  message.value = ''
  setTimeout(() => {
    messages.value.push('系统：画像已更新，下一步可以生成个性化资源。')
    sending.value = false
  }, 450)
}
</script>
