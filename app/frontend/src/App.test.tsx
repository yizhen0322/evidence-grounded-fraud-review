import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";

const HEALTH = {
  artifact_ready: true,
  ollama_status: "unavailable",
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
  y_true: 1,
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
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/health")) return response(HEALTH);
      if (url.endsWith("/provenance")) return response(PROVENANCE);
      if (url.endsWith("/demo-scenarios")) return response(SCENARIOS);
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

  it("renders the queue with explicit evaluation-only wording and recorded status", async () => {
    renderApp("/queue");

    expect(await screen.findByRole("heading", { name: "Flagged case queue" })).toBeInTheDocument();
    expect(await screen.findByText("Evaluation-only ground truth")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Fraud" })).toBeInTheDocument();
    expect(screen.getByText("Ollama unavailable")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Passed" })).toBeInTheDocument();
  });

  it("keeps recorded and live replay labels distinct and shows all four checks", async () => {
    const user = userEvent.setup();
    renderApp("/cases/42009");

    expect(await screen.findByText(/Recorded strict-prompt arm/)).toBeInTheDocument();
    expect(screen.getAllByText("Evaluation-only ground truth").length).toBeGreaterThan(0);
    expect(screen.getByText("Completeness")).toBeInTheDocument();

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
});
