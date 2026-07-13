import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { caseNarrative } from "../api/normalize";
import type { LiveNarrativeResponse, NarrativeView, ReasonCode } from "../api/types";
import { useDemoContext } from "../components/DemoContext";
import { AlertIcon, ArrowIcon, FingerprintIcon, ShieldIcon } from "../components/icons";
import { ErrorState, LoadingState } from "../components/PageState";
import { GuardrailBadges } from "../components/StatusBadge";
import { useRemoteData } from "../components/useRemoteData";

function contributionLabel(code: ReasonCode): string {
  return code.direction === "increases_risk" ? "Pushes toward fraud" : "Pushes toward legitimate";
}

function outcomeText(pred: number | undefined, yTrue: number): string {
  if (pred === 1 && yTrue === 0) return "Flagged false positive";
  if (pred === 1 && yTrue === 1) return "Flagged true positive";
  if (pred === 0 && yTrue === 1) return "Missed fraud in evaluation";
  return "Not flagged; historically legitimate";
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
        <p>{live ? "The recorded detector evidence remains available." : "The snapshot did not provide narrative text for this case."}</p>
      </div>
    );
  }
  return (
    <>
      <div className="narrative-state-row">
        <span className={`decision-state ${narrative.fallback ? "is-fallback" : "is-accepted"}`}>
          {narrative.fallback ? "Fallback active" : "Accepted narrative"}
        </span>
        {narrative.latency_seconds !== null && narrative.latency_seconds !== undefined ? (
          <span>{narrative.latency_seconds.toFixed(2)}s generation</span>
        ) : null}
      </div>
      {live ? <p className="demo-only-label">Live replay · Demo-only; not a reported G5 result</p> : <p className="recorded-label">Recorded strict-prompt arm · Reportable frozen output</p>}
      <div className="narrative-copy" aria-live="polite">{narrative.final_text}</div>
      <GuardrailBadges checks={narrative.checks} reasons={narrative.check_reasons} />
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

export function Investigation() {
  const { caseId = "" } = useParams();
  const { mode, openProvenance } = useDemoContext();
  const remote = useRemoteData(() => api.case(caseId), [caseId]);
  const [liveNarrative, setLiveNarrative] = useState<LiveNarrativeResponse>();
  const [liveError, setLiveError] = useState<Error>();
  const [liveLoading, setLiveLoading] = useState(false);

  useEffect(() => {
    setLiveNarrative(undefined);
    setLiveError(undefined);
  }, [caseId]);

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

  if (remote.loading) return <LoadingState label="Loading recorded investigation" />;
  if (remote.error) return <ErrorState error={remote.error} retry={remote.reload} />;
  if (!detail) return null;

  const currentNarrative = mode === "live" ? liveNarrative ?? null : recorded;

  return (
    <div className="route-page route-enter">
      <section className="page-heading investigation-heading">
        <div>
          <Link className="back-link" to="/queue">← Back to queue</Link>
          <span className="eyebrow">Recorded investigation</span>
          <h1>Case <code>{detail.case_id}</code></h1>
          <p>{outcomeText(detail.pred ?? (detail.detector_flagged ? 1 : 0), detail.y_true)}. Historical truth is shown for evaluation only.</p>
        </div>
        <div className="heading-actions">
          <span className={`risk-hero is-${String(detail.risk_bucket).toLowerCase()}`}>
            <small>Recorded risk</small>
            <strong>{detail.risk_bucket}</strong>
          </span>
          <button className="button secondary" onClick={openProvenance} type="button"><FingerprintIcon /> Provenance</button>
        </div>
      </section>

      <div className="investigation-grid">
        <section className="evidence-column" aria-labelledby="evidence-title">
          <div className="section-heading-line">
            <div>
              <span className="eyebrow">Frozen detector</span>
              <h2 id="evidence-title">Decision evidence</h2>
            </div>
            <span className="stage-number">01</span>
          </div>
          <dl className="metric-strip">
            <div><dt>Model score</dt><dd>{detail.score.toFixed(4)}</dd></div>
            <div><dt>Frozen threshold</dt><dd>{detail.threshold === null || detail.threshold === undefined ? "Recorded in manifest" : detail.threshold.toFixed(4)}</dd></div>
            <div><dt>Detector</dt><dd>{(detail.detector_flagged ?? detail.pred === 1) ? "Flagged" : "Not flagged"}</dd></div>
            <div><dt>Evaluation-only ground truth</dt><dd>{detail.y_true === 1 ? "Fraud" : "Legitimate"}</dd></div>
          </dl>

          <div className="chart-heading">
            <div>
              <h3>Top recorded SHAP contributions</h3>
              <p>Signed contributions push the model output toward fraud or legitimate. They are not causal claims.</p>
            </div>
            <div className="chart-legend"><span className="is-up" /> Toward fraud <span className="is-down" /> Toward legitimate</div>
          </div>
          {codes.length > 0 ? <ContributionBars codes={codes} /> : <p className="muted">No recorded contribution list is available.</p>}

          <div className="reason-table-wrap">
            <h3>Standardized reason codes</h3>
            <table className="data-table reason-table">
              <thead><tr><th>Rank</th><th>Feature</th><th>Recorded direction</th><th>SHAP contribution</th></tr></thead>
              <tbody>
                {codes.map((code) => (
                  <tr key={`${code.rank}-${code.feature}`}>
                    <td>{code.rank}</td>
                    <td><code>{code.feature}</code></td>
                    <td>{contributionLabel(code)}</td>
                    <td className={code.direction === "increases_risk" ? "numeric risk-up" : "numeric risk-down"}>
                      {code.shap_value === null || code.shap_value === undefined ? "Recorded direction only" : code.shap_value.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="narrative-column" aria-labelledby="narrative-title">
          <div className="section-heading-line">
            <div>
              <span className="eyebrow">Constrained translation</span>
              <h2 id="narrative-title">Narrative & guardrails</h2>
            </div>
            <span className="stage-number">02</span>
          </div>

          {mode === "live" ? (
            <div className="live-action-band">
              <div>
                <strong>Live replay</strong>
                <p>Uses the same recorded evidence. It is ephemeral and never reported as G5 output.</p>
              </div>
              <button className="button primary" disabled={liveLoading} onClick={generateLive} type="button">
                {liveLoading ? "Generating…" : "Generate live replay"}
              </button>
            </div>
          ) : null}
          {liveError ? (
            <div className="degraded-state" role="alert">
              <AlertIcon />
              <div><strong>Live service unavailable</strong><p>{liveError.message} Recorded evidence remains unchanged.</p></div>
            </div>
          ) : null}
          <NarrativePanel narrative={currentNarrative} live={mode === "live"} />

          <details className="data-disclosure">
            <summary>Data sent to LLM <ArrowIcon size={15} /></summary>
            {detail.data_sent_to_llm?.payload ? (
              <pre className="evidence-payload">{detail.data_sent_to_llm.payload}</pre>
            ) : null}
            <div className="disclosure-grid">
              <div>
                <strong>Included</strong>
                <ul>{(detail.data_sent_to_llm?.included ?? ["Case identifier", "Coarse risk bucket", "Feature names", "Direction and rank"]).map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              <div>
                <strong>Excluded</strong>
                <ul>{(detail.data_sent_to_llm?.excluded ?? ["Raw transaction row", "Exact feature values", "Detector score or probability", "SHAP magnitudes", "Historical label"]).map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            </div>
          </details>

          <Link className="guardrail-cta" to={`/guardrails?case_id=${detail.case_id}`}>
            <ShieldIcon />
            <span><strong>Challenge this narrative</strong><small>Run deterministic mutations through the real validator.</small></span>
            <ArrowIcon />
          </Link>
        </section>
      </div>
    </div>
  );
}
