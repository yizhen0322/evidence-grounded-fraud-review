import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { normalizeCases } from "../api/normalize";
import type { CaseDetail, ReasonCode, WorkflowRecord, WorkflowStatus } from "../api/types";
import { ArrowIcon, SearchIcon } from "../components/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { WorkflowBadge } from "../components/StatusBadge";
import { useRemoteData } from "../components/useRemoteData";

type SortMode = "work_priority" | "detector_rank" | "amount";
type QueueSource = "operational" | "research";
type SourceFilter = QueueSource | "all";

interface SourcedCase {
  source: QueueSource;
  item: CaseDetail;
}

function valueBucketLabel(value: string | null | undefined): string {
  if (!value) return "";
  return value.replaceAll("_", " ");
}

function topReasonLabel(reason: ReasonCode | string | null | undefined): string {
  if (!reason) return "Not available";
  if (typeof reason === "string") return reason;
  const label = reason.display_label ?? reason.label ?? reason.feature;
  const bucket = reason.value_bucket ? ` · ${valueBucketLabel(reason.value_bucket)}` : "";
  return `${label}${bucket} · ${reason.direction === "increases_risk" ? "increases risk" : "decreases risk"}`;
}

function topReasons(item: CaseDetail): ReasonCode[] {
  if (item.top_reasons?.length) return item.top_reasons;
  if (item.top_reason && typeof item.top_reason !== "string") return [item.top_reason];
  return [];
}

function amountLabel(value: number | undefined): string {
  if (value === undefined) return "Amount unavailable";
  return `Amount ${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function caseAmount(item: CaseDetail): number | undefined {
  return item.amount ?? item.transaction_context?.amount;
}

function timestampLabel(item: CaseDetail): string {
  const value = item.timestamp ?? item.transaction_context?.timestamp;
  if (!value) return elapsedLabel(item.transaction_context?.elapsed_seconds);
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function primarySignal(item: CaseDetail): string {
  return item.readable_top_signal ?? topReasonLabel(item.top_signal ?? item.top_reason);
}

function deliveryLabel(item: CaseDetail): string {
  const delivery = item.explanation_delivery?.toLowerCase();
  if (delivery === "guarded_llm") return "Guarded LLM brief";
  if (delivery === "deterministic_fallback") return "Deterministic fallback";
  if (delivery === "unavailable") return "Unavailable";
  return narrativeStatus(item);
}

function reasonBucket(reason: ReasonCode): string {
  return reason.value_bucket ? ` · ${valueBucketLabel(reason.value_bucket)}` : "";
}

function elapsedLabel(value: number | undefined): string {
  if (value === undefined) return "Dataset time unavailable";
  const totalMinutes = Math.floor(value / 60);
  const day = Math.floor(totalMinutes / (24 * 60)) + 1;
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60);
  const minutes = totalMinutes % 60;
  return `Day ${day} · ${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")} elapsed`;
}

function routingLabel(item: CaseDetail, workflow: WorkflowRecord): string {
  if (workflow.status === "needs_follow_up") return "Follow-up";
  if (workflow.status === "in_review") return "Active review";
  if (workflow.status === "review_complete") return "Closed";
  if (item.recorded_fallback) return "Fallback review";
  return "Unreviewed";
}

function routingOrder(item: CaseDetail, workflow: WorkflowRecord): number {
  if (workflow.status === "needs_follow_up") return 0;
  if (workflow.status === "in_review") return 1;
  if (workflow.status === "unreviewed" && item.recorded_fallback) return 2;
  if (workflow.status === "unreviewed") return 3;
  return 4;
}

function narrativeStatus(item: CaseDetail): string {
  if (item.recorded_narrative_status) {
    const status = item.recorded_narrative_status.toLowerCase();
    if (["passed", "accepted", "verified"].includes(status)) return "Verified";
    if (status === "fallback") return "Fallback";
    return item.recorded_narrative_status;
  }
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

export function CaseQueue() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [actionError, setActionError] = useState<Error>();
  const [startingCase, setStartingCase] = useState<string>();
  const [sortMode, setSortMode] = useState<SortMode>("work_priority");
  const navigate = useNavigate();
  const recordedFallback = params.get("recorded_fallback") ?? "";
  const workflowStatus = params.get("workflow_status") ?? "";
  const sourceParam = params.get("source");
  const sourceFilter: SourceFilter = sourceParam === "research" || sourceParam === "all" ? sourceParam : "operational";

  const casesRemote = useRemoteData(
    async () => {
      const [research, operational] = await Promise.all([
        api.researchCases({ recorded_fallback: recordedFallback, limit: 200 }),
        api.operationalCases({ recorded_fallback: recordedFallback, limit: 200 }).catch(() => undefined),
      ]);
      return {
        operational: normalizeCases(operational ?? { items: [], total: 0 }),
        research: normalizeCases(research),
        operationalAvailable: operational !== undefined,
      };
    },
    [recordedFallback],
  );
  const effectiveSourceFilter: SourceFilter = !sourceParam && casesRemote.data?.operationalAvailable === false ? "all" : sourceFilter;
  const workflowsRemote = useRemoteData(
    async () => {
      const [research, operational] = await Promise.all([
        api.workflows(),
        api.operationalWorkflows().catch(() => undefined),
      ]);
      return { operational: operational?.items ?? [], research: research.items };
    },
    [],
  );
  const summaryRemote = useRemoteData(
    async () => {
      const [research, operational] = await Promise.all([
        api.workflowSummary(),
        api.operationalWorkflowSummary().catch(() => undefined),
      ]);
      return {
        total: (operational?.total ?? 0) + research.total,
        counts: {
          unreviewed: (operational?.counts.unreviewed ?? 0) + research.counts.unreviewed,
          in_review: (operational?.counts.in_review ?? 0) + research.counts.in_review,
          needs_follow_up: (operational?.counts.needs_follow_up ?? 0) + research.counts.needs_follow_up,
          review_complete: (operational?.counts.review_complete ?? 0) + research.counts.review_complete,
        },
        recorded_fallback: (operational?.recorded_fallback ?? 0) + research.recorded_fallback,
      };
    },
    [],
  );

  const sourcedCases = useMemo<SourcedCase[]>(() => [
    ...(casesRemote.data?.operational.items ?? []).map((item) => ({ source: "operational" as const, item })),
    ...(casesRemote.data?.research.items ?? []).map((item) => ({ source: "research" as const, item })),
  ], [casesRemote.data]);
  const workflowMap = useMemo(
    () => new Map([
      ...(workflowsRemote.data?.operational ?? []).map((item) => [`operational:${item.case_id}`, item] as const),
      ...(workflowsRemote.data?.research ?? []).map((item) => [`research:${item.case_id}`, item] as const),
    ]),
    [workflowsRemote.data],
  );
  const rows = useMemo(() => {
    const needle = search.trim().toLowerCase();
    return sourcedCases
      .map(({ source, item }) => ({ source, item, workflow: workflowMap.get(`${source}:${item.case_id}`) ?? defaultWorkflow(item.case_id) }))
      .filter(({ source, item, workflow }) => {
        if (effectiveSourceFilter !== "all" && source !== effectiveSourceFilter) return false;
        if (workflowStatus && workflow.status !== workflowStatus) return false;
        if (!needle) return true;
        return String(item.case_id).includes(needle)
          || primarySignal(item).toLowerCase().includes(needle)
          || topReasons(item).some((reason) => topReasonLabel(reason).toLowerCase().includes(needle))
          || amountLabel(caseAmount(item)).toLowerCase().includes(needle);
      })
      .sort((left, right) => {
        if (sortMode === "detector_rank") {
          return left.source.localeCompare(right.source)
            || (left.item.score_rank ?? Number.MAX_SAFE_INTEGER) - (right.item.score_rank ?? Number.MAX_SAFE_INTEGER);
        }
        if (sortMode === "amount") {
          return (caseAmount(right.item) ?? 0) - (caseAmount(left.item) ?? 0);
        }
        return routingOrder(left.item, left.workflow) - routingOrder(right.item, right.workflow)
          || left.source.localeCompare(right.source)
          || (left.item.score_rank ?? Number.MAX_SAFE_INTEGER) - (right.item.score_rank ?? Number.MAX_SAFE_INTEGER)
          || left.item.case_id - right.item.case_id;
      });
  }, [sourcedCases, workflowMap, workflowStatus, effectiveSourceFilter, search, sortMode]);

  const snapshotBriefing = useMemo(() => {
    if (sourcedCases.length === 0) return null;
    return {
      operationalCount: sourcedCases.filter(({ source }) => source === "operational").length,
      researchCount: sourcedCases.filter(({ source }) => source === "research").length,
      fallbackCount: sourcedCases.filter(({ item }) => item.recorded_fallback).length,
      verifiedCount: sourcedCases.filter(({ item }) => !item.recorded_fallback).length,
    };
  }, [sourcedCases]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const openCase = async (source: QueueSource, caseId: number, workflow: WorkflowRecord) => {
    if (workflow.status !== "unreviewed" && workflow.evidence_compatible) {
      navigate(source === "operational" ? `/operational/cases/${caseId}` : `/research/cases/${caseId}`);
      return;
    }
    setStartingCase(`${source}:${caseId}`);
    setActionError(undefined);
    try {
      await (source === "operational" ? api.updateOperationalWorkflow : api.updateWorkflow)(caseId, {
        revision: workflow.revision,
        status: "in_review",
        disposition: workflow.disposition,
        note: workflow.note,
      });
      navigate(source === "operational" ? `/operational/cases/${caseId}` : `/research/cases/${caseId}`);
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
    await openCase(next.source, next.item.case_id, next.workflow);
  };

  const counts = summaryRemote.data?.counts;
  const loading = casesRemote.loading || workflowsRemote.loading || summaryRemote.loading;
  const error = casesRemote.error ?? workflowsRemote.error ?? summaryRemote.error;

  return (
    <div className="route-page route-enter operations-page">
      <section className="page-heading queue-heading">
        <div>
          <span className="eyebrow">Analyst work queue</span>
          <h1>Alert Queue</h1>
          <p>Review readable S0 alerts through model evidence, a guarded local-LLM brief, and a human routing decision. ULB alerts remain available as supporting real-data detector evidence.</p>
        </div>
        <div className="heading-actions">
          <div className="heading-stat compact">
            <strong>{counts?.unreviewed ?? "—"}</strong>
            <span>awaiting review</span>
          </div>
          <button className="button primary" disabled={loading || startingCase !== undefined} onClick={startNextReview} type="button">
            {startingCase !== undefined ? "Starting…" : "Review next alert"}
            <ArrowIcon size={15} />
          </button>
        </div>
      </section>

      <section aria-label="Workflow summary" className="operations-ledger compact-ledger">
        <div><span>Unreviewed</span><strong>{counts?.unreviewed ?? "—"}</strong></div>
        <div><span>In review</span><strong>{counts?.in_review ?? "—"}</strong></div>
        <div><span>Follow-up</span><strong>{counts?.needs_follow_up ?? "—"}</strong></div>
        <div><span>Closed</span><strong>{counts?.review_complete ?? "—"}</strong></div>
      </section>

      {actionError ? (
        <div className="degraded-state queue-action-error" role="alert">
          <div><strong>Workflow action unavailable</strong><p>{actionError.message}</p></div>
        </div>
      ) : null}

      {casesRemote.data?.operationalAvailable === false ? (
        <div className="degraded-state" role="status">
          <div><strong>S0 semantic evidence unavailable</strong><p>The S0 semantic evidence lane is temporarily offline or invalid. The ULB research queue remains available as the real-data detector benchmark.</p></div>
        </div>
      ) : null}

      {snapshotBriefing ? (
        <section aria-label="Queue evidence note" className="queue-evidence-note">
          <div><strong>{snapshotBriefing.operationalCount} primary explanation cases</strong><span>S0 synthetic readable evidence · default review queue · ranks within the S0 detector.</span></div>
          <div><strong>{snapshotBriefing.researchCount} supporting benchmark alerts</strong><span>ULB real-data detector evidence · anonymous PCA features · not comparable with S0 ranks.</span></div>
          <button onClick={() => updateFilter("recorded_fallback", snapshotBriefing.fallbackCount ? "true" : "")} type="button">
            <strong>{snapshotBriefing.verifiedCount}/{sourcedCases.length} guarded briefs passed</strong>
            <span>{snapshotBriefing.fallbackCount} deterministic fallback{snapshotBriefing.fallbackCount === 1 ? "" : "s"} · the local-LLM explanation path remains separate from supporting detector evidence</span>
          </button>
        </section>
      ) : null}

      <section aria-labelledby="case-table-title" className="queue-workspace">
        <div className="table-toolbar">
          <div>
            <h2 id="case-table-title">Model-flagged alerts</h2>
            <span>{rows.length} shown · {effectiveSourceFilter === "operational" ? "primary S0 explanation cases" : effectiveSourceFilter === "research" ? "supporting ULB benchmark" : "all labelled evidence sources"}</span>
          </div>
          <label className="search-field">
            <SearchIcon />
            <span className="sr-only">Search by case ID, signal, or amount</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search case, feature or amount" />
          </label>
          <label>
            <span>Source</span>
            <select value={sourceFilter} onChange={(event) => updateFilter("source", event.target.value)}>
              <option value="operational">S0 explanation cases</option>
              <option value="all">All sources</option>
              <option value="research">Research benchmark</option>
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
          <label>
            <span>Sort</span>
            <select value={sortMode} onChange={(event) => setSortMode(event.target.value as SortMode)}>
              <option value="work_priority">Work priority</option>
              <option value="detector_rank">Source and detector rank</option>
              <option value="amount">Amount</option>
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
                  <th>State</th>
                  <th>Source</th>
                  <th>Transaction / case</th>
                  <th>Rank <span className="column-help" title="Rank is calculated within the alert's own detector source and is not comparable across sources.">?</span></th>
                  <th>Model evidence</th>
                  <th>Brief</th>
                  <th><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody>
                {rows.map(({ source, item, workflow }) => {
                  const narrative = narrativeStatus(item);
                  return (
                    <tr key={`${source}-${item.case_id}`}>
                      <td className="transaction-cell">
                        <WorkflowBadge status={workflow.status as WorkflowStatus} />
                        <small>{routingLabel(item, workflow)}</small>
                      </td>
                      <td>
                        <span className={`source-badge is-${source}`}>{source === "operational" ? "Operational" : "Research"}</span>
                        <small className="cell-meta">{source === "operational" ? "S0 synthetic readable evidence" : "ULB real-data benchmark evidence"}</small>
                      </td>
                      <td className="transaction-cell">
                        <code>{item.transaction_id ?? `Case ${item.case_id}`}</code>
                        <strong>{amountLabel(caseAmount(item))}</strong>
                        <small>{source === "operational" ? timestampLabel(item) : elapsedLabel(item.transaction_context?.elapsed_seconds)}</small>
                      </td>
                      <td className="detector-score-cell numeric">
                        <strong>#{item.rank ?? item.score_rank ?? "—"} of {item.flagged_total ?? "—"}</strong>
                        <small>{source === "operational" ? "Within S0" : "Within ULB"}</small>
                      </td>
                      <td className="signal-chip-cell">
                        {source === "operational" ? <strong>{primarySignal(item)}</strong> : null}
                        <div className="signal-chip-list">
                          {topReasons(item).map((reason) => (
                            <span className={reason.direction === "increases_risk" ? "is-up" : "is-down"} key={`${reason.rank}-${reason.feature}`}>
                              <code>{reason.display_label ?? reason.label ?? reason.feature}</code>{reason.direction === "increases_risk" ? "↑" : "↓"}{reasonBucket(reason)}
                            </span>
                          ))}
                        </div>
                      </td>
                      <td><span className={`text-status is-${narrative.toLowerCase().replaceAll(" ", "-")}`}>{source === "operational" ? deliveryLabel(item) : narrative}</span><small className="cell-meta">{dateLabel(workflow.updated_at)}</small></td>
                      <td>
                        <button
                          className="row-action"
                          disabled={startingCase === `${source}:${item.case_id}`}
                          onClick={() => openCase(source, item.case_id, workflow)}
                          type="button"
                        >
                          {!workflow.evidence_compatible ? "Restart review" : "Start review"} <ArrowIcon size={15} />
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
    </div>
  );
}
