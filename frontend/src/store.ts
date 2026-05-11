import { defineStore } from 'pinia'
import { api } from './api'
import type { AgentTrace, AssessmentReport, LearningPath, Profile, Resource } from './types'

interface LearningState {
  profile: Profile | null
  resources: Resource[]
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
        const data = await api.profileChatAndGenerate(message)
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
    async generateResources(resourceTypes: string[] | Event = []) {
      const requestedTypes = Array.isArray(resourceTypes) ? resourceTypes : []
      this.loading = true
      this.progress = 0
      this.currentStep = '创建生成任务'
      this.traces = []
      try {
        this.error = ''
        const job = await api.generateBackground({
          course: '人工智能导论',
          chapter: this.profile?.current_chapter || '机器学习基础',
          goal: this.profile?.learning_goal || '掌握核心概念',
          pain_points: this.profile?.weak_points || [],
          resource_types: requestedTypes
        })
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
