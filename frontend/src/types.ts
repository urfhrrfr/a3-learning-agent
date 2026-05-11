export interface ApiError {
  code?: string
  message: string
  details?: Record<string, unknown>
}

export interface ApiResponse<T> {
  ok: boolean
  data: T
  error: ApiError | null
}

export interface HealthStatus {
  status: string
  mock_llm: boolean
  course: string
}

export interface Profile {
  id: string
  major: string
  education_level: string
  course: string
  current_chapter: string
  knowledge_base: string[]
  learning_goal: string
  cognitive_style: string
  preferred_modalities: string[]
  time_budget: string
  weak_points: string[]
  mistake_patterns: string[]
  interests: string[]
  mastery: number
  version: number
  updated_at: string
}

export interface ProfileDimension {
  key: string
  label: string
  description: string
  value_type: string
  update_rule: string
}

export interface ProfileChangeLog {
  profile_id: string
  version: number
  trigger_message: string
  extracted: Record<string, unknown>
  changed_fields: Record<string, { before: unknown; after: unknown }>
  updated_at: string
}

export interface AgentTrace {
  id: string
  job_id: string
  agent: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  input_summary: string
  output_summary: string
  collaboration_stage: string
  boundary: string
  depends_on: string[]
  source_refs: string[]
  warnings: string[]
  confidence: number
  retry_count: number
  llm_provider: string
  arbitration_note: string
  review_conclusion: string
  started_at: string
  finished_at: string | null
}

export interface Resource {
  id: string
  type: string
  title: string
  content_format: 'markdown' | 'mermaid' | 'json' | 'code'
  content: string
  source_refs: string[]
  difficulty: string
  target_profile: string[]
  review_status: 'passed' | 'needs_revision' | 'blocked'
  review_reason: string
  audit_reason: string
  review_notes: string[]
  review_confidence: number
  user_feedback: 'neutral' | 'favorite' | 'hidden'
  created_by_agents: string[]
  created_at: string
}

export interface GenerateRequest {
  course?: string
  chapter?: string
  goal?: string
  pain_points?: string[]
  resource_types?: string[]
}

export interface GenerationJob {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  current_step: string
  request: Required<GenerateRequest>
  traces: AgentTrace[]
  resources: Resource[]
  events: Array<{
    type: string
    payload: Record<string, unknown>
    created_at: string
  }>
  created_at: string
  completed_at: string | null
}

export interface GenerationEvent {
  type: string
  payload: Record<string, unknown>
  created_at: string
}

export interface LearningPathStep {
  id: string
  title: string
  objective: string
  recommended_resource_ids: string[]
  reason: string
  estimated_minutes: number
  status: 'todo' | 'doing' | 'done'
}

export interface LearningPath {
  id: string
  profile_version: number
  mastery: number
  adjustment_reason: string
  steps: LearningPathStep[]
  updated_at: string
}

export interface ProfileChatResponse {
  profile: Profile
  extracted: Record<string, unknown>
  suggested_next_question: string
  version_change: string
}

export interface TutorResponse {
  answer: string
  source_refs: string[]
  mermaid: string
  llm_provider?: string
  used_fallback?: boolean
  fallback_reason?: string
}

export interface AssessmentReport {
  id: string
  score: number
  mastery_delta: number
  strengths: string[]
  weak_points: string[]
  mistake_patterns: string[]
  feedback: string
  adjusted_path: LearningPath
  created_at: string
}
