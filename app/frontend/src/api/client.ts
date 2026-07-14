import type {
  AttackPreset,
  CaseDetail,
  CasesResponse,
  DemoScenariosResponse,
  GuardrailDemoResponse,
  HealthResponse,
  LiveNarrativeResponse,
  ProvenanceResponse,
  ResultsResponse,
  WorkflowActivityResponse,
  WorkflowListResponse,
  WorkflowRecord,
  WorkflowSummaryResponse,
  WorkflowUpdate,
} from "./types";

const API_ROOT = "/api/v1";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...init,
    headers: {
      Accept: "application/json",
      ...(init?.body ? { "Content-Type": "application/json" } : {}),
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    let code: string | undefined;
    try {
      const body = (await response.json()) as {
        code?: string;
        message?: string;
        detail?: string | { code?: string; message?: string };
      };
      if (typeof body.detail === "string") message = body.detail;
      else if (body.detail?.message) message = body.detail.message;
      else if (body.message) message = body.message;
      code = body.code ?? (typeof body.detail === "object" ? body.detail.code : undefined);
    } catch {
      // The stable fallback avoids exposing an unexpected server body.
    }
    throw new ApiError(message, response.status, code);
  }

  return (await response.json()) as T;
}

export interface CaseFilters {
  risk_bucket?: string;
  recorded_fallback?: string;
  offset?: number;
  limit?: number;
}

function queryString(filters: CaseFilters): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const api = {
  health: () => request<HealthResponse>("/health"),
  provenance: () => request<ProvenanceResponse>("/provenance"),
  scenarios: () => request<DemoScenariosResponse | { scenarios: DemoScenariosResponse }>("/demo-scenarios"),
  cases: (filters: CaseFilters = {}) => request<CasesResponse | CaseDetail[]>(`/cases${queryString(filters)}`),
  case: (caseId: number | string) => request<CaseDetail>(`/cases/${encodeURIComponent(caseId)}`),
  results: () => request<ResultsResponse>("/results"),
  workflowSummary: () => request<WorkflowSummaryResponse>("/workflow/summary"),
  workflows: () => request<WorkflowListResponse>("/workflow/cases"),
  workflow: (caseId: number | string) =>
    request<WorkflowRecord>(`/workflow/cases/${encodeURIComponent(caseId)}`),
  workflowActivity: (caseId: number | string) =>
    request<WorkflowActivityResponse>(`/workflow/cases/${encodeURIComponent(caseId)}/activity`),
  updateWorkflow: (caseId: number | string, update: WorkflowUpdate) =>
    request<WorkflowRecord>(`/workflow/cases/${encodeURIComponent(caseId)}`, {
      method: "PUT",
      body: JSON.stringify(update),
    }),
  figureUrl: (figureId: "pr_curves" | "shap_global_bar") => `${API_ROOT}/figures/${figureId}`,
  liveNarrative: (caseId: number) =>
    request<LiveNarrativeResponse>("/live/narrative", {
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({ case_id: caseId }),
    }),
  guardrailDemo: (caseId: number, preset: AttackPreset) =>
    request<GuardrailDemoResponse>("/guardrails/demo", {
      method: "POST",
      cache: "no-store",
      body: JSON.stringify({ case_id: caseId, preset }),
    }),
};
