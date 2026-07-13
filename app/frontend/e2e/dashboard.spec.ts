import { expect, test } from "@playwright/test";

const health = { artifact_ready: true, ollama_status: "unavailable", build_version: "e2e" };
const provenance = {
  source_chain_valid: true,
  source_code_compatible: true,
  detector: { run_id: "detector", manifest_sha256: "a".repeat(64) },
  g4: { run_id: "g4", manifest_sha256: "b".repeat(64) },
  g5: { run_id: "g5", manifest_sha256: "c".repeat(64) },
};
const scenarios = { faithful_case_id: 42009, error_or_uncertainty_case_id: 120085, attack_case_id: 42009 };
const narrative = {
  final_text: "Risk: High\nReasons: V14 increases risk.\nAction: Review.",
  checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
  fallback: false,
  latency_seconds: 1.2,
};
const caseRecord = {
  case_id: 42009, risk_bucket: "High", score: 0.94, pred: 1, y_true: 1, threshold: 0.42,
  top_reason: { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
  reason_codes: [{ feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 }],
  recorded_narrative: narrative,
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/health")) return route.fulfill({ json: health });
    if (url.pathname.endsWith("/provenance")) return route.fulfill({ json: provenance });
    if (url.pathname.endsWith("/demo-scenarios")) return route.fulfill({ json: scenarios });
    if (url.pathname.endsWith("/cases")) return route.fulfill({ json: { items: [caseRecord], total: 1 } });
    if (url.pathname.endsWith("/cases/42009")) return route.fulfill({ json: caseRecord });
    if (url.pathname.endsWith("/guardrails/demo")) return route.fulfill({ json: {
      case_id: 42009, preset: "direction_flip", original_text: narrative.final_text,
      tampered_text: narrative.final_text.replace("increases", "decreases"),
      checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "FAIL" },
      check_reasons: { direction: "V14 direction contradicts recorded evidence." },
      fallback: true, fallback_reason: "direction", final_text: "Reason codes: V14 increases risk.",
    } });
    if (url.pathname.endsWith("/results")) return route.fulfill({ json: {
      detector_results: [{ group: "g6", auc_pr_mean: 0.855, auc_pr_std: 0.027 }],
      explanation_results: { strict: { arm: "strict", any_detected_violation: { rate: 0.1, n: 51 }, fallback: { rate: 0.1, n: 51 } } },
    } });
    if (url.pathname.includes("/figures/")) return route.fulfill({ status: 404 });
    return route.fulfill({ status: 404, json: { message: "Unhandled fixture request" } });
  });
});

test("recorded queue to investigation to guardrail result", async ({ page }) => {
  const nonLoopback: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) nonLoopback.push(request.url());
  });

  await page.goto("/queue");
  await expect(page.getByRole("heading", { name: "Flagged case queue" })).toBeVisible();
  await page.getByRole("button", { name: /Open case/ }).click();
  await expect(page.getByRole("heading", { name: /Case/ })).toBeVisible();
  await expect(page.getByText("Evaluation-only ground truth")).toBeVisible();
  await page.getByRole("link", { name: /Challenge this narrative/ }).click();
  await page.getByRole("button", { name: "Run validation" }).click();
  await expect(page.getByText("Rejected → fallback active")).toBeVisible();
  await expect(page.getByText("Direction", { exact: true }).last()).toBeVisible();
  expect(nonLoopback).toEqual([]);
});
