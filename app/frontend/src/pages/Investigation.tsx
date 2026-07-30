import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ApiError, api } from "../api/client";
import { caseNarrative, normalizeCases } from "../api/normalize";
import type {
  LiveNarrativeResponse,
  NarrativeView,
  ReasonCode,
  WorkflowActivityEvent,
  WorkflowDisposition,
  WorkflowRecord,
  WorkflowStatus,
} from "../api/types";
import { useDemoContext } from "../components/DemoContext";
import { AlertIcon, ArrowIcon, FingerprintIcon, ShieldIcon } from "../components/icons";
import { ErrorState, LoadingState } from "../components/PageState";
import { GuardrailBadges, WorkflowBadge } from "../components/StatusBadge";
import { useRemoteData } from "../components/useRemoteData";
import { workflowLabel } from "../components/workflowLabels";

type ReviewMode = "operational" | "research";

function featureLabel(code: ReasonCode): string {
  return code.display_label ?? code.label ?? code.feature;
}

function contributionLabel(code: ReasonCode): string {
  return code.direction === "increases_risk" ? "Pushes toward fraud" : "Pushes toward legitimate";
}

function eventLabel(event: WorkflowActivityEvent): string {
  const labels: Record<string, string> = {
    review_started: "Review started",
    review_updated: "Review updated",
    review_reopened: "Review reopened",
    evidence_review_restarted: "Review restarted for current evidence",
    follow_up_requested: "Follow-up requested",
    review_completed: "Review completed",
  };
  return labels[event.event_type] ?? event.event_type.replaceAll("_", " ");
}

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function amountLabel(value: number | undefined): string {
  if (value === undefined) return "Unavailable";
  return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function elapsedLabel(value: number | undefined): string {
  if (value === undefined) return "Unavailable";
  const totalMinutes = Math.floor(value / 60);
  const day = Math.floor(totalMinutes / (24 * 60)) + 1;
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  return `Day ${day}, ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")} elapsed`;
}

function ContributionBars({ codes }: { codes: ReasonCode[] }) {
  const max = Math.max(...codes.map((item) => Math.abs(item.shap_value ?? 0)), 1);
  return (
    <div className="contribution-chart" role="img" aria-label="Top model contributions">
      <div className="chart-axis" aria-hidden="true" />
      {codes.map((code) => {
        const magnitude = Math.max(8, (Math.abs(code.shap_value ?? 0) / max) * 46);
        const increase = code.direction === "increases_risk";
        return (
          <div className="contribution-row" key={`${code.rank}-${code.feature}`}>
            <span className="feature-name">{featureLabel(code)}</span>
            <div className="bar-track">
              <span
                className={`contribution-bar ${increase ? "is-up" : "is-down"}`}
                style={increase ? { left: "50%", width: `${magnitude}%` } : { right: "50%", width: `${magnitude}%` }}
              />
            </div>
            <span className={increase ? "direction-text is-up" : "direction-text is-down"}>
              {increase ? "↑ fraud" : "↓ fraud"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function parseNarrative(text: string): { summary: string; evidence: string[]; action: string | null } {
  const summary = text.match(/(?:^|\n)NARRATIVE:\s*(.+?)(?=\n+EVIDENCE:|$)/s)?.[1]?.trim();
  const evidenceBlock = text.match(/(?:^|\n)EVIDENCE:\s*\n([\s\S]+?)(?=\n+ACTION:|$)/)?.[1];
  const action = text.match(/(?:^|\n)ACTION:\s*(.+?)\s*$/s)?.[1]?.trim() ?? null;
  const evidence = evidenceBlock
    ? evidenceBlock.split("\n").map((line) => line.replace(/^\s*-\s*/, "").trim()).filter(Boolean)
    : [];
  return { summary: summary ?? text.trim(), evidence, action };
}

function evidenceReading(codes: ReasonCode[]): string {
  const ranked = [...codes].sort((left, right) => left.rank - right.rank);
  const upward = ranked.filter((code) => code.direction === "increases_risk");
  const downward = ranked.filter((code) => code.direction === "decreases_risk");
  const primary = ranked[0];
  const absoluteTotal = ranked.reduce((total, code) => total + Math.abs(code.shap_value ?? 0), 0);
  const primaryShare = primary?.shap_value !== null && primary?.shap_value !== undefined && absoluteTotal > 0
    ? Math.round((Math.abs(primary.shap_value) / absoluteTotal) * 100)
    : null;
  const dominance = primaryShare === null
    ? `${primary ? featureLabel(primary) : "The leading feature"} is the highest-ranked contribution.`
    : `${primary ? featureLabel(primary) : "The leading feature"} is the strongest displayed contribution, accounting for about ${primaryShare}% of the absolute top-evidence magnitude.`;

  if (downward.length === 0) {
    return `${dominance} All ${upward.length} displayed contributions push the detector toward fraud, so there is no counter-signal among the top-ranked evidence.`;
  }
  const counterFeatures = downward.map(featureLabel).join(", ");
  return `${dominance} ${upward.length} contribution${upward.length === 1 ? "" : "s"} push toward fraud, while ${counterFeatures} ${downward.length === 1 ? "acts" : "act"} as counter-evidence. The counter-evidence did not prevent the detector from crossing its frozen threshold.`;
}

function prioritisationReading(rank: number | undefined, total: number | undefined): string {
  if (rank === undefined || total === undefined) {
    return "The frozen detector placed this transaction above its operating threshold. This is an alert for review, not a confirmed fraud label.";
  }
  return `The frozen detector placed this transaction above its operating threshold and ranked it #${rank} among ${total} flagged cases. The rank indicates review priority, not certainty that fraud occurred.`;
}

function reviewFocus(codes: ReasonCode[]): string {
  const counterEvidence = codes.some((code) => code.direction === "decreases_risk");
  const evidenceInstruction = counterEvidence
    ? "Check whether the available business context supports the upward signals or the counter-evidence."
    : "Because the displayed top evidence is one-directional, actively look for business context that could contradict the model output.";
  return `${evidenceInstruction} Verify customer, merchant, device, and transaction-history information in the source system before escalating or closing the alert; those fields are not available in this dataset.`;
}

function amountFromDetail(detail: { amount?: number; transaction_context?: { amount?: number } }): number | undefined {
  return detail.amount ?? detail.transaction_context?.amount;
}

function eventTimeLabel(detail: { timestamp?: string; transaction_context?: { timestamp?: string; elapsed_seconds?: number } }): string {
  const value = detail.timestamp ?? detail.transaction_context?.timestamp;
  if (!value) return elapsedLabel(detail.transaction_context?.elapsed_seconds);
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function briefTextOrNull(value: string | NarrativeView | null | undefined): string | null {
  if (!value) return null;
  const text = typeof value === "string" ? value : value.final_text;
  return text.trim() ? text : null;
}

function signedShap(value: number | null | undefined): string {
  if (value === null || value === undefined) return "Direction only";
  return `${value >= 0 ? "+" : ""}${value.toFixed(4)}`;
}

function valueBucketLabel(value: string | null | undefined): string {
  if (!value) return "";
  return value.replaceAll("_", " ");
}

function payloadText(detail: {
  minimized_payload?: string | Record<string, unknown> | null;
  explanation_comparison?: { minimized_payload?: string | Record<string, unknown> | null };
  data_sent_to_llm?: { payload?: string | Record<string, unknown> };
}): string | null {
  const value = detail.minimized_payload ?? detail.explanation_comparison?.minimized_payload ?? detail.data_sent_to_llm?.payload ?? null;
  if (!value) return null;
  return typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

function NarrativePanel({
  narrative,
  live,
  codes,
  model,
  deliverySummary,
  scoreRank,
  flaggedTotal,
}: {
  narrative: NarrativeView | null;
  live: boolean;
  codes: ReasonCode[];
  model: string;
  deliverySummary: string;
  scoreRank?: number;
  flaggedTotal?: number;
}) {
  if (!narrative) {
    return (
      <div className="narrative-empty">
        <AlertIcon />
        <strong>{live ? "A local explanation has not been generated" : "No saved explanation"}</strong>
        <p>{live ? "Verified case evidence remains available while local generation is optional." : "No explanation text is available for this case."}</p>
      </div>
    );
  }
  const sections = parseNarrative(narrative.final_text);
  return (
    <>
      <article className={`case-brief-panel analyst-brief ${narrative.fallback ? "is-fallback" : ""}`} aria-live="polite">
        <div className="brief-title-row">
          <div><span className="flow-label">Decision support</span><h3>Why this alert needs review</h3></div>
          <span className={`decision-state ${narrative.fallback ? "is-fallback" : "is-accepted"}`}>
            {narrative.fallback ? "Fallback" : "4/4 checks passed"}
          </span>
        </div>
        <div><span>Why it is prioritised</span><p>{prioritisationReading(scoreRank, flaggedTotal)}</p></div>
        <div><span>Evidence synthesis</span><p>{evidenceReading(codes)}</p></div>
        <div className="llm-note-block">
          <span>Locally generated review note <em>No new risk facts allowed</em></span>
          <p>{narrative.fallback ? "The generated candidate was not delivered. The system retained the verified model evidence and substituted a deterministic fallback record." : sections.summary}</p>
        </div>
        <div><span>What the analyst should verify next</span><p>{reviewFocus(codes)}</p></div>
        <p className="brief-boundary"><strong>Why use the LLM?</strong> It converts bounded model evidence into a consistent review note. It is deliberately prevented from inventing merchant, customer, device, or behavioural explanations that the dataset cannot support.</p>
        <footer className="brief-provenance">
          <span>{narrative.fallback ? "Deterministic reason-code fallback" : `${model} · local generation`}</span>
          <span>{narrative.latency_seconds !== null && narrative.latency_seconds !== undefined ? `${narrative.latency_seconds.toFixed(2)}s` : live ? "temporary" : "recorded"}</span>
          <span>{deliverySummary}</span>
        </footer>
      </article>

      <details className="exact-narrative-details">
        <summary>View exact generated text</summary>
        <pre>{narrative.final_text}</pre>
      </details>
      <details className="guardrail-details">
        <summary>{narrative.fallback ? "View guardrail rejection details" : "Verified against four deterministic checks"}</summary>
        <GuardrailBadges checks={narrative.checks} reasons={narrative.check_reasons} />
      </details>
      {narrative.fallback ? (
        <div className="fallback-note">
          <AlertIcon />
          <div>
            <strong>Deterministic reason-code fallback delivered</strong>
            <p>{narrative.fallback_reason?.replaceAll("_", " ") ?? "Narrative guardrail rejected the candidate."}</p>
          </div>
        </div>
      ) : null}
    </>
  );
}

function OperationalComparison({
  detail,
  codes,
}: {
  detail: {
    deterministic_brief?: string | NarrativeView | null;
    guarded_llm_brief?: string | NarrativeView | null;
    llm_brief?: string | NarrativeView | null;
    explanation_comparison?: {
      deterministic_brief?: string | NarrativeView | null;
      guarded_llm_brief?: string | NarrativeView | null;
      llm_candidate?: Record<string, unknown> | null;
      llm_brief?: string | NarrativeView | null;
      delivered_brief?: string | NarrativeView | null;
      minimized_payload?: string | Record<string, unknown> | null;
      validation?: {
        checks?: NarrativeView["checks"];
        check_reasons?: NarrativeView["check_reasons"];
        fallback?: boolean;
        fallback_reason?: string | null;
      } | null;
    };
    validation?: {
      checks?: NarrativeView["checks"];
      check_reasons?: NarrativeView["check_reasons"];
      fallback?: boolean;
      fallback_reason?: string | null;
    } | null;
    fallback_reason?: string | null;
    minimized_payload?: string | Record<string, unknown> | null;
    data_sent_to_llm?: { payload?: string | Record<string, unknown> };
  };
  codes: ReasonCode[];
}) {
  const validation = detail.validation ?? detail.explanation_comparison?.validation ?? null;
  const deterministicValue = briefTextOrNull(detail.deterministic_brief ?? detail.explanation_comparison?.deterministic_brief);
  const guardedValue = briefTextOrNull(
    detail.guarded_llm_brief
    ?? detail.llm_brief
    ?? detail.explanation_comparison?.guarded_llm_brief
    ?? detail.explanation_comparison?.llm_brief,
  );
  const deterministic = deterministicValue ?? "Not available";
  const guarded = guardedValue ?? "Not available";
  const delivered = briefTextOrNull(detail.explanation_comparison?.delivered_brief) ?? deterministicValue ?? guardedValue ?? "Not available";
  const payload = payloadText(detail);
  const llmCandidate = detail.explanation_comparison?.llm_candidate ?? null;
  const candidateEvidence = Array.isArray(llmCandidate?.evidence) ? llmCandidate.evidence : [];
  const expectedEvidenceCount = codes.length;
  const candidateSummary = typeof llmCandidate?.summary === "string" ? llmCandidate.summary : guarded;
  const fallbackReason = validation?.fallback_reason ?? detail.fallback_reason;
  const deliveredSource = validation?.fallback
    ? "Delivered analyst brief · deterministic fallback"
    : "Delivered analyst brief · guarded local-LLM accepted";
  return (
    <section className="operational-comparison" aria-labelledby="comparison-title">
      <div className="section-heading-line">
        <div><span className="eyebrow">S0 local-LLM evaluation</span><h2 id="comparison-title">SHAP, deterministic brief, guarded local-LLM brief, validation/fallback</h2></div>
      </div>
      <div className="brief-comparison-grid">
        <article>
          <span className="comparison-label">Raw SHAP reason codes</span>
          <ol className="reason-code-list">
            {codes.map((code) => (
              <li key={`${code.rank}-${code.feature}`}>
                <strong>{code.rank}. {featureLabel(code)}</strong>
                <span>{code.direction === "increases_risk" ? "Pushes toward fraud" : "Pushes toward legitimate"}{code.value_bucket ? ` · ${valueBucketLabel(code.value_bucket)}` : ""}</span>
                <code>{code.feature} · SHAP {signedShap(code.shap_value)}</code>
              </li>
            ))}
          </ol>
        </article>
        <article>
          <span className="comparison-label">Deterministic brief</span>
          <p>{deterministic}</p>
        </article>
        <article>
          <span className="comparison-label">Guarded local-LLM brief</span>
          <p>{candidateSummary}</p>
          <small>
            Structured evidence retained: {candidateEvidence.length}/{expectedEvidenceCount}. {validation?.fallback
              ? "This candidate failed the delivery contract and was replaced."
              : "The delivered sentence is shorter than the full deterministic brief and may name only the leading signal."}
          </small>
          {llmCandidate ? (
            <details className="exact-narrative-details">
              <summary>Inspect complete structured local-LLM candidate</summary>
              <pre>{JSON.stringify(llmCandidate, null, 2)}</pre>
            </details>
          ) : null}
        </article>
        <article>
          <span className={validation?.fallback ? "comparison-label is-tampered" : "comparison-label is-original"}>{deliveredSource}</span>
          <p>{delivered}</p>
          {validation?.fallback ? <small>Fallback is active; the Ollama candidate was not delivered to the analyst.</small> : <small>All four checks passed on the structured candidate. This is delivery compliance, not evidence that the sentence adds analyst value.</small>}
        </article>
      </div>
      <div className="operational-validation-grid">
        <div>
          <strong>Validation and fallback</strong>
          <p>{validation?.fallback ? "The guarded candidate was replaced by deterministic fallback." : "The delivered brief is bounded by deterministic validation."}</p>
          {fallbackReason ? <small>{fallbackReason.replaceAll("_", " ")}</small> : null}
          <GuardrailBadges checks={validation?.checks} reasons={validation?.check_reasons} />
        </div>
        <div>
          <strong>Minimized payload sent to local LLM</strong>
          {payload ? <pre className="evidence-payload">{payload}</pre> : <p className="muted">Payload details are unavailable.</p>}
        </div>
      </div>
      <p className="brief-boundary"><strong>Boundary:</strong> all entities and transactions in this route are synthetic. The analyst decides the next action after reviewing available evidence.</p>
    </section>
  );
}

function ActivityTimeline({ events }: { events: WorkflowActivityEvent[] }) {
  if (events.length === 0) {
    return <p className="activity-empty">No local analyst activity has been recorded.</p>;
  }
  return (
    <ol className="activity-timeline">
      {events.map((event) => (
        <li key={event.id}>
          <span className="activity-marker" aria-hidden="true" />
          <div>
            <strong>{eventLabel(event)}</strong>
            <span>{workflowLabel(event.to_status)} · revision {event.revision}</span>
            <time dateTime={event.created_at}>{timeLabel(event.created_at)}</time>
          </div>
        </li>
      ))}
    </ol>
  );
}

export function Investigation({ mode }: { mode: ReviewMode }) {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const { mode: narrativeMode, setMode, openProvenance, health } = useDemoContext();
  const remote = useRemoteData(() => (mode === "operational" ? api.operationalCase : api.researchCase)(caseId), [mode, caseId]);
  const workflowRemote = useRemoteData(
    () => (mode === "operational" ? api.operationalWorkflow : api.workflow)(caseId),
    [mode, caseId],
  );
  const activityRemote = useRemoteData(
    () => (mode === "operational" ? api.operationalWorkflowActivity : api.workflowActivity)(caseId),
    [mode, caseId],
  );
  const summaryRemote = useRemoteData(
    () => (mode === "operational" ? api.operationalWorkflowSummary : api.workflowSummary)(),
    [mode],
  );
  const [workflowOverride, setWorkflowOverride] = useState<WorkflowRecord>();
  const [note, setNote] = useState("");
  const [disposition, setDisposition] = useState<WorkflowDisposition | "">("");
  const [workflowError, setWorkflowError] = useState<Error>();
  const [saving, setSaving] = useState(false);
  const [liveNarrative, setLiveNarrative] = useState<LiveNarrativeResponse>();
  const [liveError, setLiveError] = useState<Error>();
  const [liveLoading, setLiveLoading] = useState(false);

  useEffect(() => {
    setLiveNarrative(undefined);
    setLiveError(undefined);
    setWorkflowOverride(undefined);
    setWorkflowError(undefined);
    setMode("recorded");
  }, [caseId, setMode]);

  const workflow = workflowOverride ?? workflowRemote.data;
  useEffect(() => {
    if (!workflow) return;
    setNote(workflow.note);
    setDisposition(workflow.disposition ?? "");
  }, [workflow]);

  const detail = remote.data;
  const codes = useMemo(
    () => detail?.explanation_comparison?.raw_reason_codes
      ?? detail?.raw_reason_codes
      ?? detail?.semantic_reason_codes
      ?? detail?.shap_reason_codes
      ?? detail?.reason_codes
      ?? detail?.codes
      ?? [],
    [detail],
  );
  const recorded = caseNarrative(detail);

  const generateLive = async () => {
    if (!detail) return;
    setLiveLoading(true);
    setLiveError(undefined);
    try {
      setLiveNarrative(await api.liveNarrative(detail.case_id));
    } catch (error) {
      setLiveError(error instanceof Error ? error : new Error("Live replay could not be generated."));
    } finally {
      setLiveLoading(false);
    }
  };

  const saveWorkflow = async (status: WorkflowStatus, openNext = false) => {
    if (!detail || !workflow) return;
    setSaving(true);
    setWorkflowError(undefined);
    try {
      const updated = await (mode === "operational" ? api.updateOperationalWorkflow : api.updateWorkflow)(detail.case_id, {
        revision: workflow.revision,
        status,
        disposition: disposition || null,
        note,
      });
      setWorkflowOverride(updated);
      activityRemote.reload();

      if (openNext) {
        const [casePayload, workflowPayload] = await Promise.all([
          (mode === "operational" ? api.operationalCases : api.researchCases)({ limit: 200 }),
          (mode === "operational" ? api.operationalWorkflows : api.workflows)(),
        ]);
        const cases = normalizeCases(casePayload).items;
        const statuses = new Map(workflowPayload.items.map((item) => [item.case_id, item.status]));
        const next = cases.find((item) => item.case_id !== detail.case_id && (statuses.get(item.case_id) ?? "unreviewed") === "unreviewed");
        navigate(next
          ? mode === "operational" ? `/operational/cases/${next.case_id}` : `/research/cases/${next.case_id}`
          : `/queue?source=${mode}&workflow_status=unreviewed`);
      }
    } catch (error) {
      setWorkflowError(error instanceof Error ? error : new Error("Workflow could not be saved."));
      if (
        error instanceof ApiError
        && ["workflow_revision_conflict", "workflow_evidence_mismatch"].includes(error.code ?? "")
      ) {
        setWorkflowOverride(undefined);
      }
      workflowRemote.reload();
      activityRemote.reload();
    } finally {
      setSaving(false);
    }
  };

  if (remote.loading || workflowRemote.loading) return <LoadingState label="Loading investigation workspace" />;
  if (remote.error) return <ErrorState error={remote.error} retry={remote.reload} />;
  if (workflowRemote.error) return <ErrorState error={workflowRemote.error} retry={workflowRemote.reload} />;
  if (!detail || !workflow) return null;

  const currentNarrative = narrativeMode === "live" ? liveNarrative ?? null : recorded;
  const isUnreviewed = workflow.status === "unreviewed";
  const isComplete = workflow.status === "review_complete";
  const ollamaModel = health?.ollama?.model ?? "llama3:8b";
  const totalBriefs = summaryRemote.data?.total;
  const fallbackBriefs = summaryRemote.data?.recorded_fallback;
  const deliverySummary = totalBriefs !== undefined && fallbackBriefs !== undefined
    ? `${totalBriefs - fallbackBriefs}/${totalBriefs} accepted · ${fallbackBriefs} fallback`
    : "Guarded delivery";

  return (
    <div className="route-page route-enter investigation-page">
      <section className="page-heading investigation-heading">
        <div>
          <Link className="back-link" to={`/queue?source=${mode}`}>
            ← Alert Queue
          </Link>
          <span className="eyebrow">{mode === "operational" ? "Operational simulation" : "Research benchmark"}</span>
          <h1>{mode === "operational" ? "Transaction" : "Case"} <code>{detail.transaction_id ?? detail.case_id}</code></h1>
          <div className="case-heading-meta">
            <span>Rank <strong>#{detail.rank ?? detail.score_rank ?? "—"} of {detail.flagged_total ?? "—"}</strong></span>
            <span>Amount <strong>{amountLabel(amountFromDetail(detail))}</strong></span>
            <span>Time <strong>{eventTimeLabel(detail)}</strong></span>
          </div>
        </div>
        <div className="heading-actions">
          <WorkflowBadge status={workflow.status} />
          <button className="button secondary" onClick={openProvenance} type="button"><FingerprintIcon /> Evidence chain</button>
        </div>
      </section>

      <div className="investigation-layout">
        <aside className="decision-rail" aria-label="Analyst decision workspace">
          <div className="decision-rail-heading">
            <div><span className="eyebrow">Analyst action</span><h2>Route this alert</h2></div>
            <WorkflowBadge status={workflow.status} />
          </div>

          {!workflow.evidence_compatible ? (
            <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Evidence chain changed</strong><p>Restart the review to bind a blank workflow record to the current evidence.</p></div></div>
          ) : null}
          {workflowError ? (
            <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Workflow save failed</strong><p>{workflowError.message}</p></div></div>
          ) : null}

          <div className="workflow-current-state">
            <span>Current state</span>
            <strong>{workflowLabel(workflow.status)}</strong>
            <small>Revision {workflow.revision}</small>
          </div>

          <label className="decision-field">
            <span>Action</span>
            <select disabled={saving || !workflow.evidence_compatible} value={disposition} onChange={(event) => setDisposition(event.target.value as WorkflowDisposition | "")}>
              <option value="">Select the next action</option>
              <option value="suspicious">Escalate for investigation</option>
              <option value="not_suspicious">Close without escalation</option>
              <option value="inconclusive">Request additional information</option>
            </select>
          </label>

          <label className="decision-field note-field">
            <span>Analyst note</span>
            <textarea disabled={saving || !workflow.evidence_compatible} maxLength={2000} onChange={(event) => setNote(event.target.value)} placeholder="Record the evidence reviewed and the reason for this action." value={note} />
            <small>{note.length}/2000 · stored in the local workflow database</small>
          </label>

          <div className="decision-actions">
            {!workflow.evidence_compatible ? (
              <button className="button primary" disabled={saving} onClick={() => saveWorkflow("in_review")} type="button">Restart on current evidence</button>
            ) : isComplete ? (
              <button className="button secondary" disabled={saving} onClick={() => saveWorkflow("in_review")} type="button">Reopen review</button>
            ) : (
              <>
                <button className="button secondary" disabled={saving} onClick={() => saveWorkflow(isUnreviewed ? "in_review" : workflow.status)} type="button">Save draft</button>
                <button className="button secondary" disabled={saving} onClick={() => saveWorkflow("needs_follow_up")} type="button">Request info</button>
                <button className="button primary" disabled={saving || !disposition} onClick={() => saveWorkflow("review_complete")} type="button">Confirm & close</button>
                <button className="button next-button" disabled={saving || !disposition} onClick={() => saveWorkflow("review_complete", true)} type="button">Save & open next <ArrowIcon size={15} /></button>
              </>
            )}
          </div>

          <details className="activity-section">
            <summary><strong>Activity</strong><span>{workflow.activity_count} events</span></summary>
            {activityRemote.loading ? <p className="activity-empty">Loading local activity…</p> : null}
            {activityRemote.error ? <p className="activity-empty">Activity could not be loaded.</p> : null}
            {activityRemote.data ? <ActivityTimeline events={activityRemote.data.items} /> : null}
          </details>
        </aside>

        <div className="investigation-evidence-stack">
          {mode === "operational" ? <OperationalComparison detail={detail} codes={codes} /> : null}

          {mode === "operational" ? (
            <Link className="guardrail-cta" to={`/assurance/narratives?mode=operational&case_id=${detail.case_id}`}>
              <ShieldIcon />
              <span><strong>Open Explanation Assurance</strong><small>Challenge the structured brief with controlled semantic failures.</small></span>
              <ArrowIcon />
            </Link>
          ) : null}

          {mode === "research" ? <section className="narrative-column" aria-labelledby="narrative-title">
            <div className="section-heading-line narrative-heading-line">
              <div><span className="eyebrow">Why this alert</span><h2 id="narrative-title">Evidence brief</h2></div>
              <button className="button secondary compact-action" onClick={() => setMode(narrativeMode === "recorded" ? "live" : "recorded")} type="button">
                {narrativeMode === "recorded" ? "Regenerate locally" : "Return to saved brief"}
              </button>
            </div>

            {narrativeMode === "live" ? (
              <>
                <p className="demo-only-label">Temporary local generation · not saved to the case record</p>
                <div className="live-action-band">
                  <div><strong>Generate a fresh explanation</strong><p>Uses the same verified evidence. The result is temporary and does not replace the saved explanation.</p></div>
                  <button className="button primary" disabled={liveLoading} onClick={generateLive} type="button">{liveLoading ? "Generating…" : "Generate explanation"}</button>
                </div>
              </>
            ) : null}
            {liveError ? (
              <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Live service unavailable</strong><p>{liveError.message} Recorded evidence remains unchanged.</p></div></div>
            ) : null}
            <NarrativePanel
              codes={codes}
              live={narrativeMode === "live"}
              model={ollamaModel}
              narrative={currentNarrative}
              deliverySummary={deliverySummary}
              scoreRank={detail.score_rank}
              flaggedTotal={detail.flagged_total}
            />

            <details className="data-disclosure">
              <summary>Inspect bounded local-LLM input <ArrowIcon size={15} /></summary>
              {detail.data_sent_to_llm?.payload ? (
                <pre className="evidence-payload">
                  {typeof detail.data_sent_to_llm.payload === "string"
                    ? detail.data_sent_to_llm.payload
                    : JSON.stringify(detail.data_sent_to_llm.payload, null, 2)}
                </pre>
              ) : null}
              <div className="disclosure-grid">
                <div><strong>Included</strong><ul>{(detail.data_sent_to_llm?.included ?? ["Coarse risk bucket", "Feature names", "Direction and rank"]).map((item) => <li key={item}>{item}</li>)}</ul></div>
                <div><strong>Excluded</strong><ul>{(detail.data_sent_to_llm?.excluded ?? ["Case identifier", "Raw transaction row", "Exact feature values", "Detector score or probability", "SHAP magnitudes", "Historical label"]).map((item) => <li key={item}>{item}</li>)}</ul></div>
              </div>
            </details>

            <Link className="guardrail-cta" to={`/assurance/narratives?mode=research&case_id=${detail.case_id}`}>
              <ShieldIcon />
              <span><strong>Open Explanation Assurance</strong><small>Challenge the saved brief with controlled failures.</small></span>
              <ArrowIcon />
            </Link>
          </section> : null}

          <section aria-label="Verified transaction context" className="transaction-context-strip compact-context">
            <div><span>{mode === "operational" ? "Transaction amount" : "Dataset amount"}</span><strong>{amountLabel(amountFromDetail(detail))}</strong><small>{mode === "operational" ? "Synthetic transaction value." : "Currency not identified."}</small></div>
            <div><span>{mode === "operational" ? "Transaction time" : "Elapsed dataset time"}</span><strong>{eventTimeLabel(detail)}</strong><small>{mode === "operational" ? "Synthetic stream timestamp." : "Relative time, not a calendar timestamp."}</small></div>
            <div className="context-boundary"><span>Available context</span><strong>{mode === "operational" ? "Past-only behaviour fields." : "Amount and elapsed time only."}</strong><small>{mode === "operational" ? "Customer and terminal entities are synthetic." : "Business fields are not present in the source dataset."}</small></div>
          </section>

          <details className="full-evidence-details">
            <summary><span><strong>Full model evidence</strong><small>Threshold, SHAP chart, reason-code table, and exact contributions</small></span><ArrowIcon size={15} /></summary>
            <section className="evidence-column" aria-labelledby="evidence-title">
              <div className="section-heading-line">
                <div><span className="eyebrow">Immutable evidence</span><h2 id="evidence-title">Detector decision and attribution</h2></div>
                <span className="evidence-state">VERIFIED MODEL OUTPUT</span>
              </div>
              <dl className="metric-strip">
                <div><dt>Detector output</dt><dd>{(detail.detector_flagged ?? detail.pred === 1) ? "Above threshold" : "Below threshold"}</dd></div>
                <div><dt>Frozen threshold</dt><dd>{detail.frozen_threshold === null || detail.frozen_threshold === undefined
                  ? detail.threshold === null || detail.threshold === undefined ? "Configured" : detail.threshold.toFixed(4)
                  : detail.frozen_threshold.toFixed(4)}</dd></div>
                <div><dt>Detector order (not severity)</dt><dd>#{detail.rank ?? detail.score_rank ?? "—"} of {detail.flagged_total ?? "—"}</dd></div>
                <div><dt>Evidence chain</dt><dd>{workflow.evidence_compatible ? "Compatible" : "Mismatch"}</dd></div>
              </dl>

              <div className="chart-heading">
                <div><h3>Top model contributions</h3><p>{mode === "operational" ? "Signed SHAP attributions show how readable past-only features moved this model output." : "Signed SHAP attributions show how anonymous components moved this model output."}</p></div>
                <div className="chart-legend"><span className="is-up" /> Toward fraud <span className="is-down" /> Toward legitimate</div>
              </div>
              {codes.length > 0 ? <ContributionBars codes={codes} /> : <p className="muted">No contribution data is available.</p>}

              <div className="reason-table-wrap">
                <h3>Standardized reason codes</h3>
                <p className="feature-boundary-note">{mode === "operational" ? "Reason labels describe synthetic, past-only transaction-history features; they are not real customer or terminal facts." : "V1–V28 are anonymised PCA components and cannot be translated into merchant, device, customer, or transaction-category meanings."}</p>
                <table className="data-table reason-table">
                  <thead><tr><th>Rank</th><th>{mode === "operational" ? "Readable feature" : "Anonymised feature"}</th><th>Effect on score</th><th>SHAP contribution</th></tr></thead>
                  <tbody>
                    {codes.map((code) => (
                      <tr key={`${code.rank}-${code.feature}`}>
                        <td>{code.rank}</td>
                        <td><code>{featureLabel(code)}</code></td>
                        <td>{contributionLabel(code)}</td>
                        <td className={code.direction === "increases_risk" ? "numeric risk-up" : "numeric risk-down"}>
                          {code.shap_value === null || code.shap_value === undefined ? "Direction only" : code.shap_value.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </details>
        </div>
      </div>
    </div>
  );
}
