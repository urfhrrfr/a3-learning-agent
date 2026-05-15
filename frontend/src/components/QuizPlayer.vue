<template>
  <section class="panel">
    <div class="panel-title">
      <h2>开始练习</h2>
      <span class="status">{{ questions.length ? `题目 ${currentIndex + 1}/${questions.length}` : '示例题' }}</span>
    </div>

    <div class="quiz-meta" v-if="currentQuestion">
      <span>{{ currentQuestion.type || '问答题' }}</span>
      <span>{{ currentQuestion.difficulty || currentQuestion.level || '基础' }}</span>
      <span v-if="currentQuestion.assessment_point">{{ currentQuestion.assessment_point }}</span>
    </div>

    <div v-if="!questions.length" class="empty small-empty">
      <strong>还没有配套题库</strong>
      <span>这是因为当前材料里没有练习题。你仍可以先做这道示例题体验反馈流程，或生成一套更贴合当前章节的题库。</span>
      <RouterLink class="btn ghost" to="/generate">生成配套题库</RouterLink>
    </div>

    <p class="quiz-question">题目：{{ questionText }}</p>

    <div v-if="currentQuestion?.options?.length" class="option-list">
      <button
        v-for="option in currentQuestion.options"
        :key="option"
        type="button"
        class="option-btn"
        :class="{ selected: answer === option }"
        @click="answer = option"
      >
        {{ option }}
      </button>
    </div>

    <textarea v-model="answer" rows="5" placeholder="请写下你的理解、判断依据或解题过程。"></textarea>

    <div class="resource-actions">
      <button class="btn secondary" :disabled="!questions.length || currentIndex === 0" @click="move(-1)">上一题</button>
      <button class="btn secondary" :disabled="!questions.length || currentIndex >= questions.length - 1" @click="move(1)">下一题</button>
      <button class="btn ghost" :disabled="submitting || refreshing" @click="$emit('refresh')">
        {{ refreshing ? '刷新中...' : '换一组题' }}
      </button>
      <button class="btn" :disabled="submitting || !answer.trim()" @click="submit">
        {{ submitting ? '评估中...' : '提交练习' }}
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

export interface QuizQuestion {
  level?: string
  difficulty?: string
  type?: string
  question?: string
  stem?: string
  answer?: string
  explanation?: string
  assessment_point?: string
  options?: string[]
}

const props = defineProps<{ submitting?: boolean; refreshing?: boolean; questions?: QuizQuestion[] }>()
const emit = defineEmits<{ submit: [answers: string[]]; refresh: [] }>()

const fallbackQuestion: QuizQuestion = {
  type: '问答题',
  difficulty: '基础',
  question: '为什么只看训练准确率可能误导学习效果判断？请结合“泛化”或“过拟合”回答。',
  assessment_point: '泛化与过拟合'
}

const currentIndex = ref(0)
const answer = ref('')
const questions = computed(() => props.questions || [])
const currentQuestion = computed(() => questions.value[currentIndex.value] || fallbackQuestion)
const questionText = computed(() => currentQuestion.value.question || currentQuestion.value.stem || fallbackQuestion.question)

watch(
  () => props.questions,
  () => {
    currentIndex.value = 0
    answer.value = ''
  },
  { immediate: true }
)

function move(offset: number) {
  currentIndex.value = Math.min(Math.max(currentIndex.value + offset, 0), Math.max(questions.value.length - 1, 0))
  answer.value = ''
}

function submit() {
  emit('submit', [`题目：${questionText.value}\n回答：${answer.value}`])
}
</script>
