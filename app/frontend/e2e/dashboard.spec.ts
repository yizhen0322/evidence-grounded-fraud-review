import { expect, test, type Page } from "@playwright/test";

type AttackPreset = "direction_flip" | "unlisted_feature" | "template_corruption";
type LiveFixture = "accepted" | "transport_unavailable";

const health = { artifact_ready: true, ollama_status: "available", build_version: "e2e" };
const provenance = {
  source_chain_valid: true,
  source_code_compatible: true,
  detector: { run_id: "detector", manifest_sha256: "a".repeat(64) },
  g4: { run_id: "g4", manifest_sha256: "b".repeat(64) },
  g5: { run_id: "g5", manifest_sha256: "c".repeat(64) },
};
const scenarios = {
  scenarios: [
    {
      key: "faithful",
      kind: "faithful",
      case_id: 42009,
      title: "Faithful recorded case",
      description: "Follow accepted evidence through the explanation chain.",
    },
    {
      key: "error",
      kind: "error",
      case_id: 120085,
      title: "Real false positive",
      description: "Inspect an evaluation-only legitimate transaction.",
    },
    {
      key: "attack",
      kind: "attack",
      case_id: 42009,
      title: "Guardrail challenge",
      description: "Run deterministic validator attacks.",
    },
  ],
};
const narrative = {
  mode: "recorded",
  reported: true,
  final_text: "Risk: High\nReasons: V14 increases risk.\nAction: Review.",
  checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
  fallback: false,
  latency_seconds: 1.2,
};
const caseRecord = {
  case_id: 42009,
  risk_bucket: "High",
  score: 0.94,
  pred: 1,
  detector_flagged: true,
  threshold: 0.42,
  top_reason: { feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 },
  reason_codes: [{ feature: "V14", direction: "increases_risk", rank: 1, shap_value: 2.4 }],
  recorded_narrative_status: "passed",
  recorded_narrative: narrative,
  data_sent_to_llm: {
    payload: "Case ID: 42009\nRisk level: High\n1. V14 increases risk",
    included: ["Case identifier", "Coarse risk bucket", "Feature names", "Direction and rank"],
    excluded: ["Raw transaction row", "Detector score or probability", "SHAP magnitudes", "Historical label"],
  },
};

const attackTargets: Record<AttackPreset, { check: string; tampered: string; reason: string }> = {
  direction_flip: {
    check: "direction",
    tampered: narrative.final_text.replace("increases", "decreases"),
    reason: "V14 direction contradicts recorded evidence.",
  },
  unlisted_feature: {
    check: "grounding",
    tampered: narrative.final_text.replace("V14", "merchant_score"),
    reason: "merchant_score is absent from the recorded evidence.",
  },
  template_corruption: {
    check: "format",
    tampered: "High risk because V14 increases risk.",
    reason: "Required narrative sections are missing.",
  },
};

const results = {
  detector_results: [
    { group: "g0", label: "Baseline", auc_pr_mean: 0.81, auc_pr_std: 0.02 },
    { group: "g4", label: "Explanation stage", auc_pr_mean: 0.99 },
    { group: "g6", label: "Hybrid", auc_pr_mean: 0.855, auc_pr_std: 0.027 },
    { group: "g5", label: "Narrative stage", auc_pr_mean: 0.99 },
  ],
  explanation_results: {
    strict: {
      arm: "strict",
      format: { rate: 0, n: 51, ci_low: 0, ci_high: 0.07 },
      completeness: { rate: 0, n: 51, ci_low: 0, ci_high: 0.07 },
      grounding: { rate: 0.02, n: 51, ci_low: 0.004, ci_high: 0.10 },
      direction: { rate: 0.02, n: 51, ci_low: 0.004, ci_high: 0.10 },
      any_detected_violation: { rate: 0.0392, n: 51, ci_low: 0.011, ci_high: 0.132 },
      fallback: { rate: 0.0392, n: 51, ci_low: 0.011, ci_high: 0.132, by_construction: true },
      mean_latency_seconds: 1.2,
      llm_transport_unavailable_count: 0,
    },
    simple: {
      arm: "simple",
      any_detected_violation: { rate: 1, n: 51, ci_low: 0.93, ci_high: 1 },
      fallback: { rate: 1, n: 51, ci_low: 0.93, ci_high: 1, by_construction: true },
      mean_latency_seconds: 0.9,
      llm_transport_unavailable_count: 0,
    },
  },
};

async function installApiFixtures(page: Page, live: LiveFixture = "accepted") {
  let workflow = {
    case_id: 42009,
    status: "unreviewed",
    disposition: null as string | null,
    note: "",
    revision: 0,
    created_at: null as string | null,
    updated_at: null as string | null,
    evidence_compatible: true,
    activity_count: 0,
  };
  let workflowEvents: Array<Record<string, unknown>> = [];
  const captured = {
    liveBodies: [] as unknown[],
    guardrailBodies: [] as unknown[],
    workflowBodies: [] as unknown[],
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/health")) {
      return route.fulfill({
        json: { ...health, ollama_status: live === "accepted" ? "available" : "unavailable" },
      });
    }
    if (url.pathname.endsWith("/provenance")) return route.fulfill({ json: provenance });
    if (url.pathname.endsWith("/demo-scenarios")) return route.fulfill({ json: scenarios });
    if (url.pathname.endsWith("/workflow/summary")) {
      return route.fulfill({
        json: {
          total: 1,
          counts: {
            unreviewed: workflow.status === "unreviewed" ? 1 : 0,
            in_review: workflow.status === "in_review" ? 1 : 0,
            needs_follow_up: workflow.status === "needs_follow_up" ? 1 : 0,
            review_complete: workflow.status === "review_complete" ? 1 : 0,
          },
          recorded_fallback: 0,
          evidence_fingerprint: "f".repeat(64),
        },
      });
    }
    if (url.pathname.endsWith("/workflow/cases/42009/activity")) {
      return route.fulfill({ json: { items: workflowEvents } });
    }
    if (url.pathname.endsWith("/workflow/cases/42009") && request.method() === "PUT") {
      const body = request.postDataJSON() as {
        revision: number;
        status: string;
        disposition: string | null;
        note: string;
      };
      captured.workflowBodies.push(body);
      if (body.revision !== workflow.revision) {
        return route.fulfill({
          status: 409,
          json: { code: "workflow_revision_conflict", message: "stale revision", details: null },
        });
      }
      const previous = workflow.status;
      workflow = {
        ...workflow,
        status: body.status,
        disposition: body.disposition,
        note: body.note,
        revision: workflow.revision + 1,
        created_at: workflow.created_at ?? "2026-07-14T01:00:00+00:00",
        updated_at: "2026-07-14T01:05:00+00:00",
        activity_count: workflow.activity_count + 1,
      };
      workflowEvents = [{
        id: workflow.revision,
        event_type: body.status === "review_complete" ? "review_completed" : previous === "unreviewed" ? "review_started" : "review_updated",
        from_status: previous,
        to_status: body.status,
        disposition: body.disposition,
        note_changed: Boolean(body.note),
        revision: workflow.revision,
        created_at: workflow.updated_at,
      }, ...workflowEvents];
      return route.fulfill({ json: workflow });
    }
    if (url.pathname.endsWith("/workflow/cases/42009")) return route.fulfill({ json: workflow });
    if (url.pathname.endsWith("/workflow/cases")) return route.fulfill({ json: { items: [workflow], total: 1 } });
    if (url.pathname.endsWith("/cases")) return route.fulfill({ json: { items: [caseRecord], total: 1 } });
    if (url.pathname.endsWith("/cases/42009")) return route.fulfill({ json: caseRecord });
    if (url.pathname.endsWith("/guardrails/demo")) {
      const body = request.postDataJSON() as { case_id: number; preset: AttackPreset };
      captured.guardrailBodies.push(body);
      const attack = attackTargets[body.preset];
      const checks = { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" };
      checks[attack.check as keyof typeof checks] = "FAIL";
      return route.fulfill({
        headers: { "Cache-Control": "no-store" },
        json: {
          mode: "guardrail_demo",
          reported: false,
          case_id: body.case_id,
          preset: body.preset,
          original_text: narrative.final_text,
          tampered_text: attack.tampered,
          checks,
          check_reasons: { [attack.check]: attack.reason },
          fallback: true,
          fallback_reason: attack.check,
          final_text: "Risk level: High\nReason codes: V14 increases risk.",
          validator: "src.narratives.guardrails.validate_narrative",
        },
      });
    }
    if (url.pathname.endsWith("/live/narrative")) {
      const body = request.postDataJSON() as { case_id: number };
      captured.liveBodies.push(body);
      if (live === "transport_unavailable") {
        return route.fulfill({
          headers: { "Cache-Control": "no-store" },
          json: {
            mode: "live_demo",
            reported: false,
            case_id: body.case_id,
            raw_text: null,
            final_text: "Risk level: High\nReason codes: V14 increases risk.",
            checks: { format: "NOT_RUN", completeness: "NOT_RUN", grounding: "NOT_RUN", direction: "NOT_RUN" },
            fallback: true,
            fallback_reason: "llm_transport_unavailable",
            latency_seconds: 0.01,
          },
        });
      }
      return route.fulfill({
        headers: { "Cache-Control": "no-store" },
        json: {
          mode: "live_demo",
          reported: false,
          case_id: body.case_id,
          raw_text: narrative.final_text,
          final_text: narrative.final_text,
          checks: { format: "PASS", completeness: "PASS", grounding: "PASS", direction: "PASS" },
          fallback: false,
          fallback_reason: null,
          latency_seconds: 0.4,
        },
      });
    }
    if (url.pathname.endsWith("/results")) return route.fulfill({ json: results });
    if (url.pathname.includes("/figures/")) return route.fulfill({ status: 404 });
    return route.fulfill({ status: 404, json: { message: "Unhandled fixture request" } });
  });

  return captured;
}

test("recorded queue to investigation keeps all browser traffic loopback-only", async ({ page }) => {
  const captured = await installApiFixtures(page);
  const nonLoopback: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["127.0.0.1", "localhost"].includes(url.hostname)) nonLoopback.push(request.url());
  });

  await page.goto("/queue");
  await expect(page.getByRole("heading", { name: "Work Queue" })).toBeVisible();
  await expect(page.getByText("Evaluation-only ground truth")).toHaveCount(0);
  await page.getByRole("button", { name: "Start review", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Case 42009/ })).toBeVisible();
  await expect(page.getByText(/Historical ground truth/)).toHaveCount(0);
  await expect(page.getByText("Recorded strict-prompt arm · Reportable frozen output")).toBeVisible();
  expect(captured.liveBodies).toEqual([]);
  expect(nonLoopback).toEqual([]);
});

test("all three guardrail presets fail their intended check and activate fallback", async ({ page }) => {
  const captured = await installApiFixtures(page);
  const cases: Array<{ preset: AttackPreset; label: string; check: string }> = [
    { preset: "direction_flip", label: "Direction flip", check: "Direction" },
    { preset: "unlisted_feature", label: "Unlisted feature", check: "Grounding" },
    { preset: "template_corruption", label: "Template corruption", check: "Format" },
  ];

  await page.goto("/assurance/narratives?case_id=42009");
  for (const item of cases) {
    await page.getByText(item.label, { exact: true }).click();
    await page.getByRole("button", { name: "Run assurance test" }).click();
    await expect(page.getByText("Rejected → fallback active")).toBeVisible();
    const badge = page.getByLabel("Guardrail checks").locator(".status-badge", { hasText: item.check });
    await expect(badge).toContainText("FAIL");
    await expect(page.getByText("Deterministic fallback delivered")).toBeVisible();
  }

  expect(captured.guardrailBodies).toEqual(cases.map(({ preset }) => ({ case_id: 42009, preset })));
});

test("live replay success is explicitly demo-only and accepted", async ({ page }) => {
  const captured = await installApiFixtures(page, "accepted");
  await page.goto("/cases/42009");
  await page.getByRole("button", { name: "Live replay", exact: true }).click();
  await expect(page.getByText("Live replay has not been generated")).toBeVisible();
  await page.getByRole("button", { name: "Generate live replay" }).click();

  await expect(page.getByText("Explanation verified")).toBeVisible();
  await expect(page.getByText("Live replay · Demo-only; not a reported G5 result")).toBeVisible();
  await expect(page.getByLabel("Guardrail checks").getByText("PASS", { exact: true })).toHaveCount(4);
  expect(captured.liveBodies).toEqual([{ case_id: 42009 }]);
});

test("live transport failure becomes a successful NOT RUN fallback", async ({ page }) => {
  const captured = await installApiFixtures(page, "transport_unavailable");
  await page.goto("/cases/42009");
  await page.getByRole("button", { name: "Live replay", exact: true }).click();
  await page.getByRole("button", { name: "Generate live replay" }).click();

  await expect(page.getByText("Fallback active")).toBeVisible();
  await expect(page.getByText("Deterministic reason-code fallback delivered")).toBeVisible();
  await expect(page.getByText("llm transport unavailable")).toBeVisible();
  await expect(page.getByLabel("Guardrail checks").getByText("NOT RUN", { exact: true })).toHaveCount(4);
  expect(captured.liveBodies).toEqual([{ case_id: 42009 }]);
});

test("case deep links survive a full browser refresh", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/cases/42009");
  await expect(page.getByRole("heading", { name: /Case 42009/ })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/cases\/42009$/);
  await expect(page.getByRole("heading", { name: /Case 42009/ })).toBeVisible();
});

test("monitor keeps detector metrics separate from G4 and G5 narrative evidence", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/assurance/performance");

  const detectorSection = page.getByRole("region", { name: "Detector performance" });
  const explanationSection = page.getByRole("region", { name: "Explanation & narrative evidence" });
  await expect(detectorSection).toBeVisible();
  await expect(explanationSection).toBeVisible();
  await expect(detectorSection.getByRole("row")).toHaveCount(3);
  await expect(detectorSection.getByText("G0", { exact: true })).toBeVisible();
  await expect(detectorSection.getByText("G6", { exact: true })).toBeVisible();
  await expect(detectorSection.getByText("G4", { exact: true })).toHaveCount(0);
  await expect(detectorSection.getByText("G5", { exact: true })).toHaveCount(0);
  await expect(explanationSection.getByText("3.9%", { exact: true }).first()).toBeVisible();
  await explanationSection.getByText("Show simple-prompt comparison arm").click();
  await expect(explanationSection.getByText(/100.0% · n=51/).first()).toBeVisible();
});

test("primary routes are keyboard reachable", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/queue");

  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /Work Queue/ })).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("link", { name: /Narrative Assurance/ })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("heading", { name: "Narrative Assurance" })).toBeVisible();
});

test("the closed provenance drawer cannot capture keyboard focus", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/queue");

  const drawer = page.locator('aside[aria-label="Artifact provenance"]');
  await expect(drawer).toHaveAttribute("inert", "");
  await page.getByRole("button", { name: "Provenance", exact: true }).click();
  await expect(drawer).not.toHaveAttribute("inert", "");
  await expect(page.getByRole("heading", { name: "Provenance" })).toBeVisible();
  await drawer.getByRole("button", { name: "Close provenance drawer" }).click();
  await expect(drawer).toHaveAttribute("inert", "");
});

test("analyst can complete a review and recover it after refresh", async ({ page }) => {
  const captured = await installApiFixtures(page);
  await page.goto("/queue");
  await page.getByRole("button", { name: "Start review", exact: true }).click();

  await expect(page.getByText("In review").first()).toBeVisible();
  await page.getByLabel("Provisional assessment").selectOption("suspicious");
  await page.getByLabel("Analyst note").fill("Escalate based on the recorded evidence.");
  await page.getByRole("button", { name: "Complete review" }).click();

  await expect(page.getByText("Review complete").first()).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Analyst note")).toHaveValue("Escalate based on the recorded evidence.");
  await expect(page.getByLabel("Provisional assessment")).toHaveValue("suspicious");
  expect(captured.workflowBodies).toEqual([
    { revision: 0, status: "in_review", disposition: null, note: "" },
    {
      revision: 1,
      status: "review_complete",
      disposition: "suspicious",
      note: "Escalate based on the recorded evidence.",
    },
  ]);
});

test("legacy assurance links redirect to the product routes", async ({ page }) => {
  await installApiFixtures(page);
  await page.goto("/guardrails");
  await expect(page).toHaveURL(/\/assurance\/narratives$/);
  await expect(page.getByRole("heading", { name: "Narrative Assurance" })).toBeVisible();

  await page.goto("/results");
  await expect(page).toHaveURL(/\/assurance\/performance$/);
  await expect(page.getByRole("heading", { name: "Model & Policy Monitor" })).toBeVisible();
});
