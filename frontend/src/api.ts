const API_BASE = import.meta.env.VITE_API_BASE || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options?.headers || {}) },
    ...options
  })
  const body = await response.json()
  if (!body.ok) throw new Error(body.error?.message || '接口请求失败')
  return body.data as T
}

export const api = {
  health: () => request('/api/health'),
  profile: () => request('/api/profile/current'),
  profileChat: (message: string) => request('/api/profile/chat', { method: 'POST', body: JSON.stringify({ message }) }),
  generate: (payload: unknown) => request('/api/resources/generate', { method: 'POST', body: JSON.stringify(payload) }),
  resources: () => request('/api/resources'),
  path: () => request('/api/learning-path/current'),
  generatePath: () => request('/api/learning-path/generate', { method: 'POST' }),
  tutor: (question: string, resource_id?: string) => request('/api/tutor/chat', { method: 'POST', body: JSON.stringify({ question, resource_id }) }),
  submitQuiz: (answers: string[], resource_id?: string) => request('/api/quiz/submit', { method: 'POST', body: JSON.stringify({ answers, resource_id }) }),
  assessment: () => request('/api/assessment/report')
}
