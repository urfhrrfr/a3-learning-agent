<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark" aria-hidden="true">
          <span class="brand-mark-node"></span>
          <span class="brand-mark-path"></span>
        </span>
        <span>
          <strong>智学导航</strong>
          <small>Personal Learning Studio</small>
        </span>
      </RouterLink>
      <nav class="topnav" aria-label="主导航">
        <RouterLink v-for="item in nav" :key="item.path" :to="item.path">{{ item.label }}</RouterLink>
      </nav>
      <div class="topbar-actions">
        <span class="sync-state" :class="{ active: store.refreshing }">
          {{ store.refreshing ? '同步中' : '已就绪' }}
        </span>
      </div>
    </header>

    <main class="main">
      <div v-if="store.error" class="alert" role="alert">
        <span>{{ store.error }}</span>
        <button class="icon-btn" type="button" aria-label="关闭错误提示" @click="store.clearError">×</button>
      </div>
      <div v-if="store.refreshing" class="page-loading">
        正在同步画像、资源和学习路径...
      </div>
      <RouterView />
    </main>
    <DemoGuide />
  </div>
</template>

<script setup lang="ts">
import DemoGuide from './components/DemoGuide.vue'
import { useLearningStore } from './store'

const store = useLearningStore()
const nav = [
  { path: '/', label: '今日学习中心' },
  { path: '/profile', label: '我的学习档案' },
  { path: '/generate', label: '生成学习资料' },
  { path: '/resources', label: '我的学习资料' },
  { path: '/path', label: '我的学习任务' },
  { path: '/tutor', label: '智能导师' },
  { path: '/assessment', label: '学习结果' }
]
</script>
