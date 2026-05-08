<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">A3 学习智能体</div>
      <RouterLink v-for="item in nav" :key="item.path" :to="item.path">{{ item.label }}</RouterLink>
    </aside>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
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
