import { defineStore } from 'pinia'
import { api } from './api'
import type { AgentTrace, AssessmentReport, LearningPath, PlanSummary, Profile, Resource } from './types'

interface LearningState {
  profile: Profile | null
  resources: Resource[]
  planSummary: PlanSummary | null
  traces: AgentTrace[]
  path: LearningPath | null
  report: AssessmentReport | null
  progress: number
  currentStep: string
  initialized: boolean
  refreshing: boolean
  loading: boolean
  assessing: boolean
  refreshingQuiz: boolean
  error: string
}

let refreshPromise: Promise<void> | null = null

export const useLearningStore = defineStore('learning', {
  state: (): LearningState => ({
    profile: null,
    resources: [],
    planSummary: null,
    traces: [],
    path: null,
    report: null,
    progress: 0,
    currentStep: '等待生成',
    initialized: false,
    refreshing: false,
    loading: false,
    assessing: false,
    refreshingQuiz: false,
    error: ''
  }),
  actions: {
    clearError() {
      this.error = ''
    },
    async ensureReady() {
      if (this.initialized) return
      await this.refresh()
    },
    async refresh() {
      if (refreshPromise) return refreshPromise
      refreshPromise = this.loadSnapshot()
      try {
        await refreshPromise
      } finally {
        refreshPromise = null
      }
    },
    async loadSnapshot() {
      this.refreshing = true
      try {
        this.error = ''
        const [profile, resources, path, report] = await Promise.all([
          api.profile(),
          api.resources(),
          api.path(),
          api.assessment()
        ])
        this.profile = profile
        this.resources = resources
        this.path = path
        this.report = report
        this.initialized = true
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.refreshing = false
      }
    },
    async sendProfileMessage(message: string) {
      try {
        this.error = ''
        const previousVersion = this.profile?.version
        const data = await api.profileChatAndGenerate(message)
        const validation = data.fusion_meta?.validation
        if (validation?.requires_confirmation && previousVersion) {
          const warnings = validation.warnings.length ? `\n\n${validation.warnings.join('\n')}` : ''
          const accepted = window.confirm(`本次画像更新存在较高风险，是否保留更新？${warnings}`)
          if (!accepted) {
            const rolledBack = await api.rollbackProfile(previousVersion)
            this.profile = rolledBack.profile
            if (rolledBack.learning_path) this.path = rolledBack.learning_path
            await this.refresh()
            return
          }
        }
        this.profile = data.profile
        if (data.resources && data.resources.length > 0) {
          this.resources = data.resources
        }
        if (data.learning_path) {
          this.path = data.learning_path
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      }
    },
    async generateResources(resourceTypes: string[] | Event = [], taskPrompt = '') {
      const requestedTypes = Array.isArray(resourceTypes) ? resourceTypes : []
      const prompt = taskPrompt.trim()
      const request = buildGenerationRequest({
        prompt,
        profile: this.profile,
        resourceTypes: requestedTypes
      })
      this.loading = true
      this.progress = 0
      this.currentStep = '创建生成任务'
      this.traces = []
      this.planSummary = null
      try {
        this.error = ''
        const job = await api.generateBackground(request)
        await this.watchGenerationJob(job.id)
        this.path = await api.path()
        this.initialized = true
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.loading = false
      }
    },
    async watchGenerationJob(jobId: string) {
      await new Promise<void>((resolve, reject) => {
        let source: EventSource | null = new EventSource(api.generationEventsUrl(jobId))
        let pollingTimer: ReturnType<typeof setInterval> | null = null
        let syncTimer: ReturnType<typeof setTimeout> | null = null
        let syncInFlight = false
        let syncQueued = false

        const cleanup = () => {
          if (source) {
            source.close()
            source = null
          }
          if (pollingTimer) {
            clearInterval(pollingTimer)
            pollingTimer = null
          }
          if (syncTimer) {
            clearTimeout(syncTimer)
            syncTimer = null
          }
        }

        const syncJob = async () => {
          if (syncInFlight) {
            syncQueued = true
            return
          }
          syncInFlight = true
          try {
            const latest = await api.job(jobId)
            this.progress = latest.progress
            this.currentStep = latest.current_step
            this.traces = latest.traces
            this.resources = latest.resources
            this.planSummary = latest.plan_summary
            if (latest.status === 'completed') {
              cleanup()
              resolve()
            }
            if (latest.status === 'failed') {
              cleanup()
              reject(new Error('资源生成任务失败'))
            }
          } catch (e) {
            // Ignore fetch errors during sync to allow retries
          } finally {
            syncInFlight = false
            if (syncQueued) {
              syncQueued = false
              scheduleSync()
            }
          }
        }

        const scheduleSync = () => {
          if (syncTimer) return
          syncTimer = setTimeout(() => {
            syncTimer = null
            void syncJob()
          }, 350)
        }

        const eventTypes = ['job_queued', 'job_started', 'agent_completed', 'resource_ready', 'job_completed', 'job_failed']
        for (const type of eventTypes) {
          source.addEventListener(type, () => {
            scheduleSync()
          })
        }

        source.onerror = () => {
          // SSE 中断时不立即抛出错误，而是尝试轮询，避免白屏
          if (!pollingTimer) {
            pollingTimer = setInterval(scheduleSync, 2000)
          }
        }
      })
    },
    async submitAssessment(answers: string[]) {
      this.assessing = true
      try {
        this.error = ''
        this.report = await api.submitQuiz(answers)
        this.profile = await api.profile()
        this.path = this.report.adjusted_path
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.assessing = false
      }
    },
    async refreshQuiz() {
      this.refreshingQuiz = true
      try {
        this.error = ''
        const quiz = await api.refreshQuiz()
        const existingIndex = this.resources.findIndex(resource => resource.type === 'quiz')
        if (existingIndex >= 0) {
          this.resources.splice(existingIndex, 1, quiz)
        } else {
          this.resources.push(quiz)
        }
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      } finally {
        this.refreshingQuiz = false
      }
    },
    async submitResourceFeedback(resourceId: string, action: Resource['user_feedback']) {
      try {
        this.error = ''
        const result = await api.resourceFeedback(resourceId, action)
        this.resources = this.resources.map(resource => resource.id === resourceId ? result.resource : resource)
        if (result.learning_path) this.path = result.learning_path
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      }
    }
  }
})

function buildGenerationRequest(options: {
  prompt: string
  profile: Profile | null
  resourceTypes: string[]
}) {
  const chapter = inferChapter(options.prompt) || options.profile?.current_chapter || '人工智能概述'
  const painPoints = inferPainPoints(options.prompt, options.profile?.weak_points || [])
  return {
    course: options.profile?.course || '人工智能导论',
    chapter,
    goal: options.prompt || options.profile?.learning_goal || '掌握核心概念',
    pain_points: painPoints,
    resource_types: options.resourceTypes
  }
}

function inferChapter(prompt: string) {
  const chapterAliases: Array<[string, string[]]> = [
    ['人工智能概述', ['人工智能概述', '人工智能导论', '图灵测试', '弱人工智能']],
    ['搜索问题与启发式搜索', ['搜索', '启发式', 'A*', 'A 星', '路径规划']],
    ['知识表示与推理', ['知识表示', '推理', '命题逻辑', '谓词逻辑', '产生式', '本体']],
    ['机器学习基础', ['机器学习基础', '机器学习', '训练集', '泛化', '损失函数', '过拟合']],
    ['监督学习', ['监督学习', '分类', '回归', '决策树', '评估指标']],
    ['无监督学习', ['无监督学习', '聚类', '降维', 'K-means', '主成分']],
    ['神经网络与深度学习入门', ['神经网络', '深度学习', '感知机', '反向传播', '激活函数', '梯度下降']],
    ['自然语言处理基础', ['自然语言处理', 'NLP', '分词', '词向量', '序列建模', '文本分类']],
    ['计算机视觉基础', ['计算机视觉', '图像', '卷积', '目标检测', '数据增强']],
    ['强化学习基础', ['强化学习', '状态', '动作', '奖励', '策略']],
    ['大模型与提示词工程', ['大模型', '提示词', 'Prompt', 'RAG', '上下文学习', '工具调用']],
    ['AI 伦理、安全与应用实践', ['伦理', '安全', '公平', '隐私', '可解释']]
  ]
  const normalized = prompt.toLowerCase()
  const matched = chapterAliases.find(([, aliases]) =>
    aliases.some(alias => normalized.includes(alias.toLowerCase()))
  )
  return matched?.[0]
}

function inferPainPoints(prompt: string, profileWeakPoints: string[]) {
  const weakPoints = [...profileWeakPoints]
  const candidates = ['概念混淆', '公式迁移', '模型评估指标', '过拟合', '泛化', '反向传播', '线性代数', 'Python']
  for (const candidate of candidates) {
    if (prompt.includes(candidate) && !weakPoints.includes(candidate)) {
      weakPoints.push(candidate)
    }
  }
  if (prompt.includes('考研') && !weakPoints.includes('考试复习')) {
    weakPoints.push('考试复习')
  }
  return weakPoints.slice(0, 10)
}
