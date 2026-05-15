<template>
  <div class="demo-guide" :class="{ open: expanded }">
    <button
      class="demo-guide-fab"
      type="button"
      :aria-expanded="expanded"
      aria-controls="demo-guide-panel"
      @click="expanded = !expanded"
    >
      演示模式
    </button>

    <aside v-if="expanded" id="demo-guide-panel" class="demo-guide-panel" aria-label="中国软件杯演示导航器">
      <div class="demo-guide-head">
        <div>
          <span class="eyebrow">7 分钟视频路线</span>
          <h2>按比赛要求录制</h2>
        </div>
        <button class="icon-btn with-border" type="button" aria-label="收起演示导航器" @click="expanded = false">×</button>
      </div>

      <div class="demo-guide-current">
        <span>当前步骤 {{ currentIndex + 1 }}/{{ steps.length }}</span>
        <strong>{{ currentStep.title }}</strong>
        <p>{{ currentStep.talkingPoint }}</p>
      </div>

      <div class="demo-step-list">
        <button
          v-for="(step, index) in steps"
          :key="step.title"
          class="demo-step"
          :class="{ active: index === currentIndex, here: route.path === step.path }"
          type="button"
          @click="currentIndex = index"
        >
          <span>{{ index + 1 }}</span>
          <div>
            <strong>{{ step.title }}</strong>
            <small>{{ step.pageLabel }}</small>
          </div>
        </button>
      </div>

      <section class="demo-guide-detail">
        <dl>
          <div>
            <dt>对应页面</dt>
            <dd>{{ currentStep.path }}</dd>
          </div>
          <div>
            <dt>视频要点</dt>
            <dd>{{ currentStep.talkingPoint }}</dd>
          </div>
          <div>
            <dt>推荐输入</dt>
            <dd>{{ currentStep.sampleInput || '本步骤主要展示已有真实数据和页面状态。' }}</dd>
          </div>
        </dl>
      </section>

      <div class="demo-guide-actions">
        <button class="btn ghost" type="button" :disabled="currentIndex === 0" @click="move(-1)">上一步</button>
        <button class="btn secondary" type="button" :disabled="!currentStep.sampleInput" @click="copyInput">
          {{ copied ? '已复制' : '复制示例输入' }}
        </button>
        <button class="btn hero-primary" type="button" @click="goCurrent">跳转页面</button>
        <button class="btn ghost" type="button" :disabled="currentIndex === steps.length - 1" @click="move(1)">下一步</button>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

interface DemoStep {
  title: string
  pageLabel: string
  path: string
  talkingPoint: string
  sampleInput?: string
}

const router = useRouter()
const route = useRoute()
const expanded = ref(false)
const copied = ref(false)

const steps: DemoStep[] = [
  {
    title: '开场：今日学习中心',
    pageLabel: '操作流程入口',
    path: '/',
    talkingPoint: '展示学生进入系统后先看到今天该学什么、薄弱点和三个主要行动入口。',
  },
  {
    title: '系统理解学生',
    pageLabel: '学生画像',
    path: '/profile',
    talkingPoint: '展示学习目标、薄弱点、学习偏好和系统建议，说明后续推荐不是通用内容。',
    sampleInput: '我是计算机专业大二学生，机器学习基础一般，最近在学神经网络，反向传播和损失函数总是搞不清楚，希望用图解和代码案例来学习。'
  },
  {
    title: '生成多模态资料',
    pageLabel: '资源生成',
    path: '/generate',
    talkingPoint: '输入学习需求，展示生成进度和图文、导图、练习、脚本、代码等多种材料类型。',
    sampleInput: '请围绕神经网络反向传播，为我生成讲义、思维导图、练习题、视频脚本和代码实操案例。'
  },
  {
    title: '查看生成效果',
    pageLabel: '材料库',
    path: '/resources',
    talkingPoint: '打开不同类型材料，重点展示多模态资源的正文、导图、练习、动画场景或代码案例。'
  },
  {
    title: '按任务清单学习',
    pageLabel: '学习路径',
    path: '/path',
    talkingPoint: '展示第一步学什么、第二步做什么、第三步练什么，以及每步预计时间。'
  },
  {
    title: '智能导师答疑',
    pageLabel: '智能导师',
    path: '/tutor',
    talkingPoint: '提出一个真实问题，展示回答正文、下一步建议和小练习。',
    sampleInput: '为什么反向传播需要链式法则？能不能用适合初学者的方式解释，并给我一个代码例子？'
  },
  {
    title: '练习评估闭环',
    pageLabel: '评估页',
    path: '/assessment',
    talkingPoint: '展示本次得分、主要错因、下一步怎么补和推荐学习任务。'
  },
  {
    title: '补充：AI 应用成果',
    pageLabel: '展开说明',
    path: '/generate',
    talkingPoint: '最后短暂展开“查看生成说明”，证明背后有资料规划、内容生成、审核和依据支撑。'
  }
]

const currentIndex = ref(Math.max(0, steps.findIndex(step => step.path === route.path)))
const currentStep = computed(() => steps[currentIndex.value])

watch(() => route.path, path => {
  const index = steps.findIndex(step => step.path === path)
  if (index >= 0) currentIndex.value = index
})

function move(delta: number) {
  currentIndex.value = Math.min(steps.length - 1, Math.max(0, currentIndex.value + delta))
  copied.value = false
}

async function goCurrent() {
  await router.push(currentStep.value.path)
}

async function copyInput() {
  if (!currentStep.value.sampleInput) return
  try {
    await navigator.clipboard.writeText(currentStep.value.sampleInput)
    copied.value = true
    window.setTimeout(() => {
      copied.value = false
    }, 1800)
  } catch {
    copied.value = false
  }
}
</script>
