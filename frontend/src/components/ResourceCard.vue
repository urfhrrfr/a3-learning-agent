<template>
  <article class="panel">
    <div class="split"><h2>{{ resource.title }}</h2><span class="status">{{ resource.review_status }}</span></div>
    <p class="muted">{{ resource.type }} / {{ resource.difficulty }}</p>
    <div class="chips">
      <span class="chip" v-for="ref in resource.source_refs" :key="ref">{{ ref }}</span>
    </div>
    <div class="chips">
      <span class="chip" v-for="agent in resource.created_by_agents" :key="agent">{{ agent }}</span>
    </div>
    <button class="btn secondary" @click="$emit('select', resource)">查看内容</button>
  </article>
</template>

<script setup lang="ts">
import type { Resource } from '../types'
defineProps<{ resource: Resource }>()
defineEmits<{ select: [resource: Resource] }>()
</script>
