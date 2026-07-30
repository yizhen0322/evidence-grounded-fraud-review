import type {
  CaseDetail,
  CasesResponse,
  DemoScenario,
  DemoScenariosResponse,
  ExplanationArmResult,
  HealthResponse,
  NarrativeView,
  OperationalProvenanceResponse,
  ProvenanceEntry,
  ProvenanceResponse,
  ResultsResponse,
} from "./types";

export function normalizeCases(response: CasesResponse | CaseDetail[]): { items: CaseDetail[]; total: number } {
  if (Array.isArray(response)) return { items: response, total: response.length };
  const items = (response.items ?? response.cases ?? []) as CaseDetail[];
  return { items, total: response.total ?? items.length };
}

export function normalizeScenarios(
  response: DemoScenariosResponse | { scenarios: DemoScenariosResponse } | undefined,
): DemoScenario[] {
  const value: DemoScenariosResponse | undefined = response && "scenarios" in response && !Array.isArray(response.scenarios)
    ? response.scenarios
    : response as DemoScenariosResponse | undefined;
  if (!value) return [];
  if (Array.isArray(value.scenarios)) return value.scenarios;
  const scenarios: DemoScenario[] = [];
  if (value.faithful_case_id !== undefined) {
    scenarios.push({
      key: "faithful",
      kind: "faithful",
      case_id: value.faithful_case_id,
      title: "Faithful recorded case",
      description: "Follow accepted strict-arm evidence through the full explanation chain.",
    });
  }
  if (value.error_or_uncertainty_case_id !== undefined) {
    scenarios.push({
      key: "error",
      kind: "error",
      case_id: value.error_or_uncertainty_case_id,
      title: "Real false positive",
      description: "Inspect a flagged transaction whose evaluation-only label is legitimate.",
    });
  }
  if (value.attack_case_id !== undefined) {
    scenarios.push({
      key: "attack",
      kind: "attack",
      case_id: value.attack_case_id,
      title: "Guardrail challenge",
      description: "Use recorded evidence for deterministic validator attacks.",
    });
  }
  return scenarios;
}

export function artifactReady(health: HealthResponse | undefined): boolean | null {
  if (!health) return null;
  return health.artifact_ready ?? health.artifacts_ready ?? health.application_ready ?? health.ready ?? false;
}

export function ollamaState(health: HealthResponse | undefined): "available" | "unavailable" | "checking" {
  if (!health) return "checking";
  const status = health.ollama?.status ?? health.ollama_status;
  if (status === "available" || status === "unavailable" || status === "checking") return status;
  const available = health.ollama?.available ?? health.ollama_available;
  if (available === null || available === undefined) return "checking";
  return available ? "available" : "unavailable";
}

export function caseNarrative(value: CaseDetail | undefined): NarrativeView | null {
  return value?.recorded_narrative ?? value?.narrative ?? null;
}

export function provenanceEntries(response: ProvenanceResponse | OperationalProvenanceResponse | undefined): Array<[string, ProvenanceEntry]> {
  if (!response) return [];
  if ("run_id" in response) {
    return [["s0", {
      run_id: response.run_id,
      manifest_sha256: response.manifest_sha256,
      group: response.group,
    }]];
  }
  if (response.artifacts) return Object.entries(response.artifacts);
  return (["detector", "g4", "g5", "results"] as const).flatMap((key) => {
    const entry = response[key];
    return entry ? [[key, entry] as [string, ProvenanceEntry]] : [];
  });
}

export function explanationArms(results: ResultsResponse | undefined): ExplanationArmResult[] {
  if (!results?.explanation_results) return [];
  if (Array.isArray(results.explanation_results)) return results.explanation_results;
  if (Array.isArray(results.explanation_results.arms)) return results.explanation_results.arms;
  return [results.explanation_results.strict, results.explanation_results.simple].filter(
    (item): item is ExplanationArmResult => Boolean(item),
  );
}
