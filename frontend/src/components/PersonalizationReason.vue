<template>
  <section class="panel personalization-panel">
    <div class="panel-title">
      <div>
        <h2>为什么这样回答</h2>
        <p class="muted compact">基于当前画像、引用资源和导师返回的个性化信息说明。</p>
      </div>
      <span class="status">{{ reasons.length ? '有依据' : '待补充' }}</span>
    </div>

    <div v-if="reasons.length" class="reason-chip-grid">
      <article v-for="reason in reasons" :key="reason.title" class="reason-chip-card">
        <span>{{ reason.tag }}</span>
        <strong>{{ reason.title }}</strong>
        <small>{{ reason.detail }}</small>
      </article>
    </div>

    <div v-else class="empty small-empty">
      <strong>暂无足够画像信息</strong>
      <span>完善画像或生成学习资源后，系统会更明确地说明个性化回答依据。</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Profile, Resource, TutorResponse } from '../types'

const props = defineProps<{
  profile: Profile | null
  personalization?: TutorResponse['personalization'] | null
  citedResources?: NonNullable<TutorResponse['cited_resources']>
  selectedResource?: Resource | null
  profileSuggestion?: TutorResponse['profile_suggestion'] | null
}>()

const reasons = computed(() => {
  const items: Array<{ tag: string; title: string; detail: string }> = []
  if (props.profile?.learning_goal) {
    items.push({
      tag: '目标',
      title: '结合你的学习目标',
      detail: props.profile.learning_goal
    })
  }
  const weakPoints = props.personalization?.weak_points?.length
    ? props.personalization.weak_points
    : props.profile?.weak_points || []
  if (weakPoints.length) {
    items.push({
      tag: '薄弱点',
      title: '针对当前薄弱知识展开',
      detail: weakPoints.slice(0, 4).join('、')
    })
  }
  const modalities = props.personalization?.preferred_modalities?.length
    ? props.personalization.preferred_modalities
    : props.profile?.preferred_modalities || []
  if (modalities.length) {
    items.push({
      tag: '偏好',
      title: '匹配资源呈现方式',
      detail: modalities.slice(0, 4).join('、')
    })
  }
  if (props.profile?.cognitive_style) {
    items.push({
      tag: '风格',
      title: '适配认知风格',
      detail: props.profile.cognitive_style
    })
  }
  if (props.selectedResource || props.citedResources?.length) {
    items.push({
      tag: '依据',
      title: '优先结合已生成材料',
      detail: props.selectedResource?.title || props.citedResources?.map(item => item.title).join('、') || ''
    })
  }
  if (props.profileSuggestion) {
    items.push({
      tag: '画像',
      title: '回答可能影响画像',
      detail: props.profileSuggestion.message
    })
  }
  return items.slice(0, 6)
})
</script>
