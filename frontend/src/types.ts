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
  llm_provider: string
  cache: {
    enabled: boolean
    available: boolean
    reason: string
  }
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

export interface ProfileFusionMeta {
  source: 'llm' | 'fallback' | string
  changed_fields: string[]
  conflicts: unknown[]
  merge_reasoning: string
  confidence: number
  validation?: {
    is_valid: boolean
    confidence_score: number
    warnings: string[]
    requires_confirmation: boolean
  }
}

export interface ProfileChangeLog {
  profile_id: string
  version: number
  trigger_message: string
  extracted: Record<string, unknown>
  conflicts: string[]
  fusion_reason: string
  fusion_meta?: ProfileFusionMeta
  extraction_confidence?: number
  extraction_source?: string
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

export interface EvidenceSource {
  id: string
  text: string
  relevance_score: number
  reason: string
}

export interface Resource {
  id: string
  type: string
  title: string
  content_format: 'markdown' | 'mermaid' | 'json' | 'code'
  content: string
  evidence_sources?: EvidenceSource[]
  source_refs: string[]
  difficulty: string
  target_profile: string[]
  personalized_reason?: string
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

export interface PlanDecision {
  resource_type: string
  priority: number
  difficulty: string
  reason: string
}

export interface PlanSummary {
  total_estimated_time: number
  decisions: PlanDecision[]
}

export interface GenerationJob {
  id: string
  status: 'queued' | 'running' | 'completed' | 'failed'
  progress: number
  current_step: string
  request: Required<GenerateRequest>
  plan_summary: PlanSummary
  traces: AgentTrace[]
  resources: Resource[]
  events: Array<{
    type: string
    payload: Record<string, unknown>
    created_at: string
  }>
  fallback_reason?: string
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
  confidence?: number
  source?: string
  reasoning?: string
  conflicts?: string[]
  fusion_reason?: string
  fusion_meta?: ProfileFusionMeta
  changed_fields?: Record<string, { before: unknown; after: unknown }>
  suggested_next_question?: string
  suggested_next_questions?: string[]
  version_change?: string
}

export interface TutorResponse {
  answer: string
  source_refs: string[]
  mermaid: string
  llm_provider?: string
  used_fallback?: boolean
  fallback_reason?: string
  profile_suggestion?: {
    type: 'weak_point' | string
    topic: string
    confidence: number
    already_exists?: boolean
    message: string
  } | null
  profile_snapshot?: Profile
  personalization?: {
    preferred_mode: string
    preferred_modalities: string[]
    weak_points: string[]
  }
  cited_resources?: Array<{
    id: string
    title: string
    type: string
    difficulty: string
  }>
  next_step?: TutorNextStep
  exercise?: TutorExercise
}

export interface TutorMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface TutorNextStep {
  title: string
  objective: string
  reason: string
  estimated_minutes: number
  resource_ids: string[]
}

export interface TutorExercise {
  id: string
  topic: string
  type: string
  prompt: string
  expected_keywords: string[]
  hint: string
  resource_id?: string | null
}

export interface TutorExerciseResult {
  score: number
  mastery_delta: number
  weak_points?: string[]
  mistake_patterns?: string[]
  feedback: string
  matched_keywords: string[]
  adjusted_path?: LearningPath
  profile: Profile
  learning_path: LearningPath
  next_step: TutorNextStep | null
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
