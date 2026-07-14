export type CheckState = "PASS" | "FAIL" | "NOT_RUN";
export type GuardrailCheckName = "format" | "completeness" | "grounding" | "direction";
export type Mode = "recorded" | "live";
export type RiskBucket = "High" | "Medium" | "Low" | string;
export type AttackPreset = "direction_flip" | "unlisted_feature" | "template_corruption";
export type WorkflowStatus = "unreviewed" | "in_review" | "needs_follow_up" | "review_complete";
export type WorkflowDisposition = "suspicious" | "not_suspicious" | "inconclusive";

export interface ApiErrorShape {
  code?: string;
  message?: string;
  detail?: string | { code?: string; message?: string; details?: unknown };
  details?: unknown;
}

export interface HealthResponse {
  status?: string;
  ready?: boolean;
  application_ready?: boolean;
  artifact_ready?: boolean;
  artifacts_ready?: boolean;
  frontend_build?: string;
  build_version?: string;
  frontend_build_version?: string;
  ollama_available?: boolean | null;
  ollama_status?: "available" | "unavailable" | "checking" | string;
  ollama?: {
    available?: boolean | null;
    status?: "available" | "unavailable" | "checking" | string;
    model?: string;
  };
  workflow_status?: "ready" | "unavailable" | string;
}

export interface ProvenanceEntry {
  run_id: string;
  manifest_sha256: string;
  group?: string;
  source_run_ids?: string[];
  source_code_compatible?: boolean;
}

export interface ProvenanceResponse {
  detector?: ProvenanceEntry;
  g4?: ProvenanceEntry;
  g5?: ProvenanceEntry;
  results?: ProvenanceEntry;
  artifacts?: Record<string, ProvenanceEntry>;
  source_chain_valid?: boolean;
  source_code_compatible?: boolean;
  verified_at?: string;
}

export interface DemoScenario {
  id?: string;
  key?: string;
  scenario?: string;
  case_id: number;
  title?: string;
  label?: string;
  description: string;
  kind?: "faithful" | "error" | "attack" | string;
}

export interface DemoScenariosResponse {
  scenarios?: DemoScenario[];
  faithful_case_id?: number;
  error_or_uncertainty_case_id?: number;
  attack_case_id?: number;
}

export interface ReasonCode {
  feature: string;
  direction: "increases_risk" | "decreases_risk" | string;
  rank: number;
  shap_value?: number | null;
  reason?: string;
}

export type GuardrailChecks = Record<GuardrailCheckName, CheckState>;

export interface NarrativeView {
  mode?: "recorded" | "live_demo" | string;
  reported?: boolean;
  arm?: "strict" | "simple" | string;
  raw_text?: string | null;
  candidate_text?: string | null;
  final_text: string;
  checks: Partial<GuardrailChecks>;
  check_reasons?: Partial<Record<GuardrailCheckName, string | null>>;
  fallback: boolean;
  fallback_reason?: string | null;
  latency_seconds?: number | null;
  llm_transport_unavailable?: boolean;
}

export interface CaseSummary {
  case_id: number;
  risk_bucket: RiskBucket;
  score: number;
  pred?: number;
  detector_flagged?: boolean;
  top_reason?: ReasonCode | string | null;
  recorded_narrative_status?: "passed" | "fallback" | "unavailable" | string;
  recorded_fallback?: boolean;
}

export interface CasesResponse {
  items?: CaseSummary[];
  cases?: CaseSummary[];
  total: number;
  offset?: number;
  limit?: number;
}

export interface CaseDetail extends CaseSummary {
  threshold?: number | null;
  reason_codes?: ReasonCode[];
  codes?: ReasonCode[];
  recorded_narrative?: NarrativeView | null;
  narrative?: NarrativeView | null;
  source_run_ids?: string[];
  data_sent_to_llm?: {
    payload?: string;
    included?: string[];
    excluded?: string[];
  };
  provenance?: ProvenanceResponse;
}

export interface LiveNarrativeResponse extends NarrativeView {
  mode: "live_demo";
  reported: false;
  case_id: number;
}

export interface GuardrailDemoResponse {
  mode?: "guardrail_demo" | string;
  reported?: false;
  case_id: number;
  preset: AttackPreset;
  original_text: string;
  tampered_text: string;
  checks: Partial<GuardrailChecks>;
  check_reasons?: Partial<Record<GuardrailCheckName, string | null>>;
  failure_reasons?: Partial<Record<GuardrailCheckName, string | null>>;
  fallback: boolean;
  fallback_reason?: string | null;
  final_text: string;
  validator?: string;
}

export interface DetectorResult {
  group: string;
  label?: string;
  seeds?: number;
  n_seeds?: number;
  auc_pr_mean?: number;
  auc_pr_std?: number;
  roc_auc_mean?: number;
  roc_auc_std?: number;
  precision_mean?: number;
  precision_std?: number;
  recall_mean?: number;
  recall_std?: number;
  f1_mean?: number;
  f1_std?: number;
  precision_at_100_mean?: number;
  recall_at_100_mean?: number;
  false_positives_mean?: number;
  false_negatives_mean?: number;
  inference_time_seconds_mean?: number;
  [key: string]: string | number | undefined;
}

export interface RateEstimate {
  rate: number;
  n: number;
  ci_low?: number;
  ci_high?: number;
  by_construction?: boolean;
}

export interface ExplanationArmResult {
  arm: "strict" | "simple" | string;
  format?: RateEstimate;
  completeness?: RateEstimate;
  grounding?: RateEstimate;
  direction?: RateEstimate;
  any_detected_violation?: RateEstimate;
  fallback?: RateEstimate;
  mean_latency_seconds?: number;
  llm_transport_unavailable_count?: number;
}

export interface ResultsResponse {
  detector_results: DetectorResult[];
  explanation_results?: {
    explained_cases?: number;
    strict?: ExplanationArmResult;
    simple?: ExplanationArmResult;
    arms?: ExplanationArmResult[];
    g4_run_id?: string;
    g5_run_id?: string;
  } | ExplanationArmResult[];
  figures?: Array<{
    id: string;
    title?: string;
    caption?: string;
  }>;
  provenance?: {
    results_manifest_sha256?: string;
    source_run_ids?: string[];
  };
}

export interface WorkflowRecord {
  case_id: number;
  status: WorkflowStatus;
  disposition: WorkflowDisposition | null;
  note: string;
  revision: number;
  created_at: string | null;
  updated_at: string | null;
  evidence_compatible: boolean;
  activity_count: number;
}

export interface WorkflowListResponse {
  items: WorkflowRecord[];
  total: number;
}

export interface WorkflowSummaryResponse {
  total: number;
  counts: Record<WorkflowStatus, number>;
  recorded_fallback: number;
  evidence_fingerprint: string;
}

export interface WorkflowActivityEvent {
  id: number;
  event_type: string;
  from_status: WorkflowStatus | null;
  to_status: WorkflowStatus;
  disposition: WorkflowDisposition | null;
  note_changed: boolean;
  revision: number;
  created_at: string;
}

export interface WorkflowActivityResponse {
  items: WorkflowActivityEvent[];
}

export interface WorkflowUpdate {
  revision: number;
  status: WorkflowStatus;
  disposition: WorkflowDisposition | null;
  note: string;
}
