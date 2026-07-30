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

export interface OperationalProvenanceResponse {
  run_id: string;
  group: "s0" | string;
  seed?: number;
  synthetic: true;
  manifest_sha256: string;
  dataset_sha256?: string | null;
  config_sha256?: string | null;
  threshold?: number;
  feature_names?: string[];
  artifacts?: Record<string, { sha256: string; source?: string }>;
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
  display_label?: string;
  label?: string;
  direction: "increases_risk" | "decreases_risk" | string;
  rank: number;
  shap_value?: number | null;
  reason?: string;
  value_bucket?: string | null;
}

export interface TransactionContext {
  amount: number;
  elapsed_seconds?: number;
  timestamp?: string;
  transaction_time?: string;
  transaction_id?: string;
  currency?: null;
  time_basis?: "seconds_since_dataset_start" | string;
  source?: "hash_verified_dataset_row" | string;
  [key: string]: unknown;
}

export type GuardrailChecks = Record<GuardrailCheckName, CheckState>;

export interface NarrativeView {
  mode?: "recorded" | "live_demo" | string;
  reported?: boolean;
  arm?: "strict" | "simple" | string;
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
  transaction_id?: string;
  risk_bucket: RiskBucket;
  score_rank?: number;
  rank?: number;
  flagged_total?: number;
  pred?: number;
  detector_flagged?: boolean;
  top_reason?: ReasonCode | string | null;
  top_signal?: ReasonCode | string | null;
  readable_top_signal?: string;
  top_reasons?: ReasonCode[];
  recorded_narrative_status?: "passed" | "fallback" | "unavailable" | string;
  recorded_fallback?: boolean;
  explanation_delivery?: "guarded_llm" | "deterministic_fallback" | "unavailable" | string;
  review_state?: WorkflowStatus | string;
  transaction_context?: TransactionContext;
  timestamp?: string;
  amount?: number;
  customer_activity?: string | number | null;
  terminal_context?: string | number | null;
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
  frozen_threshold?: number | null;
  reason_codes?: ReasonCode[];
  codes?: ReasonCode[];
  raw_reason_codes?: ReasonCode[];
  semantic_reason_codes?: ReasonCode[];
  shap_reason_codes?: ReasonCode[];
  recorded_narrative?: NarrativeView | null;
  narrative?: NarrativeView | null;
  deterministic_brief?: string | NarrativeView | null;
  guarded_llm_brief?: string | NarrativeView | null;
  llm_brief?: string | NarrativeView | null;
  explanation_comparison?: {
    raw_reason_codes?: ReasonCode[];
    deterministic_brief?: string | NarrativeView | null;
    guarded_llm_brief?: string | NarrativeView | null;
    llm_candidate?: Record<string, unknown> | null;
    llm_brief?: string | NarrativeView | null;
    delivered_brief?: string | NarrativeView | null;
    validation?: OperationalValidation | null;
    minimized_payload?: string | Record<string, unknown> | null;
  };
  source_run_ids?: string[];
  data_sent_to_llm?: {
    payload?: string | Record<string, unknown>;
    included?: string[];
    excluded?: string[];
  };
  minimized_payload?: string | Record<string, unknown> | null;
  validation?: OperationalValidation | null;
  fallback_reason?: string | null;
  synthetic?: boolean;
  provenance?: ProvenanceResponse;
}

export interface OperationalValidation {
  passed?: boolean;
  fallback?: boolean;
  fallback_reason?: string | null;
  checks?: Partial<GuardrailChecks>;
  check_reasons?: Partial<Record<GuardrailCheckName, string | null>>;
  [key: string]: unknown;
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
  lower?: number;
  upper?: number;
  by_construction?: boolean;
  label?: string;
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
  detector_result_rows?: DetectorResult[];
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

export interface OperationalResultsResponse {
  synthetic: true;
  metrics: {
    test?: Record<string, number | string | boolean | null>;
    val?: Record<string, number | string | boolean | null>;
    [key: string]: unknown;
  };
  explanation_summary: {
    rows?: number;
    cases?: number;
    fallbacks?: number;
	    fallback_rate?: number | RateEstimate;
	    fallback_rate_wilson?: { rate: number; n: number; lower?: number; upper?: number };
	    transport_failure_rate?: RateEstimate;
	    validator_failure_rate?: RateEstimate;
	    deterministic_delivered_detected_violation_rate?: RateEstimate;
	    llm_latency_ms_mean?: number;
	    llm_latency_ms_n?: number;
    transport_failures?: number;
    validator_failures?: number;
    structural_descriptors?: {
      payload_fields?: string[];
      evidence_fields?: string[];
      validator_checks?: string[];
      top_k?: number;
      corpus_version?: string;
    };
    [key: string]: unknown;
  };
  validator_calibration?: {
    passed?: boolean;
    n?: number;
    corpus_version?: string;
    attack_interception?: { rate: number; n: number; lower?: number; upper?: number };
    control_acceptance?: { rate: number; n: number; lower?: number; upper?: number };
    [key: string]: unknown;
  } | null;
  case_count: number;
  provenance: OperationalProvenanceResponse;
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
