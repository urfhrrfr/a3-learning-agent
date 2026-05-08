import { defineStore } from 'pinia'
import { api } from './api'
import type { AgentTrace, AssessmentReport, LearningPath, Profile, Resource } from './types'

export const useLearningStore = defineStore('learning', {
  state: () => ({
    profile: null as Profile | null,
    resources: [] as Resource[],
    traces: [] as AgentTrace[],
    path: null as LearningPath | null,
    report: null as AssessmentReport | null,
    progress: 0,
    loading: false,
    error: ''
  }),
  actions: {
    async refresh() {
      try {
        this.profile = await api.profile() as Profile
        this.resources = await api.resources() as Resource[]
        this.path = await api.path() as LearningPath
        this.report = await api.assessment() as AssessmentReport | null
      } catch (error) {
        this.error = error instanceof Error ? error.message : String(error)
      }
    },
    async sendProfileMessage(message: string) {
      const data = await api.profileChat(message) as { profile: Profile }
      this.profile = data.profile
    },
    async generateResources() {
      this.loading = true
      this.progress = 8
      const timer = window.setInterval(() => {
        if (this.progress < 88) this.progress += 7
      }, 260)
      try {
        const job = await api.generate({
          course: '人工智能导论',
          chapter: this.profile?.current_chapter || '机器学习基础',
          goal: this.profile?.learning_goal || '掌握核心概念',
          pain_points: this.profile?.weak_points || []
        }) as { progress: number; traces: AgentTrace[]; resources: Resource[] }
        this.progress = job.progress
        this.traces = job.traces
        this.resources = job.resources
        this.path = await api.path() as LearningPath
      } finally {
        window.clearInterval(timer)
        this.loading = false
      }
    },
    async submitAssessment(answers: string[]) {
      this.report = await api.submitQuiz(answers) as AssessmentReport
      this.profile = await api.profile() as Profile
      this.path = this.report.adjusted_path
    }
  }
})
