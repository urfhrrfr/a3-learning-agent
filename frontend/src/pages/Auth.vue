<template>
  <section class="auth-page">
    <div class="auth-panel">
      <div class="auth-copy">
        <span class="eyebrow">Personal Learning Studio</span>
        <h1>{{ isRegisterMode ? '创建你的专属学习空间' : '欢迎回来' }}</h1>
        <p>{{ isRegisterMode ? '首次注册后，系统会把画像、资料、路径和测评都绑定到这个账号。' : '登录后继续读取你的画像、资料、学习路径和练习记录。' }}</p>
        <div class="auth-signal">
          <span>{{ isRegisterMode ? '首次绑定' : '专属档案' }}</span>
          <strong>{{ isRegisterMode ? 'Single user' : store.authStatus?.registration_mode || 'single' }}</strong>
        </div>
      </div>

      <form class="auth-form" @submit.prevent="submit">
        <div class="panel-title">
          <div>
            <h2>{{ isRegisterMode ? '首次注册' : '账号登录' }}</h2>
            <p class="muted compact">{{ isRegisterMode ? '创建后注册入口会关闭。' : '请输入首次注册时设置的账号。' }}</p>
          </div>
        </div>

        <label class="field-label">
          <span>用户名</span>
          <input v-model.trim="username" autocomplete="username" minlength="3" maxlength="40" required />
        </label>
        <label v-if="isRegisterMode" class="field-label">
          <span>显示名称</span>
          <input v-model.trim="displayName" autocomplete="name" maxlength="60" />
        </label>
        <label class="field-label">
          <span>密码</span>
          <input v-model="password" type="password" autocomplete="current-password" minlength="6" maxlength="128" required />
        </label>
        <label v-if="isRegisterMode" class="field-label">
          <span>确认密码</span>
          <input v-model="confirmPassword" type="password" autocomplete="new-password" minlength="6" maxlength="128" required />
        </label>

        <div v-if="error" class="auth-error">{{ error }}</div>
        <button class="btn" type="submit" :disabled="submitting">
          <span v-if="submitting" class="btn-spinner"></span>
          {{ isRegisterMode ? '创建并进入' : '登录' }}
        </button>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useLearningStore } from '../store'
import { friendlyErrorMessage } from '../store'

const store = useLearningStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const displayName = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const error = ref('')

const isRegisterMode = computed(() => !store.authStatus?.has_user && store.authStatus?.registration_mode !== 'disabled')

onMounted(async () => {
  if (!store.authReady) await store.initAuth()
})

async function submit() {
  error.value = ''
  if (isRegisterMode.value && password.value !== confirmPassword.value) {
    error.value = '两次输入的密码不一致'
    return
  }
  submitting.value = true
  try {
    if (isRegisterMode.value) {
      await store.register(username.value, password.value, displayName.value)
    } else {
      await store.login(username.value, password.value)
    }
    await router.replace(String(route.query.redirect || '/'))
  } catch (err) {
    error.value = friendlyErrorMessage(err, isRegisterMode.value ? '注册失败' : '登录失败')
  } finally {
    submitting.value = false
  }
}
</script>
