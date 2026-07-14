import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import type { WorkflowRecord } from "./api/types";

const HEALTH = {
  artifact_ready: true,
  ollama_status: "unavailable",
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
  score: 0.9412,
  pred: 1,
  threshold: 0.42,
  reason_codes: [
    { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
    { feature: "V10", direction: "decreases_risk", rank: 2, shap_value: -1.1 },
  ],
  recorded_narrative: {
    mode: "recorded",
    reported: true,
    arm: "strict",
    final_text: "Risk: High\nReasons: V14 increases risk. V10 decreases risk.\nAction: Review this transaction.",
    checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
    fallback: false,
    latency_seconds: 1.2,
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

describe("Fraud Evidence Console", () => {
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

  it("renders an operational queue without exposing historical ground truth", async () => {
    renderApp("/queue");

    expect(await screen.findByRole("heading", { name: "Work Queue" })).toBeInTheDocument();
    expect(screen.queryByText("Evaluation-only ground truth")).not.toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: "Fraud" })).not.toBeInTheDocument();
    expect(screen.getByText("Ollama unavailable")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Unreviewed" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Verified" })).toBeInTheDocument();
  });

  it("keeps recorded and live replay labels distinct and shows all four checks", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    expect(await screen.findByText(/Recorded strict-prompt arm/)).toBeInTheDocument();
    expect(screen.queryByText(/Historical ground truth/)).not.toBeInTheDocument();
    await user.click(screen.getByText(/Verified against four deterministic checks/));
    expect(screen.getByText("Completeness")).toBeVisible();

    await user.click(screen.getByRole("button", { name: "Live replay" }));
    expect(screen.getByText(/Demo-only; not a reported G5 result/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate live replay" }));

    expect(await screen.findByText("Live replay text")).toBeInTheDocument();
    expect(screen.queryByText(/Reportable frozen output/)).not.toBeInTheDocument();
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/live/narrative", expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ case_id: 42009 }),
      }));
    });
  });

  it("persists a provisional analyst review through the workflow API", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    await user.click(await screen.findByRole("button", { name: "Start review" }));
    expect((await screen.findAllByText("In review")).length).toBeGreaterThan(0);

    await user.selectOptions(screen.getByLabelText("Provisional assessment"), "suspicious");
    await user.type(screen.getByLabelText(/Analyst note/), "Escalate based on the recorded evidence.");
    await user.click(screen.getByRole("button", { name: "Complete review" }));

    expect((await screen.findAllByText("Review complete")).length).toBeGreaterThan(0);
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/workflow/cases/42009", expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          revision: 1,
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

    await user.click(await screen.findByRole("button", { name: "Start review" }));
    conflictNextUpdate = true;
    await user.click(screen.getByRole("button", { name: "Save review" }));

    expect(await screen.findByText("stale revision")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText(/Analyst note/)).toHaveValue("Saved in another browser tab.");
    });

    await user.clear(screen.getByLabelText(/Analyst note/));
    await user.type(screen.getByLabelText(/Analyst note/), "Reviewed after conflict recovery.");
    await user.click(screen.getByRole("button", { name: "Save review" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith("/api/v1/workflow/cases/42009", expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({
          revision: 2,
          status: "in_review",
          disposition: null,
          note: "Reviewed after conflict recovery.",
        }),
      }));
    });
  });
});
