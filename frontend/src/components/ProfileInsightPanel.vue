<template>
  <section class="panel">
    <h2>学习画像 v{{ profile?.version || '-' }}</h2>
    <div v-if="profile" class="timeline">
      <div><b>专业层次：</b>{{ profile.major }} / {{ profile.education_level }}</div>
      <div><b>当前章节：</b>{{ profile.course }} - {{ profile.current_chapter }}</div>
      <div><b>学习目标：</b>{{ profile.learning_goal }}</div>
      <div><b>认知风格：</b>{{ profile.cognitive_style }}</div>
      <div><b>时间预算：</b>{{ profile.time_budget }}</div>
      <div><b>掌握度：</b>{{ Math.round(profile.mastery * 100) }}%</div>
      <div class="chips"><span class="chip" v-for="item in profile.preferred_modalities" :key="item">{{ item }}</span></div>
      <div class="chips"><span class="chip" v-for="item in profile.weak_points" :key="item">{{ item }}</span></div>
      <div class="chips"><span class="chip" v-for="item in profile.mistake_patterns" :key="item">{{ item }}</span></div>
    </div>
    <p v-else class="muted">正在读取画像...</p>
  </section>
</template>

<script setup lang="ts">
import type { Profile } from '../types'
defineProps<{ profile: Profile | null }>()
</script>
