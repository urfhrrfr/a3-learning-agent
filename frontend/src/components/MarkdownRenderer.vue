<template>
  <div class="markdown" v-html="html"></div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = defineProps<{ content: string }>()

const html = computed(() => props.content
  .replace(/&/g, '&amp;')
  .replace(/</g, '&lt;')
  .replace(/^# (.*)$/gm, '<h1>$1</h1>')
  .replace(/^## (.*)$/gm, '<h2>$1</h2>')
  .replace(/^- (.*)$/gm, '<li>$1</li>')
  .replace(/\n/g, '<br />'))
</script>
