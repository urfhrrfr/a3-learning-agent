<template>
  <section class="panel profile-chat-panel" :class="{ featured }">
    <div class="profile-chat-header">
      <div>
        <span class="eyebrow">画像从一句话开始</span>
        <h2>对话式画像构建</h2>
        <p class="muted compact">告诉我你的基础、目标、困惑和偏好的学习方式，我会把它整理成后续推荐会使用的学习档案。</p>
      </div>
      <span class="status" :class="{ running: sending || loading }">{{ sending || loading ? '正在更新' : '推荐先完成' }}</span>
    </div>
    <div class="profile-chat-layout">
      <div class="timeline profile-chat-thread">
        <div v-for="item in messages" :key="item" class="timeline-item">{{ item }}</div>
      </div>
      <div class="profile-chat-composer">
        <div class="prompt-chips" aria-label="可以补充的信息">
          <span>基础</span>
          <span>目标</span>
          <span>困惑</span>
          <span>偏好</span>
        </div>
        <textarea v-model="message" rows="5" placeholder="例如：我是大二学生，Python 基础一般，线性代数比较薄弱，希望用图解和代码案例学习机器学习。"></textarea>
        <div class="split">
          <button class="btn" :disabled="!message.trim() || sending || loading" @click="send">发送并更新画像</button>
          <span class="muted" v-if="sending || loading">正在更新画像并生成个性化建议...</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{ loading?: boolean; featured?: boolean }>()
const emit = defineEmits<{ send: [message: string] }>()
const message = ref('')
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
