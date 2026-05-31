import type {
  ApiResponse,
  AuthSession,
  AuthStatus,
  AuthUser,
  AssessmentReport,
  AssessmentHistoryItem,
  GenerateRequest,
  GenerationJob,
  GenerationHistoryItem,
  GenerationHistorySummary,
  HealthStatus,
  LearningPath,
  LearningPathHistoryItem,
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

const API_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
const AUTH_TOKEN_STORAGE_KEY = 'a3_learning_auth_token'

export function authToken() {
  return localStorage.getItem(AUTH_TOKEN_STORAGE_KEY) || ''
}

export function setAuthToken(token: string) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token)
  } else {
    localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY)
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = authToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...(options?.headers as Record<string, string> || {}) }
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${API_BASE}${path}`, {
    headers,
    ...options
  })

  let body: ApiResponse<T> | { detail?: string }
  try {
    body = await response.json() as ApiResponse<T> | { detail?: string }
  } catch {
    throw new Error(`HTTP ${response.status}`)
  }
  if (!response.ok) {
    throw new Error('detail' in body && body.detail ? body.detail : `HTTP ${response.status}`)
  }
  if (!('ok' in body) || !body.ok) {
    throw new Error('error' in body ? body.error?.message || '接口请求失败' : '接口请求失败')
  }

  return body.data as T
}

export const api = {
  authStatus: () => request<AuthStatus>('/api/auth/status'),
  register: (username: string, password: string, display_name = '') =>
    request<AuthSession>('/api/auth/register', { method: 'POST', body: JSON.stringify({ username, password, display_name }) }),
  login: (username: string, password: string) =>
    request<AuthSession>('/api/auth/login', { method: 'POST', body: JSON.stringify({ username, password }) }),
  me: () => request<{ user: AuthUser } & AuthStatus>('/api/auth/me'),
  health: () => request<HealthStatus>('/api/health'),
  profile: () => request<Profile>('/api/profile/current'),
  clearProfile: () =>
    request<{ deleted: boolean; profile: Profile; learning_path: LearningPath | null }>('/api/profile/current', { method: 'DELETE' }),
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
  generationEventsUrl: (job_id: string) => `${API_BASE}/api/jobs/${job_id}/events?access_token=${encodeURIComponent(authToken())}`,
  job: (job_id: string) => request<GenerationJob>(`/api/jobs/${job_id}`),
  resources: () => request<Resource[]>('/api/resources'),
  resourceHistory: () => request<GenerationHistorySummary[]>('/api/resources/history'),
  resourceHistoryDetail: (job_id: string) => request<GenerationHistoryItem>(`/api/resources/history/${job_id}`),
  deleteResourceHistory: (job_id: string) =>
    request<{ deleted: boolean; job_id: string }>(`/api/resources/history/${job_id}`, { method: 'DELETE' }),
  resource: (resource_id: string) => request<Resource>(`/api/resources/${resource_id}`),
  resourceFeedback: (resource_id: string, action: Resource['user_feedback']) =>
    request<{ resource: Resource; learning_path: LearningPath | null }>('/api/resources/feedback', {
      method: 'POST',
      body: JSON.stringify({ resource_id, action })
    }),
  path: () => request<LearningPath | null>('/api/learning-path/current'),
  pathHistory: () => request<LearningPathHistoryItem[]>('/api/learning-path/history'),
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
  assessment: () => request<AssessmentReport | null>('/api/assessment/report'),
  assessmentHistory: () => request<AssessmentHistoryItem[]>('/api/assessment/history')
}
