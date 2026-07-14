import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { normalizeCases } from "../api/normalize";
import type { CaseDetail, DemoScenario, ReasonCode, WorkflowRecord, WorkflowStatus } from "../api/types";
import { ArrowIcon, SearchIcon } from "../components/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { useDemoContext } from "../components/DemoContext";
import { WorkflowBadge } from "../components/StatusBadge";
import { useRemoteData } from "../components/useRemoteData";

function topReasonLabel(reason: ReasonCode | string | null | undefined): string {
  if (!reason) return "Not recorded";
  if (typeof reason === "string") return reason;
  return `${reason.feature} · ${reason.direction === "increases_risk" ? "increases risk" : "decreases risk"}`;
}

function narrativeStatus(item: CaseDetail): string {
  if (item.recorded_narrative_status) return item.recorded_narrative_status;
  if (item.recorded_fallback) return "Fallback";
  const narrative = item.recorded_narrative ?? item.narrative;
  if (!narrative) return "Unavailable";
  return narrative.fallback ? "Fallback" : "Verified";
}

function defaultWorkflow(caseId: number): WorkflowRecord {
  return {
    case_id: caseId,
    status: "unreviewed",
    disposition: null,
    note: "",
    revision: 0,
    created_at: null,
    updated_at: null,
    evidence_compatible: true,
    activity_count: 0,
  };
}

function dateLabel(value: string | null): string {
  if (!value) return "Not started";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function ScenarioShortcut({ scenario, open }: { scenario: DemoScenario; open: (scenario: DemoScenario) => void }) {
  return (
    <button className="scenario-shortcut" onClick={() => open(scenario)} type="button">
      <span className={`scenario-index is-${scenario.kind ?? scenario.key ?? "case"}`} aria-hidden="true" />
      <span>
        <strong>{scenario.title ?? scenario.label ?? "Curated case"}</strong>
        <small>Case {scenario.case_id}</small>
      </span>
      <p>{scenario.description}</p>
      <ArrowIcon />
    </button>
  );
}

export function CaseQueue() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState<Error>();
  const [startingCase, setStartingCase] = useState<number>();
  const navigate = useNavigate();
  const { scenarios } = useDemoContext();
  const riskBucket = params.get("risk_bucket") ?? "";
  const recordedFallback = params.get("recorded_fallback") ?? "";
  const workflowStatus = params.get("workflow_status") ?? "";

  const casesRemote = useRemoteData(
    () => api.cases({
      risk_bucket: riskBucket,
      recorded_fallback: recordedFallback,
      limit: 200,
    }),
    [riskBucket, recordedFallback],
  );
  const workflowsRemote = useRemoteData(api.workflows, []);
  const summaryRemote = useRemoteData(api.workflowSummary, []);

  const response = useMemo(
    () => (casesRemote.data ? normalizeCases(casesRemote.data) : { items: [], total: 0 }),
    [casesRemote.data],
  );
  const workflowMap = useMemo(
    () => new Map((workflowsRemote.data?.items ?? []).map((item) => [item.case_id, item])),
    [workflowsRemote.data],
  );
  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return response.items
      .map((item) => ({ item, workflow: workflowMap.get(item.case_id) ?? defaultWorkflow(item.case_id) }))
      .filter(({ item, workflow }) => {
        if (workflowStatus && workflow.status !== workflowStatus) return false;
        if (!needle) return true;
        return String(item.case_id).includes(needle) || topReasonLabel(item.top_reason).toLowerCase().includes(needle);
      });
  }, [response.items, workflowMap, workflowStatus, search]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const openScenario = (scenario: DemoScenario) => {
    if (scenario.kind === "attack" || scenario.key === "attack") {
      navigate(`/assurance/narratives?case_id=${scenario.case_id}`);
    } else {
      navigate(`/cases/${scenario.case_id}`);
    }
  };

  const openCase = async (caseId: number, workflow: WorkflowRecord) => {
    if (workflow.status !== "unreviewed" && workflow.evidence_compatible) {
      navigate(`/cases/${caseId}`);
      return;
    }
    setStartingCase(caseId);
    setActionError(undefined);
    try {
      await api.updateWorkflow(caseId, {
        revision: workflow.revision,
        status: "in_review",
        disposition: workflow.disposition,
        note: workflow.note,
      });
      navigate(`/cases/${caseId}`);
    } catch (error) {
      setActionError(error instanceof Error ? error : new Error("Review could not be started."));
      workflowsRemote.reload();
      summaryRemote.reload();
    } finally {
      setStartingCase(undefined);
    }
  };

  const startNextReview = async () => {
    const next = rows.find(({ workflow }) => workflow.status === "unreviewed");
    if (!next) {
      setActionError(new Error("No unreviewed case matches the current filters."));
      return;
    }
    await openCase(next.item.case_id, next.workflow);
  };

  const counts = summaryRemote.data?.counts;
  const loading = casesRemote.loading || workflowsRemote.loading || summaryRemote.loading;
  const error = casesRemote.error ?? workflowsRemote.error ?? summaryRemote.error;

  return (
    <div className="route-page route-enter operations-page">
      <section className="page-heading queue-heading">
        <div>
          <span className="eyebrow">Operations</span>
          <h1>Work Queue</h1>
          <p>Prioritised model-flagged cases backed by the frozen detector and explanation chain.</p>
        </div>
        <div className="heading-actions">
          <div className="heading-stat compact">
            <strong>{counts?.unreviewed ?? "—"}</strong>
            <span>awaiting review</span>
          </div>
          <button className="button primary" disabled={loading || startingCase !== undefined} onClick={startNextReview} type="button">
            {startingCase !== undefined ? "Starting…" : "Start next review"}
            <ArrowIcon size={15} />
          </button>
        </div>
      </section>

      <section aria-label="Workflow summary" className="operations-ledger">
        <div><span>Total flagged</span><strong>{summaryRemote.data?.total ?? "—"}</strong></div>
        <div><span>Unreviewed</span><strong>{counts?.unreviewed ?? "—"}</strong></div>
        <div><span>In review</span><strong>{counts?.in_review ?? "—"}</strong></div>
        <div><span>Needs follow-up</span><strong>{counts?.needs_follow_up ?? "—"}</strong></div>
        <div><span>Review complete</span><strong>{counts?.review_complete ?? "—"}</strong></div>
        <div><span>Narrative fallback</span><strong>{summaryRemote.data?.recorded_fallback ?? "—"}</strong></div>
      </section>

      {actionError ? (
        <div className="degraded-state queue-action-error" role="alert">
          <div><strong>Workflow action unavailable</strong><p>{actionError.message}</p></div>
        </div>
      ) : null}

      <section aria-labelledby="case-table-title" className="queue-workspace">
        <div className="table-toolbar">
          <div>
            <h2 id="case-table-title">Flagged cases</h2>
            <span>{rows.length} shown · ordered by recorded model score</span>
          </div>
          <label className="search-field">
            <SearchIcon />
            <span className="sr-only">Search by case ID or top reason</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search case or feature" />
          </label>
          <label>
            <span>Risk</span>
            <select value={riskBucket} onChange={(event) => updateFilter("risk_bucket", event.target.value)}>
              <option value="">All buckets</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </label>
          <label>
            <span>Review state</span>
            <select value={workflowStatus} onChange={(event) => updateFilter("workflow_status", event.target.value)}>
              <option value="">All states</option>
              <option value="unreviewed">Unreviewed</option>
              <option value="in_review">In review</option>
              <option value="needs_follow_up">Needs follow-up</option>
              <option value="review_complete">Review complete</option>
            </select>
          </label>
          <label>
            <span>Explanation</span>
            <select value={recordedFallback} onChange={(event) => updateFilter("recorded_fallback", event.target.value)}>
              <option value="">All delivery states</option>
              <option value="false">Verified narrative</option>
              <option value="true">Fallback delivered</option>
            </select>
          </label>
        </div>

        {loading ? <LoadingState label="Loading analyst work queue" /> : null}
        {error ? <ErrorState error={error} retry={() => { casesRemote.reload(); workflowsRemote.reload(); summaryRemote.reload(); }} /> : null}
        {!loading && !error && rows.length === 0 ? (
          <EmptyState title="No matching review work" detail="Adjust the deterministic filters or clear the search term." />
        ) : null}
        {!loading && !error && rows.length > 0 ? (
          <div className="table-scroll queue-table-scroll">
            <table className="data-table queue-table">
              <thead>
                <tr>
                  <th>Risk</th>
                  <th>Case</th>
                  <th>Model score</th>
                  <th>Explanation delivery</th>
                  <th>Primary signal</th>
                  <th>Review state</th>
                  <th>Updated</th>
                  <th><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ item, workflow }) => {
                  const narrative = narrativeStatus(item);
                  return (
                    <tr key={item.case_id}>
                      <td><span className={`risk-label is-${String(item.risk_bucket).toLowerCase()}`}>{item.risk_bucket}</span></td>
                      <td><code>{item.case_id}</code></td>
                      <td className="numeric">{item.score.toFixed(4)}</td>
                      <td><span className={`text-status is-${narrative.toLowerCase()}`}>{narrative}</span></td>
                      <td className="reason-cell">{topReasonLabel(item.top_reason)}</td>
                      <td><WorkflowBadge status={workflow.status as WorkflowStatus} /></td>
                      <td className="timestamp-cell">{dateLabel(workflow.updated_at)}</td>
                      <td>
                        <button
                          className="row-action"
                          disabled={startingCase === item.case_id}
                          onClick={() => openCase(item.case_id, workflow)}
                          type="button"
                        >
                          {!workflow.evidence_compatible ? "Restart review" : workflow.status === "unreviewed" ? "Start review" : "Open workspace"} <ArrowIcon size={15} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>

      {scenarios.length > 0 ? (
        <details className="demo-paths">
          <summary>Validated examiner paths</summary>
          <p>Secondary shortcuts for rehearsing a faithful case, a real evaluation error, and a controlled guardrail attack.</p>
          <div className="scenario-list">
            {scenarios.map((scenario) => (
              <ScenarioShortcut key={`${scenario.key ?? scenario.kind}-${scenario.case_id}`} scenario={scenario} open={openScenario} />
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
