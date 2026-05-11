<template>
  <div class="shell">
    <header class="topbar">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">A3</span>
        <span>
          <strong>学习智能体</strong>
          <small>AI Learning Workspace</small>
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
  </div>
</template>

<script setup lang="ts">
import { useLearningStore } from './store'

const store = useLearningStore()
const nav = [
  { path: '/', label: '工作台' },
  { path: '/profile', label: '学习画像' },
  { path: '/generate', label: '资源生成' },
  { path: '/resources', label: '资源库' },
  { path: '/path', label: '学习路径' },
  { path: '/tutor', label: '智能辅导' },
  { path: '/assessment', label: '练习评估' }
]
</script>
