import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { normalizeCases } from "../api/normalize";
import type { CaseDetail, DemoScenario, ReasonCode } from "../api/types";
import { ArrowIcon, SearchIcon } from "../components/icons";
import { EmptyState, ErrorState, LoadingState } from "../components/PageState";
import { useDemoContext } from "../components/DemoContext";
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
  return narrative.fallback ? "Fallback" : "Passed";
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
  const navigate = useNavigate();
  const { scenarios } = useDemoContext();
  const riskBucket = params.get("risk_bucket") ?? "";
  const historicalLabel = params.get("historical_label") ?? "";
  const recordedFallback = params.get("recorded_fallback") ?? "";

  const remote = useRemoteData(
    () => api.cases({
      risk_bucket: riskBucket,
      historical_label: historicalLabel,
      recorded_fallback: recordedFallback,
      limit: 200,
    }),
    [riskBucket, historicalLabel, recordedFallback],
  );

  const response = useMemo(() => (remote.data ? normalizeCases(remote.data) : { items: [], total: 0 }), [remote.data]);
  const items = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return response.items;
    return response.items.filter((item) =>
      String(item.case_id).includes(needle) || topReasonLabel(item.top_reason).toLowerCase().includes(needle),
    );
  }, [response.items, search]);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  };

  const openScenario = (scenario: DemoScenario) => {
    if (scenario.kind === "attack" || scenario.key === "attack") navigate(`/guardrails?case_id=${scenario.case_id}`);
    else navigate(`/cases/${scenario.case_id}`);
  };

  return (
    <div className="route-page route-enter">
      <section className="page-heading queue-heading">
        <div>
          <span className="eyebrow">Frozen detector output</span>
          <h1>Flagged case queue</h1>
          <p>Cases are ordered by recorded model score. Selecting a row never recomputes the detector.</p>
        </div>
        <div className="heading-stat">
          <strong>{remote.loading ? "—" : response.total}</strong>
          <span>recorded flagged cases</span>
        </div>
      </section>

      {scenarios.length > 0 ? (
        <section aria-labelledby="scenario-title" className="scenario-strip">
          <div className="section-label">
            <h2 id="scenario-title">Rehearsed paths</h2>
            <span>Predicate-validated at startup</span>
          </div>
          <div className="scenario-list">
            {scenarios.map((scenario) => (
              <ScenarioShortcut key={`${scenario.key ?? scenario.kind}-${scenario.case_id}`} scenario={scenario} open={openScenario} />
            ))}
          </div>
        </section>
      ) : null}

      <section aria-labelledby="case-table-title" className="queue-workspace">
        <div className="table-toolbar">
          <div>
            <h2 id="case-table-title">Recorded cases</h2>
            <span>{items.length} shown</span>
          </div>
          <label className="search-field">
            <SearchIcon />
            <span className="sr-only">Search by case ID or top reason</span>
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search case or reason" />
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
            <span>Evaluation label</span>
            <select value={historicalLabel} onChange={(event) => updateFilter("historical_label", event.target.value)}>
              <option value="">All labels</option>
              <option value="1">Fraud</option>
              <option value="0">Legitimate</option>
            </select>
          </label>
          <label>
            <span>Narrative</span>
            <select value={recordedFallback} onChange={(event) => updateFilter("recorded_fallback", event.target.value)}>
              <option value="">All states</option>
              <option value="false">Passed</option>
              <option value="true">Fallback</option>
            </select>
          </label>
        </div>

        {remote.loading ? <LoadingState label="Loading recorded case queue" /> : null}
        {remote.error ? <ErrorState error={remote.error} retry={remote.reload} /> : null}
        {!remote.loading && !remote.error && items.length === 0 ? (
          <EmptyState title="No matching recorded cases" detail="Adjust the deterministic filters or clear the search term." />
        ) : null}
        {!remote.loading && !remote.error && items.length > 0 ? (
          <div className="table-scroll">
            <table className="data-table queue-table">
              <thead>
                <tr>
                  <th>Case</th>
                  <th>Risk</th>
                  <th>Model score</th>
                  <th>Detector</th>
                  <th>Evaluation-only ground truth</th>
                  <th>Top reason</th>
                  <th>Recorded narrative</th>
                  <th><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => {
                  const status = narrativeStatus(item);
                  return (
                    <tr key={item.case_id}>
                      <td><code>{item.case_id}</code></td>
                      <td><span className={`risk-label is-${String(item.risk_bucket).toLowerCase()}`}>{item.risk_bucket}</span></td>
                      <td className="numeric">{item.score.toFixed(4)}</td>
                      <td>{(item.detector_flagged ?? item.pred === 1) ? "Flagged" : "Not flagged"}</td>
                      <td><strong>{item.y_true === 1 ? "Fraud" : "Legitimate"}</strong></td>
                      <td className="reason-cell">{topReasonLabel(item.top_reason)}</td>
                      <td><span className={`text-status is-${status.toLowerCase()}`}>{status}</span></td>
                      <td>
                        <button className="row-action" onClick={() => navigate(`/cases/${item.case_id}`)} type="button">
                          Open case <ArrowIcon size={15} />
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
