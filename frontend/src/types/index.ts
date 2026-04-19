export type Verdict = 'PASS' | 'NO_IMAGE' | 'ERROR'

export type FieldStatus = 'match' | 'no_signal' | 'conflict' | 'unverified'

export type FailReason =
  | 'no_candidates'
  | 'quality_failed'
  | 'identity_unverified'
  | 'conflicting_fields'
  | 'producer_mismatch'
  | 'appellation_mismatch'
  | 'vineyard_or_cuvee_mismatch'
  | 'classification_conflict'
  | 'vintage_mismatch'
  | 'unreadable_core_identity'
  | 'pipeline_not_implemented'

export type AnalyzerMode = 'strict' | 'balanced'
export type PipelineName = 'voter' | 'paddle_qwen'

export interface AnalyzeRequest {
  wine_name: string
  vintage: string
  format: string
  region: string
  analyzer_mode: AnalyzerMode
}

export interface ModuleVote {
  module: string
  available: boolean
  passed: boolean
  confidence: number
  weight: number
  reason?: string
}

export interface ParsedIdentity {
  producer: string | null
  appellation: string | null
  vineyard_or_cuvee: string | null
  classification: string | null
  vintage: string | null
  format: string | null
  region: string | null
  raw_wine_name: string
  normalized_wine_name: string
}

export interface FieldMatch {
  target: string | null
  extracted: string | null
  status: FieldStatus
  confidence: number
}

export interface ScoreBreakdown {
  producer: number
  appellation: number
  vineyard_or_cuvee: number
  classification: number
  vintage: number
  ocr_clarity: number
  image_quality: number
  source_trust: number
}

export interface CandidateSummary {
  candidate_id: string
  source_domain: string
  confidence: number
  should_fail: boolean
  fail_reason: string | null
  image_url: string
  module_votes?: ModuleVote[]
}

export interface DebugPayload {
  queries: string[]
  candidates_considered: number
  hard_fail_reasons: string[]
  ocr_snippets: string[]
  score_breakdown: ScoreBreakdown
  notes: string[]
  candidate_summaries: CandidateSummary[]
  module_votes: ModuleVote[]
}

export interface AnalyzeResponse {
  input: AnalyzeRequest
  parsed_identity: ParsedIdentity
  verdict: Verdict
  confidence: number
  selected_image_url: string | null
  selected_source_page: string | null
  reason: string
  fail_reason: FailReason | null
  field_matches: Record<string, FieldMatch>
  debug: DebugPayload
}

export interface BatchAnalyzeResponse {
  results: AnalyzeResponse[]
  summary: {
    total: number
    verdict_counts: Record<string, number>
  }
}

export interface TestSku {
  wine_name: string
  vintage: string
  format: string
  region: string
  difficulty: string
}
