<template>
  <div class="page">
    <div class="header"><h1>学习画像</h1></div>
    <div class="grid">
      <ChatPanel class="span-7" :loading="loading" @send="send" />
      <ProfileInsightPanel class="span-5" :profile="store.profile" />
      <section class="panel span-12">
        <div class="panel-title">
          <h2>画像维度清单与更新规则</h2>
        </div>
        <table class="storyboard-table" v-if="dimensions.length">
          <thead>
            <tr>
              <th>维度</th>
              <th>字段</th>
              <th>取值类型</th>
              <th>定义</th>
              <th>更新策略</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in dimensions" :key="item.key">
              <td>{{ item.label }}</td>
              <td><code>{{ item.key }}</code></td>
              <td>{{ item.value_type }}</td>
              <td>{{ item.description }}</td>
              <td>{{ item.update_rule }}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <section class="panel span-12">
        <div class="panel-title">
          <h2>随学随新：版本变更轨迹</h2>
        </div>
        <div v-if="changeLogs.length" class="trace-list">
          <article class="trace-item" v-for="log in changeLogs.slice(0, 8)" :key="`${log.version}-${log.updated_at}`">
            <div class="trace-index">v{{ log.version }}</div>
            <div class="trace-body">
              <p class="compact"><b>触发语句：</b>{{ log.trigger_message }}</p>
              <p class="compact"><b>更新时间：</b>{{ log.updated_at }}</p>
              <p class="compact"><b>变化字段：</b>{{ Object.keys(log.changed_fields).join('、') || '无字段变化' }}</p>
              <div class="chips">
                <span class="chip" v-for="key in Object.keys(log.extracted)" :key="key">{{ key }} 已提取</span>
              </div>
              <details class="profile-diff">
                <summary>查看字段 before/after 对比</summary>
                <pre>{{ renderChangedFields(log.changed_fields) }}</pre>
              </details>
            </div>
          </article>
        </div>
        <p v-else class="muted">暂无画像变更日志，发送一条画像对话后会自动记录。</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { api } from '../api'
import ChatPanel from '../components/ChatPanel.vue'
import ProfileInsightPanel from '../components/ProfileInsightPanel.vue'
import { useLearningStore } from '../store'
import type { ProfileChangeLog, ProfileDimension } from '../types'

const store = useLearningStore()
const dimensions = ref<ProfileDimension[]>([])
const changeLogs = ref<ProfileChangeLog[]>([])

async function loadProfileMeta() {
  const [dimensionRows, logs] = await Promise.all([api.profileDimensions(), api.profileChangeLog()])
  dimensions.value = dimensionRows
  changeLogs.value = logs
}

onMounted(async () => {
  await store.ensureReady()
  await loadProfileMeta()
})

const loading = ref(false)

async function send(message: string) {
  loading.value = true
  await store.sendProfileMessage(message)
  await loadProfileMeta()
  loading.value = false
}

function renderChangedFields(changedFields: ProfileChangeLog['changed_fields']) {
  return JSON.stringify(changedFields, null, 2)
}
</script>
