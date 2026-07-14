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

function ContributionBars({ codes }: { codes: ReasonCode[] }) {
  const max = Math.max(...codes.map((item) => Math.abs(item.shap_value ?? 0)), 1);
  return (
    <div className="contribution-chart" role="img" aria-label="Top recorded SHAP contributions">
      <div className="chart-axis" aria-hidden="true" />
      {codes.map((code) => {
        const magnitude = Math.max(8, (Math.abs(code.shap_value ?? 0) / max) * 46);
        const increase = code.direction === "increases_risk";
        return (
          <div className="contribution-row" key={`${code.rank}-${code.feature}`}>
            <span className="feature-name">{code.feature}</span>
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

function NarrativePanel({ narrative, live }: { narrative: NarrativeView | null; live: boolean }) {
  if (!narrative) {
    return (
      <div className="narrative-empty">
        <AlertIcon />
        <strong>{live ? "Live replay has not been generated" : "No recorded narrative"}</strong>
        <p>{live ? "Recorded evidence remains available while local generation is optional." : "The snapshot did not provide narrative text for this case."}</p>
      </div>
    );
  }
  return (
    <>
      <div className="narrative-state-row">
        <span className={`decision-state ${narrative.fallback ? "is-fallback" : "is-accepted"}`}>
          {narrative.fallback ? "Fallback active" : "Explanation verified"}
        </span>
        {narrative.latency_seconds !== null && narrative.latency_seconds !== undefined ? (
          <span>{narrative.latency_seconds.toFixed(2)}s generation</span>
        ) : null}
      </div>
      {!live ? <p className="recorded-label">Recorded strict-prompt arm · Reportable frozen output</p> : null}
      <div className="narrative-copy" aria-live="polite">{narrative.final_text}</div>
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

export function Investigation() {
  const { caseId = "" } = useParams();
  const navigate = useNavigate();
  const { mode, setMode, openProvenance } = useDemoContext();
  const remote = useRemoteData(() => api.case(caseId), [caseId]);
  const workflowRemote = useRemoteData(() => api.workflow(caseId), [caseId]);
  const activityRemote = useRemoteData(() => api.workflowActivity(caseId), [caseId]);
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
  const codes = useMemo(() => detail?.reason_codes ?? detail?.codes ?? [], [detail]);
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
      const updated = await api.updateWorkflow(detail.case_id, {
        revision: workflow.revision,
        status,
        disposition: disposition || null,
        note,
      });
      setWorkflowOverride(updated);
      activityRemote.reload();

      if (openNext) {
        const [casePayload, workflowPayload] = await Promise.all([
          api.cases({ limit: 200 }),
          api.workflows(),
        ]);
        const cases = normalizeCases(casePayload).items;
        const statuses = new Map(workflowPayload.items.map((item) => [item.case_id, item.status]));
        const next = cases.find((item) => item.case_id !== detail.case_id && (statuses.get(item.case_id) ?? "unreviewed") === "unreviewed");
        navigate(next ? `/cases/${next.case_id}` : "/queue?workflow_status=unreviewed");
      }
    } catch (error) {
      setWorkflowError(error instanceof Error ? error : new Error("Workflow could not be saved."));
      if (error instanceof ApiError && error.code === "workflow_revision_conflict") {
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

  const currentNarrative = mode === "live" ? liveNarrative ?? null : recorded;
  const isUnreviewed = workflow.status === "unreviewed";
  const isComplete = workflow.status === "review_complete";

  return (
    <div className="route-page route-enter investigation-page">
      <section className="page-heading investigation-heading">
        <div>
          <Link className="back-link" to="/queue">← Work Queue</Link>
          <span className="eyebrow">Investigation Workspace</span>
          <h1>Case <code>{detail.case_id}</code></h1>
          <p>Review immutable detector evidence and record a provisional local decision.</p>
        </div>
        <div className="heading-actions">
          <WorkflowBadge status={workflow.status} />
          <span className={`risk-hero is-${String(detail.risk_bucket).toLowerCase()}`}>
            <small>Recorded risk</small>
            <strong>{detail.risk_bucket}</strong>
          </span>
          <button className="button secondary" onClick={openProvenance} type="button"><FingerprintIcon /> Evidence chain</button>
        </div>
      </section>

      <div className="investigation-layout">
        <div className="investigation-evidence-stack">
          <section className="evidence-column" aria-labelledby="evidence-title">
            <div className="section-heading-line">
              <div><span className="eyebrow">Immutable evidence</span><h2 id="evidence-title">Detector decision and attribution</h2></div>
              <span className="evidence-state">RECORDED / VERIFIED</span>
            </div>
            <dl className="metric-strip">
              <div><dt>Model score</dt><dd>{detail.score.toFixed(4)}</dd></div>
              <div><dt>Frozen threshold</dt><dd>{detail.threshold === null || detail.threshold === undefined ? "Manifest" : detail.threshold.toFixed(4)}</dd></div>
              <div><dt>Detector</dt><dd>{(detail.detector_flagged ?? detail.pred === 1) ? "Flagged" : "Not flagged"}</dd></div>
              <div><dt>Evidence chain</dt><dd>{workflow.evidence_compatible ? "Compatible" : "Mismatch"}</dd></div>
            </dl>

            <div className="chart-heading">
              <div><h3>Top recorded SHAP contributions</h3><p>Signed model attributions, not causal claims or business feature meanings.</p></div>
              <div className="chart-legend"><span className="is-up" /> Toward fraud <span className="is-down" /> Toward legitimate</div>
            </div>
            {codes.length > 0 ? <ContributionBars codes={codes} /> : <p className="muted">No recorded contribution list is available.</p>}

            <div className="reason-table-wrap">
              <h3>Standardized reason codes</h3>
              <table className="data-table reason-table">
                <thead><tr><th>Rank</th><th>Anonymised feature</th><th>Recorded direction</th><th>SHAP contribution</th></tr></thead>
                <tbody>
                  {codes.map((code) => (
                    <tr key={`${code.rank}-${code.feature}`}>
                      <td>{code.rank}</td>
                      <td><code>{code.feature}</code></td>
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

          <section className="narrative-column" aria-labelledby="narrative-title">
            <div className="section-heading-line narrative-heading-line">
              <div><span className="eyebrow">Validated explanation</span><h2 id="narrative-title">Narrative delivery</h2></div>
              <div className="mode-switch" aria-label="Narrative mode">
                <button aria-pressed={mode === "recorded"} className={mode === "recorded" ? "is-active" : ""} onClick={() => setMode("recorded")} type="button">Recorded</button>
                <button aria-pressed={mode === "live"} className={mode === "live" ? "is-active" : ""} onClick={() => setMode("live")} type="button">Live replay</button>
              </div>
            </div>

            {mode === "live" ? (
              <>
                <p className="demo-only-label">Live replay · Demo-only; not a reported G5 result</p>
                <div className="live-action-band">
                  <div><strong>Optional local replay</strong><p>Uses the same recorded evidence. It is ephemeral and never reported as G5 output.</p></div>
                  <button className="button primary" disabled={liveLoading} onClick={generateLive} type="button">{liveLoading ? "Generating…" : "Generate live replay"}</button>
                </div>
              </>
            ) : null}
            {liveError ? (
              <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Live service unavailable</strong><p>{liveError.message} Recorded evidence remains unchanged.</p></div></div>
            ) : null}
            <NarrativePanel narrative={currentNarrative} live={mode === "live"} />

            <details className="data-disclosure">
              <summary>Data sent to local LLM <ArrowIcon size={15} /></summary>
              {detail.data_sent_to_llm?.payload ? <pre className="evidence-payload">{detail.data_sent_to_llm.payload}</pre> : null}
              <div className="disclosure-grid">
                <div><strong>Included</strong><ul>{(detail.data_sent_to_llm?.included ?? ["Case identifier", "Coarse risk bucket", "Feature names", "Direction and rank"]).map((item) => <li key={item}>{item}</li>)}</ul></div>
                <div><strong>Excluded</strong><ul>{(detail.data_sent_to_llm?.excluded ?? ["Raw transaction row", "Exact feature values", "Detector score or probability", "SHAP magnitudes", "Historical label"]).map((item) => <li key={item}>{item}</li>)}</ul></div>
              </div>
            </details>

            <Link className="guardrail-cta" to={`/assurance/narratives?case_id=${detail.case_id}`}>
              <ShieldIcon />
              <span><strong>Open Narrative Assurance</strong><small>Challenge this evidence with controlled validator mutations.</small></span>
              <ArrowIcon />
            </Link>
          </section>

        </div>

        <aside className="decision-rail" aria-label="Analyst decision workspace">
          <div className="decision-rail-heading">
            <div><span className="eyebrow">Local workflow</span><h2>Review decision</h2></div>
            <WorkflowBadge status={workflow.status} />
          </div>

          {!workflow.evidence_compatible ? (
            <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Evidence chain changed</strong><p>The previous local decision is hidden. Restart review to bind a blank workflow record to the current evidence.</p></div></div>
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
            <span>Provisional assessment</span>
            <select disabled={isUnreviewed || saving} value={disposition} onChange={(event) => setDisposition(event.target.value as WorkflowDisposition | "")}>
              <option value="">Select an assessment</option>
              <option value="suspicious">Suspicious</option>
              <option value="not_suspicious">Not suspicious</option>
              <option value="inconclusive">Inconclusive</option>
            </select>
          </label>

          <label className="decision-field note-field">
            <span>Analyst note</span>
            <textarea disabled={isUnreviewed || saving} maxLength={2000} onChange={(event) => setNote(event.target.value)} placeholder="Record the evidence considered and the next action." value={note} />
            <small>{note.length}/2000 · stored only in the local workflow database</small>
          </label>

          <div className="decision-actions">
            {isUnreviewed ? (
              <button className="button primary" disabled={saving} onClick={() => saveWorkflow("in_review")} type="button">{saving ? "Starting…" : workflow.evidence_compatible ? "Start review" : "Restart on current evidence"}</button>
            ) : isComplete ? (
              <button className="button secondary" disabled={saving} onClick={() => saveWorkflow("in_review")} type="button">Reopen review</button>
            ) : (
              <>
                <button className="button secondary" disabled={saving} onClick={() => saveWorkflow(workflow.status)} type="button">Save review</button>
                <button className="button secondary" disabled={saving} onClick={() => saveWorkflow("needs_follow_up")} type="button">Needs follow-up</button>
                <button className="button primary" disabled={saving || !disposition} onClick={() => saveWorkflow("review_complete")} type="button">Complete review</button>
                <button className="button next-button" disabled={saving || !disposition} onClick={() => saveWorkflow("review_complete", true)} type="button">Save & open next <ArrowIcon size={15} /></button>
              </>
            )}
          </div>

          <div className="workflow-boundary-note">
            <strong>Provisional local decision</strong>
            <p>Not fraud ground truth. Not included in G0–G7, G4, G5, or reported results.</p>
          </div>

          <section className="activity-section" aria-labelledby="activity-title">
            <div><h3 id="activity-title">Analyst activity</h3><span>{workflow.activity_count} events</span></div>
            {activityRemote.loading ? <p className="activity-empty">Loading local activity…</p> : null}
            {activityRemote.error ? <p className="activity-empty">Activity could not be loaded.</p> : null}
            {activityRemote.data ? <ActivityTimeline events={activityRemote.data.items} /> : null}
          </section>
        </aside>
      </div>
    </div>
  );
}
