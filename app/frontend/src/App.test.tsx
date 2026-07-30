import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { AttackPreset, WorkflowRecord } from "./api/types";

const HEALTH = {
  artifact_ready: true,
  ollama_status: "unavailable",
  ollama: {
    available: false,
    status: "unavailable",
    model: "llama3:8b",
  },
  workflow_status: "ready",
  build_version: "test-build",
};

const PROVENANCE = {
  source_chain_valid: true,
  source_code_compatible: true,
  detector: { run_id: "2026-07-14_g6_seed42", manifest_sha256: "a".repeat(64) },
  g4: { run_id: "2026-07-14_g4_seed42", manifest_sha256: "b".repeat(64) },
  g5: { run_id: "2026-07-14_g5_seed42", manifest_sha256: "c".repeat(64) },
};

const SCENARIOS = {
  faithful_case_id: 42009,
  error_or_uncertainty_case_id: 120085,
  attack_case_id: 42009,
};

const CASE = {
  case_id: 42009,
  risk_bucket: "High",
  score_rank: 1,
  flagged_total: 51,
  pred: 1,
  threshold: 0.42,
  transaction_context: {
    amount: 112.33,
    elapsed_seconds: 40919,
    currency: null,
    time_basis: "seconds_since_dataset_start",
    source: "hash_verified_dataset_row",
  },
  reason_codes: [
    { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
    { feature: "V10", direction: "decreases_risk", rank: 2, shap_value: -1.1 },
  ],
  top_reason: { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
  top_reasons: [
    { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
    { feature: "V10", direction: "decreases_risk", rank: 2, shap_value: -1.1 },
  ],
  recorded_narrative: {
    mode: "recorded",
    reported: true,
    arm: "strict",
    final_text: "NARRATIVE: This case is rated High risk. V14 increases risk, while V10 decreases risk.\nEVIDENCE:\n- V14 - increases risk\n- V10 - decreases risk\nACTION: Recommended for manual review.",
    checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
    fallback: false,
    latency_seconds: 1.2,
  },
};

const OPERATIONAL_CASE = {
  ...CASE,
  case_id: 9001,
  transaction_id: "TX-0009001",
  timestamp: "2026-01-08T09:35:00+00:00",
  amount: 486.75,
  rank: 2,
  readable_top_signal: "Amount vs customer 30-day average is unusually high",
  top_signal: {
    feature: "AmountVsCustomer30Day",
    display_label: "Amount vs customer 30-day average",
    direction: "increases_risk",
    rank: 1,
    shap_value: 1.8,
    value_bucket: "high",
  },
  top_reasons: [
    {
      feature: "AmountVsCustomer30Day",
      display_label: "Amount vs customer 30-day average",
      direction: "increases_risk",
      rank: 1,
      shap_value: 1.8,
      value_bucket: "high",
    },
    {
      feature: "NewTerminalForCustomer30Day",
      display_label: "New terminal for customer",
      direction: "increases_risk",
      rank: 2,
      shap_value: 1.1,
      value_bucket: "new",
    },
  ],
  raw_reason_codes: [
    {
      feature: "AmountVsCustomer30Day",
      display_label: "Amount vs customer 30-day average",
      direction: "increases_risk",
      rank: 1,
      shap_value: 1.8,
      value_bucket: "high",
    },
    {
      feature: "NewTerminalForCustomer30Day",
      display_label: "New terminal for customer",
      direction: "increases_risk",
      rank: 2,
      shap_value: 1.1,
      value_bucket: "new",
    },
  ],
  deterministic_brief: "Deterministic brief: amount is high against the customer history and the terminal is new.",
  guarded_llm_brief: "Guarded LLM brief: this alert combines a high relative amount with a new terminal signal.",
  explanation_comparison: {
    raw_reason_codes: [
      {
        feature: "AmountVsCustomer30Day",
        display_label: "Amount vs customer 30-day average",
        direction: "increases_risk",
        rank: 1,
        shap_value: 1.8,
        value_bucket: "high",
      },
      {
        feature: "NewTerminalForCustomer30Day",
        display_label: "New terminal for customer",
        direction: "increases_risk",
        rank: 2,
        shap_value: 1.1,
        value_bucket: "new",
      },
    ],
    deterministic_brief: "Deterministic brief: amount is high against the customer history and the terminal is new.",
    guarded_llm_brief: "Guarded LLM brief: this alert combines a high relative amount with a new terminal signal.",
    delivered_brief: "Delivered brief: this alert combines a high relative amount with a new terminal signal.",
  },
  validation: {
    fallback: false,
    checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
  },
  minimized_payload: {
    evidence: [
      { key: "AmountVsCustomer30Day", label: "Amount vs customer 30-day average", direction: "increases_risk", rank: 1, bucket: "high" },
      { key: "NewTerminalForCustomer30Day", label: "New terminal for customer", direction: "increases_risk", rank: 2, bucket: "new" },
    ],
  },
  explanation_delivery: "guarded_llm",
  transaction_context: {
    amount: 486.75,
    timestamp: "2026-01-08T09:35:00+00:00",
    currency: null,
    time_basis: "synthetic_stream_timestamp",
    source: "synthetic_operational_case",
  },
};

const RESULTS = {
  detector_results: [
    {
      group: "g0",
      auc_pr_mean: 0.853,
      auc_pr_std: 0.021,
      roc_auc_mean: 0.975,
      roc_auc_std: 0.009,
      precision_mean: 0.93,
      precision_std: 0.06,
      recall_mean: 0.789,
      recall_std: 0.061,
      f1_mean: 0.851,
      f1_std: 0.026,
      false_positives_mean: 4.6,
      false_negatives_mean: 15,
    },
    {
      group: "g2",
      auc_pr_mean: 0.854,
      auc_pr_std: 0.017,
      roc_auc_mean: 0.976,
      roc_auc_std: 0.008,
      precision_mean: 0.937,
      precision_std: 0.039,
      recall_mean: 0.814,
      recall_std: 0.05,
      f1_mean: 0.87,
      f1_std: 0.026,
      false_positives_mean: 4,
      false_negatives_mean: 13.2,
    },
  ],
  explanation_results: {
    strict: {
      arm: "strict",
      format: { rate: 0.039, n: 51, ci_low: 0.011, ci_high: 0.132 },
      completeness: { rate: 0, n: 51, ci_low: 0, ci_high: 0.07 },
      grounding: { rate: 0.039, n: 51, ci_low: 0.011, ci_high: 0.132 },
      direction: { rate: 0.039, n: 51, ci_low: 0.011, ci_high: 0.132 },
      any_detected_violation: { rate: 0.039, n: 51, ci_low: 0.011, ci_high: 0.132 },
      fallback: { rate: 0.039, n: 51, ci_low: 0.011, ci_high: 0.132 },
      mean_latency_seconds: 4.84,
      llm_transport_unavailable_count: 0,
    },
  },
};

const OPERATIONAL_RESULTS = {
  synthetic: true,
  metrics: {
    test: { auc_pr: 0.544, precision: 0.72, recall: 0.4 },
  },
  explanation_summary: {
    rows: 25,
    fallbacks: 2,
    fallback_rate: 0.08,
    fallback_rate_wilson: { rate: 0.08, n: 25, lower: 0.022, upper: 0.251 },
    transport_failure_rate: { rate: 0.04, n: 25, lower: 0.007, upper: 0.195 },
    validator_failure_rate: { rate: 0.04, n: 25, lower: 0.007, upper: 0.195 },
    deterministic_delivered_detected_violation_rate: { rate: 0, n: 25, lower: 0, upper: 0.133, label: "by_construction" },
    llm_latency_ms_mean: 21932,
    llm_latency_ms_n: 23,
    structural_descriptors: {
      top_k: 3,
      payload_fields: ["risk_bucket", "evidence"],
      evidence_fields: ["rank", "feature", "display_label", "direction", "value_bucket"],
      validator_checks: ["format", "completeness", "grounding", "direction"],
      corpus_version: "semantic_guardrail_corpus_v1",
    },
  },
  validator_calibration: {
    passed: true,
    n: 190,
    corpus_version: "semantic_guardrail_corpus_v1",
    attack_interception: { rate: 1, n: 150 },
    control_acceptance: { rate: 1, n: 40 },
  },
  case_count: 25,
  provenance: {
    run_id: "2026-07-26_s0_seed42",
    group: "s0",
    seed: 42,
    synthetic: true,
    manifest_sha256: "d".repeat(64),
    artifacts: {
      "semantic_validator_calibration.json": {
        sha256: "e".repeat(64),
        source: "semantic_run/semantic_validator_calibration.json",
      },
    },
  },
};

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  }));
}

function renderApp(path: string) {
  window.history.pushState({}, "", path);
  return render(<BrowserRouter><App /></BrowserRouter>);
}

describe("Fraud Review Workbench", () => {
  let workflow: WorkflowRecord;
  let workflowEvents: Array<Record<string, unknown>>;
  let conflictNextUpdate: boolean;

  beforeEach(() => {
    workflow = {
      case_id: 42009,
      status: "unreviewed",
      disposition: null,
      note: "",
      revision: 0,
      created_at: null,
      updated_at: null,
      evidence_compatible: true,
      activity_count: 0,
    };
    workflowEvents = [];
    conflictNextUpdate = false;
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return response(HEALTH);
      if (url.endsWith("/provenance")) return response(PROVENANCE);
      if (url.endsWith("/demo-scenarios")) return response(SCENARIOS);
      if (url.endsWith("/workflow/summary")) {
        return response({
          total: 1,
          counts: {
            unreviewed: workflow.status === "unreviewed" ? 1 : 0,
            in_review: workflow.status === "in_review" ? 1 : 0,
            needs_follow_up: workflow.status === "needs_follow_up" ? 1 : 0,
            review_complete: workflow.status === "review_complete" ? 1 : 0,
          },
          recorded_fallback: 0,
          evidence_fingerprint: "f".repeat(64),
        });
      }
      if (url.endsWith("/workflow/cases/9001/activity")) return response({ items: workflowEvents });
      if (url.endsWith("/workflow/cases/9001")) return response({ ...workflow, case_id: 9001 });
      if (url.endsWith("/operational/cases/9001")) return response(OPERATIONAL_CASE);
      if (url.includes("/operational/cases")) return response({ items: [OPERATIONAL_CASE], total: 1 });
      if (url.endsWith("/operational/results")) return response(OPERATIONAL_RESULTS);
      if (url.endsWith("/operational/guardrails/demo") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { case_id: number; preset: AttackPreset };
        return response({
          mode: "operational_guardrail_demo",
          reported: false,
          case_id: body.case_id,
          preset: body.preset,
          original_text: JSON.stringify({ risk_bucket: "High", action: "manual_review" }, null, 2),
          tampered_text: JSON.stringify({ risk_bucket: "High" }, null, 2),
          checks: { format: body.preset === "template_corruption" ? "FAIL" : "PASS", completeness: "PASS", grounding: body.preset === "unlisted_feature" ? "FAIL" : "PASS", direction: body.preset === "direction_flip" ? "FAIL" : "PASS" },
          fallback: true,
          fallback_reason: body.preset === "direction_flip" ? "direction" : body.preset === "unlisted_feature" ? "grounding" : "format",
          final_text: "Deterministic semantic fallback delivered.",
          validator: "src.semantic.explanations.validate_structured_brief",
        });
      }
      if (url.endsWith("/workflow/cases/42009/activity")) return response({ items: workflowEvents });
      if (url.endsWith("/workflow/cases/42009") && init?.method === "PUT") {
        const update = JSON.parse(String(init.body)) as Pick<WorkflowRecord, "status" | "disposition" | "note" | "revision">;
        if (conflictNextUpdate) {
          conflictNextUpdate = false;
          workflow = {
            ...workflow,
            revision: workflow.revision + 1,
            note: "Saved in another browser tab.",
            updated_at: "2026-07-14T01:03:00+00:00",
          };
          return response({ code: "workflow_revision_conflict", message: "stale revision", details: null }, 409);
        }
        workflow = {
          ...workflow,
          status: update.status,
          disposition: update.disposition,
          note: update.note,
          revision: workflow.revision + 1,
          created_at: workflow.created_at ?? "2026-07-14T01:00:00+00:00",
          updated_at: "2026-07-14T01:00:00+00:00",
          activity_count: workflow.activity_count + 1,
        };
        workflowEvents = [{
          id: workflow.revision,
          event_type: workflow.status === "review_complete" ? "review_completed" : "review_started",
          from_status: "unreviewed",
          to_status: workflow.status,
          disposition: workflow.disposition,
          note_changed: Boolean(workflow.note),
          revision: workflow.revision,
          created_at: workflow.updated_at,
        }, ...workflowEvents];
        return response(workflow);
      }
      if (url.endsWith("/workflow/cases/42009")) return response(workflow);
      if (url.endsWith("/workflow/cases")) return response({ items: [workflow], total: 1 });
      if (url.includes("/cases/42009")) return response(CASE);
      if (url.includes("/cases")) return response({ items: [CASE], total: 1 });
      if (url.endsWith("/results")) return response(RESULTS);
      if (url.endsWith("/live/narrative") && init?.method === "POST") {
        return response({
          mode: "live_demo",
          reported: false,
          case_id: 42009,
          final_text: "Live replay text",
          checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
          fallback: false,
          latency_seconds: 0.8,
        });
      }
      return response({ message: `Unhandled request ${url}` }, 404);
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
    window.history.pushState({}, "", "/");
  });

  it("lands directly on the analyst work queue", async () => {
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Alert Queue" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Alert Queue/ })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "Source" })).toHaveValue("operational");
    expect(screen.getByRole("option", { name: "S0 explanation cases" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "All sources" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Explanation Assurance/ })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Evaluation Results/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Operations Overview/ })).not.toBeInTheDocument();
  });

  it("defaults the queue to source-labelled S0 cases without exposing historical ground truth", async () => {
    renderApp("/queue");

    expect(await screen.findByRole("heading", { name: "Alert Queue" })).toBeInTheDocument();
    expect(screen.getAllByText("Operational").length).toBeGreaterThan(0);
    expect(screen.queryByText("ULB real-data benchmark evidence")).not.toBeInTheDocument();
    expect(screen.getByText("1 primary explanation cases")).toBeInTheDocument();
    expect(screen.getByText("1 supporting benchmark alerts")).toBeInTheDocument();
    expect(screen.queryByText("Evaluation-only ground truth")).not.toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "Fraud" })).not.toBeInTheDocument();
    expect(screen.getByText("Narrative service unavailable")).toBeInTheDocument();
    expect(screen.getAllByText("Unreviewed").length).toBeGreaterThan(0);
    expect(screen.getByText("Guarded LLM brief")).toBeInTheDocument();
    expect(screen.getByText("Amount 486.75")).toBeInTheDocument();
    expect(screen.getByText("#2 of 51")).toBeInTheDocument();
    expect(screen.getByText("Amount vs customer 30-day average is unusually high")).toBeInTheDocument();
    expect(screen.getByText("New terminal for customer")).toBeInTheDocument();
    expect(screen.getAllByText((_, element) => element?.textContent === "Amount vs customer 30-day average↑ · high").length).toBeGreaterThan(0);
    expect(screen.getAllByText((_, element) => element?.textContent === "New terminal for customer↑ · new").length).toBeGreaterThan(0);
    expect(screen.queryByText("0.9412")).not.toBeInTheDocument();
  });

  it("shows ULB benchmark evidence only when the research or all-source lane is selected", async () => {
    const user = userEvent.setup();
    renderApp("/queue");

    await user.selectOptions(await screen.findByRole("combobox", { name: "Source" }), "all");

    expect(screen.getAllByText("Operational").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Research").length).toBeGreaterThan(0);
    expect(screen.getByText("S0 synthetic readable evidence")).toBeInTheDocument();
    expect(screen.getByText("ULB real-data benchmark evidence")).toBeInTheDocument();
    expect(screen.getByText("Within S0")).toBeInTheDocument();
    expect(screen.getByText("Within ULB")).toBeInTheDocument();
  });

  it("uses the same Start review action for active S0 and ULB cases", async () => {
    workflow = {
      ...workflow,
      status: "in_review",
      revision: 1,
      updated_at: "2026-07-14T01:00:00+00:00",
    };
    renderApp("/queue?source=all");

    expect(await screen.findAllByRole("button", { name: "Start review" })).toHaveLength(2);
    expect(screen.queryByRole("button", { name: "Open workspace" })).not.toBeInTheDocument();
  });

  it("keeps the ULB benchmark queue available when primary S0 evidence is unavailable", async () => {
    const defaultFetch = vi.mocked(fetch).getMockImplementation();
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).includes("/operational/")) {
        return response({ code: "semantic_run_unavailable", message: "S0 is unavailable" }, 503);
      }
      return defaultFetch!(input, init);
    });

    renderApp("/queue");

    expect(await screen.findByRole("heading", { name: "Alert Queue" })).toBeInTheDocument();
    expect(screen.getAllByText("Research").length).toBeGreaterThan(0);
    expect(screen.getByText("1 supporting benchmark alerts")).toBeInTheDocument();
    expect(screen.getByText(/S0 semantic evidence unavailable/)).toBeInTheDocument();
  });

  it("shows operational SHAP comparison and runs the S0 guardrail endpoint", async () => {
    const user = userEvent.setup();
    renderApp("/operational/cases/9001");

    expect(await screen.findByRole("heading", { name: "SHAP, deterministic brief, guarded local-LLM brief, validation/fallback" })).toBeInTheDocument();
    expect(screen.getByText(/SHAP \+1\.8000/)).toBeInTheDocument();
    expect(screen.getByText("Delivered brief: this alert combines a high relative amount with a new terminal signal.")).toBeInTheDocument();
    await user.click(screen.getByRole("link", { name: /Open Explanation Assurance/ }));
    expect(await screen.findByRole("heading", { name: "Explanation Assurance" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Run assurance test" }));

    expect(await screen.findByText("src.semantic.explanations.validate_structured_brief")).toBeInTheDocument();
    expect(screen.getByText("Deterministic semantic fallback delivered.")).toBeInTheDocument();
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/operational/guardrails/demo", expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ case_id: 9001, preset: "direction_flip" }),
      }));
    });
  });

  it("defaults direct guardrail entry to the S0 semantic validator", async () => {
    renderApp("/assurance/narratives");

    expect(await screen.findByRole("heading", { name: "Explanation Assurance" })).toBeInTheDocument();
    expect(screen.getByText("S0 structured validator")).toBeInTheDocument();
  });

  it("never presents missing provenance as verified", async () => {
    const user = userEvent.setup();
    const defaultFetch = vi.mocked(fetch).getMockImplementation();
    vi.mocked(fetch).mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input).endsWith("/provenance")) {
        return response({ code: "provenance_unavailable", message: "unavailable" }, 503);
      }
      return defaultFetch!(input, init);
    });

    renderApp("/research/queue");
    await user.click(await screen.findByRole("button", { name: /Evidence details/ }));

    expect(await screen.findByText("Verification unavailable")).toBeInTheDocument();
    expect(screen.queryByText("Source chain verified")).not.toBeInTheDocument();
  });

  it("keeps recorded and live replay labels distinct and shows all four checks", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    expect(await screen.findByRole("heading", { name: "Why this alert needs review" })).toBeInTheDocument();
    expect(screen.getAllByText("112.33").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Day 1, 11:21 elapsed").length).toBeGreaterThan(0);
    expect(screen.getByText(/V1–V28 are anonymised PCA components/)).toBeInTheDocument();
    expect(screen.queryByText("0.9412")).not.toBeInTheDocument();
    expect(screen.queryByText(/Historical ground truth/)).not.toBeInTheDocument();
    expect(screen.getByText("Why it is prioritised")).toBeInTheDocument();
    expect(screen.getByText("Evidence synthesis")).toBeInTheDocument();
    expect(screen.getByText("Locally generated review note", { exact: false })).toBeInTheDocument();
    expect(screen.getByText(/ranked it #1 among 51 flagged cases/)).toBeInTheDocument();
    expect(screen.getByText(/acts as counter-evidence/)).toBeInTheDocument();
    expect(screen.getByText(/Why use the LLM/)).toBeInTheDocument();
    expect(screen.getByText(/llama3:8b/)).toBeInTheDocument();
    await user.click(screen.getByText(/Verified against four deterministic checks/));
    expect(screen.getByText("Completeness")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Regenerate locally" }));
    expect(screen.getByText(/Temporary local generation/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate explanation" }));

    expect(await screen.findAllByText("Live replay text")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Return to saved brief" })).toBeInTheDocument();
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/live/narrative", expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ case_id: 42009 }),
      }));
    });
  });

  it("shows F1 and operating trade-offs as readable bar charts", async () => {
    renderApp("/assurance/performance");

    const semantic = await screen.findByRole("region", { name: "Primary semantic and operational evaluation" });
    const explanation = screen.getByRole("region", { name: "Explanation policy performance" });
    const detector = screen.getByRole("region", { name: "Supporting detector benchmark" });
    expect(semantic.compareDocumentPosition(detector) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(explanation.compareDocumentPosition(detector) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Evaluation Results" })).toBeInTheDocument();
    expect(screen.getByText("Primary local-LLM evaluation context")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "F1 score comparison" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "F1 score by detector strategy" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "Precision and recall by detector strategy" })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: "False positives and false negatives by detector strategy" })).toBeInTheDocument();
    expect(screen.getAllByText("0.870 ± 0.026")).toHaveLength(2);
    expect(screen.getByRole("img", { name: "Narrative policy violation, fallback, and pass rates" })).toBeInTheDocument();
    expect(screen.getByText("Guardrail pass / LLM delivered")).toBeInTheDocument();
    expect(screen.getByText("96.1%")).toBeInTheDocument();
    expect(screen.getAllByText(/Fallback delivery/).length).toBeGreaterThan(0);
    expect(screen.getByText(/8.0% · n=25 · 95% CI 2.2/)).toBeInTheDocument();
    expect(screen.getByText(/Transport failure/)).toBeInTheDocument();
    expect(screen.getByText(/Delivered deterministic violations/)).toBeInTheDocument();
    expect(screen.getByText(/by construction/)).toBeInTheDocument();
    expect(screen.getByText(/semantic_guardrail_corpus_v1 · top-k 3/)).toBeInTheDocument();
    expect(screen.getByText(/risk_bucket, evidence/)).toBeInTheDocument();
  });

  it("persists a provisional analyst review through the workflow API", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    await user.selectOptions(await screen.findByLabelText("Action"), "suspicious");
    await user.type(screen.getByLabelText(/Analyst note/), "Escalate based on the recorded evidence.");
    await user.click(screen.getByRole("button", { name: "Confirm & close" }));

    expect((await screen.findAllByText("Closed")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/workflow/cases/42009", expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          revision: 0,
          status: "review_complete",
          disposition: "suspicious",
          note: "Escalate based on the recorded evidence.",
        }),
      }));
    });
  });

  it("reloads the current revision after an optimistic workflow conflict", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    await user.type(await screen.findByLabelText(/Analyst note/), "Draft before conflict.");
    conflictNextUpdate = true;
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    expect(await screen.findByText("stale revision")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/Analyst note/)).toHaveValue("Saved in another browser tab.");
    });

    await user.clear(screen.getByLabelText(/Analyst note/));
    await user.type(screen.getByLabelText(/Analyst note/), "Reviewed after conflict recovery.");
    await user.click(screen.getByRole("button", { name: "Save draft" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/workflow/cases/42009", expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          revision: 1,
          status: "in_review",
          disposition: null,
          note: "Reviewed after conflict recovery.",
        }),
      }));
    });
  });
});
