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
  TutorMessage,
  TutorExercise,
  TutorExerciseResult,
  TutorResponse
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE || ''
const USER_ID_STORAGE_KEY = 'a3_learning_user_id'

function userId() {
  let existing = localStorage.getItem(USER_ID_STORAGE_KEY)
  if (!existing) {
    const randomId = crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}_${Math.random().toString(16).slice(2)}`
    existing = `anon_${randomId}`
    localStorage.setItem(USER_ID_STORAGE_KEY, existing)
  }
  return existing
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', 'X-User-Id': userId(), ...(options?.headers || {}) },
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
  profileVersions: () => request<Profile[]>('/api/profile/versions'),
  rollbackProfile: (version: number) =>
    request<{ profile: Profile; learning_path: LearningPath | null }>(`/api/profile/rollback/${version}`, { method: 'POST' }),
  profileDimensions: () => request<ProfileDimension[]>('/api/profile/dimensions'),
  profileChangeLog: () => request<ProfileChangeLog[]>('/api/profile/change-log'),
  profileChat: (message: string) =>
    request<ProfileChatResponse>('/api/profile/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  profileChatAndGenerate: (message: string) =>
    request<ProfileChatResponse & { resources: Resource[]; learning_path: LearningPath | null; message: string }>('/api/profile/chat-and-generate', { 
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
  tutor: (question: string, resource_id?: string | null, history: TutorMessage[] = []) =>
    request<TutorResponse>('/api/tutor/chat', { method: 'POST', body: JSON.stringify({ question, resource_id, history }) }),
  confirmWeakPoint: (topic: string, evidence = '') =>
    request<{ profile: Profile; profile_updated: boolean }>('/api/profile/weak-points/confirm', {
      method: 'POST',
      body: JSON.stringify({ topic, evidence })
    }),
  submitTutorExercise: (exercise: TutorExercise, answer: string) =>
    request<TutorExerciseResult>('/api/tutor/exercise/submit', {
      method: 'POST',
      body: JSON.stringify({ exercise, answer })
    }),
  refreshQuiz: () => request<Resource>('/api/quiz/refresh', { method: 'POST' }),
  submitQuiz: (answers: string[], resource_id?: string | null) =>
    request<AssessmentReport>('/api/quiz/submit', { method: 'POST', body: JSON.stringify({ answers, resource_id }) }),
  assessment: () => request<AssessmentReport | null>('/api/assessment/report')
}
