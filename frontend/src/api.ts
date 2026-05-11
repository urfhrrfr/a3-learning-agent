import type {
  ApiResponse,
  AssessmentReport,
  GenerateRequest,
  GenerationJob,
  HealthStatus,
  LearningPath,
  Profile,
  ProfileChangeLog,
  ProfileChatResponse,
  ProfileDimension,
  Resource,
  TutorResponse
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options
  })

  const body = await response.json() as ApiResponse<T> | { detail?: string }
  if (!response.ok) {
    throw new Error('detail' in body && body.detail ? body.detail : `HTTP ${response.status}`)
  }
  if (!('ok' in body) || !body.ok) {
    throw new Error('error' in body ? body.error?.message || '接口请求失败' : '接口请求失败')
  }

  return body.data as T
}

export const api = {
  health: () => request<HealthStatus>('/api/health'),
  profile: () => request<Profile>('/api/profile/current'),
  profileDimensions: () => request<ProfileDimension[]>('/api/profile/dimensions'),
  profileChangeLog: () => request<ProfileChangeLog[]>('/api/profile/change-log'),
  profileChat: (message: string) =>
    request<ProfileChatResponse>('/api/profile/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  profileChatAndGenerate: (message: string) =>
    request<{ profile: Profile; resources: Resource[]; learning_path: LearningPath | null; message: string }>('/api/profile/chat-and-generate', { 
      method: 'POST', 
      body: JSON.stringify({ message, regenerate_resources: true }) 
    }),
  generate: (payload: GenerateRequest) =>
    request<GenerationJob>('/api/resources/generate', { method: 'POST', body: JSON.stringify(payload) }),
  generateBackground: (payload: GenerateRequest) =>
    request<GenerationJob>('/api/resources/generate/background', { method: 'POST', body: JSON.stringify(payload) }),
  generationEventsUrl: (job_id: string) => `${API_BASE}/api/jobs/${job_id}/events`,
  job: (job_id: string) => request<GenerationJob>(`/api/jobs/${job_id}`),
  resources: () => request<Resource[]>('/api/resources'),
  resource: (resource_id: string) => request<Resource>(`/api/resources/${resource_id}`),
  resourceFeedback: (resource_id: string, action: Resource['user_feedback']) =>
    request<{ resource: Resource; learning_path: LearningPath | null }>('/api/resources/feedback', {
      method: 'POST',
      body: JSON.stringify({ resource_id, action })
    }),
  path: () => request<LearningPath>('/api/learning-path/current'),
  generatePath: () => request<LearningPath>('/api/learning-path/generate', { method: 'POST' }),
  tutor: (question: string, resource_id?: string | null) =>
    request<TutorResponse>('/api/tutor/chat', { method: 'POST', body: JSON.stringify({ question, resource_id }) }),
  refreshQuiz: () => request<Resource>('/api/quiz/refresh', { method: 'POST' }),
  submitQuiz: (answers: string[], resource_id?: string | null) =>
    request<AssessmentReport>('/api/quiz/submit', { method: 'POST', body: JSON.stringify({ answers, resource_id }) }),
  assessment: () => request<AssessmentReport | null>('/api/assessment/report')
}
