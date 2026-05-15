<template>
  <section class="loop-overview panel">
    <div class="panel-title">
      <div>
        <h2>学习闭环总览</h2>
        <p class="muted compact">画像、资源、路径、辅导和评估之间的数据流全部来自当前 store。</p>
      </div>
      <span class="status completed">{{ completedCount }}/{{ nodes.length }} 已就绪</span>
    </div>

    <div class="loop-track">
      <RouterLink
        v-for="(node, index) in nodes"
        :key="node.key"
        class="loop-node"
        :class="{ done: node.done, active: node.key === activeKey }"
        :to="node.path"
      >
        <span class="loop-index">{{ index + 1 }}</span>
        <div>
          <strong>{{ node.title }}</strong>
          <small>{{ node.summary }}</small>
        </div>
        <em>{{ node.metric }}</em>
      </RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTrace, AssessmentReport, LearningPath, Profile, Resource } from '../types'

const props = defineProps<{
  profile: Profile | null
  resources: Resource[]
  path: LearningPath | null
  report: AssessmentReport | null
  traces: AgentTrace[]
  activeKey?: string
}>()

const nodes = computed(() => [
  {
    key: 'profile',
    title: '学生画像',
    summary: props.profile ? props.profile.learning_goal : '等待学习目标和薄弱点',
    metric: props.profile ? `v${props.profile.version}` : '未建立',
    path: '/profile',
    done: Boolean(props.profile)
  },
  {
    key: 'resources',
    title: '资源生成',
    summary: props.resources.length ? '多格式材料进入资源库' : '等待智能体生成',
    metric: `${props.resources.length} 份`,
    path: '/generate',
    done: props.resources.length > 0
  },
  {
    key: 'path',
    title: '学习路径',
    summary: props.path?.adjustment_reason || '等待路径规划',
    metric: `${props.path?.steps.length || 0} 阶段`,
    path: '/path',
    done: Boolean(props.path?.steps?.length)
  },
  {
    key: 'tutor',
    title: '智能辅导',
    summary: props.traces.length ? '可追踪智能体协作过程' : '等待提问或生成记录',
    metric: `${props.traces.length} 轨迹`,
    path: '/tutor',
    done: props.traces.length > 0
  },
  {
    key: 'assessment',
    title: '效果评估',
    summary: props.report ? props.report.feedback : '等待练习反馈',
    metric: props.report ? `${props.report.score} 分` : '未评估',
    path: '/assessment',
    done: Boolean(props.report)
  }
])

const completedCount = computed(() => nodes.value.filter(node => node.done).length)
</script>
