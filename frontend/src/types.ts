export interface Profile {
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

export interface AgentTrace {
  id: string
  agent: string
  status: string
  input_summary: string
  output_summary: string
  source_refs: string[]
  confidence: number
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
  review_status: string
  created_by_agents: string[]
}

export interface LearningPath {
  id: string
  mastery: number
  adjustment_reason: string
  steps: Array<{
    id: string
    title: string
    objective: string
    recommended_resource_ids: string[]
    reason: string
    estimated_minutes: number
    status: string
  }>
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
}
