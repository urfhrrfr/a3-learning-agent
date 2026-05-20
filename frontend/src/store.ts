import { defineStore } from 'pinia'
import { api } from './api'
import type {
  AgentTrace,
  AssessmentHistoryItem,
  AssessmentReport,
  GenerationHistoryItem,
  GenerationHistorySummary,
  HealthStatus,
  LearningPath,
  LearningPathHistoryItem,
  PlanSummary,
  Profile,
  ProfileChatResponse,
  Resource
} from './types'

interface LearningState {
  health: HealthStatus | null
  profile: Profile | null
  resources: Resource[]
  resourceHistory: GenerationHistorySummary[]
  resourceHistoryDetails: Record<string, GenerationHistoryItem>
  planSummary: PlanSummary | null
  traces: AgentTrace[]
  path: LearningPath | null
  pathHistory: LearningPathHistoryItem[]
  report: AssessmentReport | null
  assessmentHistory: AssessmentHistoryItem[]
  lastProfileUpdate: (ProfileChatResponse & { resources?: Resource[]; learning_path?: LearningPath | null; message?: string }) | null
  progress: number
  currentStep: string
  initialized: boolean
  refreshing: boolean
  historyDetailLoadingId: string
  loading: boolean
  assessing: boolean
  refreshingQuiz: boolean
  error: string
}

let refreshPromise: Promise<void> | null = null
const resourceHistoryDetailPromises = new Map<string, Promise<GenerationHistoryItem>>()
const ACTIVE_TASKS_STORAGE_KEY = 'a3_learning_has_active_tasks'
const ACTIVE_ASSESSMENT_STORAGE_KEY = 'a3_learning_has_assessment_result'
const PROFILE_RESULT_STORAGE_KEY = 'a3_learning_has_profile_result'

function hasActiveTasks() {
  return localStorage.getItem(ACTIVE_TASKS_STORAGE_KEY) === 'true'
}

function hasAssessmentResult() {
  return localStorage.getItem(ACTIVE_ASSESSMENT_STORAGE_KEY) === 'true'
}

function hasProfileResult() {
  return localStorage.getItem(PROFILE_RESULT_STORAGE_KEY) === 'true'
}

function markActiveTasks() {
  localStorage.setItem(ACTIVE_TASKS_STORAGE_KEY, 'true')
}

function markAssessmentResult() {
  localStorage.setItem(ACTIVE_ASSESSMENT_STORAGE_KEY, 'true')
}

function markProfileResult() {
  localStorage.setItem(PROFILE_RESULT_STORAGE_KEY, 'true')
}

export const useLearningStore = defineStore('learning', {
  state: (): LearningState => ({
    health: null,
    profile: null,
    resources: [],
    resourceHistory: [],
    resourceHistoryDetails: {},
    planSummary: null,
    traces: [],
    path: null,
    pathHistory: [],
    report: null,
    assessmentHistory: [],
    lastProfileUpdate: null,
    progress: 0,
    currentStep: '等待生成',
    initialized: false,
    refreshing: false,
    historyDetailLoadingId: '',
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
        const [health, profile, resources, path, report] = await Promise.all([
          api.health(),
          api.profile(),
          api.resources(),
          api.path(),
          api.assessment()
        ])
        this.health = health
        this.profile = hasProfileResult() ? profile : null
        this.resources = hasActiveTasks() ? resources : []
        this.path = hasActiveTasks() ? path : null
        this.report = hasAssessmentResult() ? report : null
        await this.refreshHistories()
        this.initialized = true
      } catch (error) {
        this.error = friendlyErrorMessage(error, '初始化学习数据失败')
      } finally {
        this.refreshing = false
      }
    },
    async sendProfileMessage(message: string) {
      try {
        this.error = ''
        const previousVersion = this.profile?.version
        const data = await api.profileChatAndGenerate(message)
        this.lastProfileUpdate = data
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
        markProfileResult()
        markActiveTasks()
        if (data.resources && data.resources.length > 0) {
          this.resources = data.resources
        }
        if (data.learning_path) {
          this.path = data.learning_path
        }
        await this.refreshHistories()
      } catch (error) {
        this.error = friendlyErrorMessage(error, '画像更新失败')
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
        markActiveTasks()
        this.path = await api.path()
        await this.refreshHistories()
        this.initialized = true
      } catch (error) {
        this.error = friendlyErrorMessage(error, '资源生成失败')
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
        let syncFailures = 0

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
            syncFailures = 0
            if (latest.status === 'completed') {
              cleanup()
              resolve()
            }
            if (latest.status === 'failed') {
              cleanup()
              reject(new Error('资源生成任务失败，请调整任务描述后重试。'))
            }
          } catch {
            syncFailures += 1
            if (syncFailures >= 6) {
              cleanup()
              reject(new Error('生成进度同步中断，可能是后端服务暂时不可用。已停止等待，请检查服务后重试。'))
            }
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

        const eventTypes = ['job_queued', 'job_started', 'agent_completed', 'resource_ready', 'job_fallback', 'trace_completed', 'job_completed', 'job_failed', 'completed', 'failed']
        for (const type of eventTypes) {
          source.addEventListener(type, () => {
            scheduleSync()
          })
        }

        source.onerror = () => {
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
        markActiveTasks()
        markAssessmentResult()
        markProfileResult()
        this.profile = await api.profile()
        this.path = this.report.adjusted_path
        await this.refreshHistories()
      } catch (error) {
        this.error = friendlyErrorMessage(error, '评估提交失败')
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
        await this.refreshHistories()
      } catch (error) {
        this.error = friendlyErrorMessage(error, '练习题刷新失败')
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
        markActiveTasks()
        await this.refreshHistories()
      } catch (error) {
        this.error = friendlyErrorMessage(error, '资源反馈保存失败')
      }
    },
    async loadResourceHistoryDetail(jobId: string) {
      if (this.resourceHistoryDetails[jobId]) return this.resourceHistoryDetails[jobId]
      let promise = resourceHistoryDetailPromises.get(jobId)
      if (!promise) {
        promise = api.resourceHistoryDetail(jobId)
        resourceHistoryDetailPromises.set(jobId, promise)
      }
      this.historyDetailLoadingId = jobId
      try {
        const detail = await promise
        this.resourceHistoryDetails = {
          ...this.resourceHistoryDetails,
          [jobId]: detail
        }
        return detail
      } catch (error) {
        this.error = friendlyErrorMessage(error, '历史资料包加载失败')
        throw error
      } finally {
        resourceHistoryDetailPromises.delete(jobId)
        if (this.historyDetailLoadingId === jobId) this.historyDetailLoadingId = ''
      }
    },
    async refreshHistories() {
      const [resourceHistory, pathHistory, assessmentHistory] = await Promise.all([
        api.resourceHistory(),
        api.pathHistory(),
        api.assessmentHistory()
      ])
      this.resourceHistory = hasActiveTasks() ? resourceHistory : resourceHistory.map(item => ({ ...item, is_current: false }))
      const historyIds = new Set(this.resourceHistory.map(item => item.id))
      this.resourceHistoryDetails = Object.fromEntries(
        Object.entries(this.resourceHistoryDetails).filter(([id]) => historyIds.has(id))
      )
      this.pathHistory = hasActiveTasks() ? pathHistory : []
      this.assessmentHistory = hasAssessmentResult() ? assessmentHistory : []
    }
  }
})

export function friendlyErrorMessage(error: unknown, fallback = '操作失败') {
  const raw = error instanceof Error ? error.message : String(error || '')
  const normalized = raw.toLowerCase()
  if (
    normalized.includes('failed to fetch') ||
    normalized.includes('networkerror') ||
    normalized.includes('load failed') ||
    normalized.includes('connection') ||
    normalized.includes('fetch')
  ) {
    return `${fallback}：无法连接后端服务。请确认后端已启动；当前页面仍可查看已有数据或演示兜底内容。`
  }
  if (normalized.includes('http 500') || normalized.includes('internal server error')) {
    return `${fallback}：后端处理异常。请稍后重试，或先使用页面中的兜底/示例内容继续演示。`
  }
  if (normalized.includes('http 404')) {
    return `${fallback}：暂未找到对应数据，可能还没有生成内容。请先完成资源生成后再试。`
  }
  if (!raw) return `${fallback}，请稍后重试。`
  return `${fallback}：${raw}`
}

export function isDemoAssessmentReport(report: AssessmentReport | null | undefined) {
  if (!report) return false
  const text = [
    report.feedback,
    ...(report.strengths || []),
    report.adjusted_path?.adjustment_reason || ''
  ].join(' ')
  return report.mastery_delta === 0 && /暂无正式测评|完成练习提交后|初始化演示测评报告/.test(text)
}

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
