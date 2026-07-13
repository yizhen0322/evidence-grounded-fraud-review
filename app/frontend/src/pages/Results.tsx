import { api } from "../api/client";
import { explanationArms } from "../api/normalize";
import type { DetectorResult, RateEstimate, ResultsResponse } from "../api/types";
import { FingerprintIcon } from "../components/icons";
import { useDemoContext } from "../components/DemoContext";
import { ErrorState, LoadingState } from "../components/PageState";
import { useRemoteData } from "../components/useRemoteData";

function meanStd(result: DetectorResult, metric: string, digits = 3): string {
  const mean = result[`${metric}_mean`];
  const std = result[`${metric}_std`];
  if (typeof mean !== "number") {
    const direct = result[metric];
    return typeof direct === "number" ? direct.toFixed(digits) : "—";
  }
  return typeof std === "number" ? `${mean.toFixed(digits)} ± ${std.toFixed(digits)}` : mean.toFixed(digits);
}

function rateLabel(value: RateEstimate | undefined): string {
  if (!value) return "—";
  const percent = `${(value.rate * 100).toFixed(1)}%`;
  const ci = value.ci_low !== undefined && value.ci_high !== undefined
    ? `95% CI ${(value.ci_low * 100).toFixed(1)}–${(value.ci_high * 100).toFixed(1)}%`
    : "CI recorded in artifact";
  return `${percent} · n=${value.n} · ${ci}${value.by_construction ? " · by construction" : ""}`;
}

function detectorRows(results: ResultsResponse): DetectorResult[] {
  const values = Array.isArray(results.detector_results) ? results.detector_results : [];
  return values.filter((item) => ["g0", "g1", "g2", "g3", "g6", "g7"].includes(item.group.toLowerCase()));
}

export function Results() {
  const remote = useRemoteData(api.results, []);
  const { openProvenance } = useDemoContext();

  if (remote.loading) return <LoadingState label="Loading provenance-linked results" />;
  if (remote.error) return <ErrorState error={remote.error} retry={remote.reload} />;
  if (!remote.data) return null;

  const detectors = detectorRows(remote.data);
  const arms = explanationArms(remote.data);
  const strict = arms.find((arm) => arm.arm === "strict") ?? arms[0];
  const simple = arms.find((arm) => arm.arm === "simple");

  return (
    <div className="route-page route-enter">
      <section className="page-heading results-heading">
        <div>
          <span className="eyebrow">Recorded research outputs</span>
          <h1>Results</h1>
          <p>Detector performance and explanation faithfulness are separate stages with separate evidence.</p>
        </div>
        <button className="button secondary" onClick={openProvenance} type="button"><FingerprintIcon /> Inspect result provenance</button>
      </section>

      <section className="results-section" aria-labelledby="detector-results-title">
        <div className="results-section-heading">
          <div><span className="stage-number">01</span><div><h2 id="detector-results-title">Detector performance</h2><p>G0/G1/G2/G3/G6/G7 · test metrics from five frozen seeds.</p></div></div>
          <span className="result-tag">Recorded metrics</span>
        </div>
        <div className="table-scroll">
          <table className="data-table results-table">
            <thead>
              <tr><th>Group</th><th>AUC-PR</th><th>ROC-AUC</th><th>Precision</th><th>Recall</th><th>F1</th><th>Precision@100</th><th>Recall@100</th><th>Inference</th></tr>
            </thead>
            <tbody>
              {detectors.map((result) => (
                <tr key={result.group}>
                  <td><strong>{result.group.toUpperCase()}</strong><small>{result.label}</small></td>
                  <td className="metric-primary">{meanStd(result, "auc_pr")}</td>
                  <td>{meanStd(result, "roc_auc")}</td>
                  <td>{meanStd(result, "precision")}</td>
                  <td>{meanStd(result, "recall")}</td>
                  <td>{meanStd(result, "f1")}</td>
                  <td>{meanStd(result, "precision_at_100")}</td>
                  <td>{meanStd(result, "recall_at_100")}</td>
                  <td>{meanStd(result, "inference_time_seconds", 4)}s</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {detectors.length === 0 ? <p className="muted">No detector rows were returned by the verified results snapshot.</p> : null}
      </section>

      <section className="results-section explanation-results" aria-labelledby="explanation-results-title">
        <div className="results-section-heading">
          <div><span className="stage-number">02</span><div><h2 id="explanation-results-title">Explanation & narrative evidence</h2><p>G4/G5 · detected violations under paired OFF/ON delivery policies.</p></div></div>
          <span className="result-tag is-explanation">Separate evaluation stage</span>
        </div>
        {strict ? (
          <>
            <div className="faithfulness-lead">
              <div><span>Strict prompt arm</span><strong>{strict.any_detected_violation ? `${(strict.any_detected_violation.rate * 100).toFixed(1)}%` : "—"}</strong><small>raw outputs with any detected violation</small></div>
              <div><span>Fallback delivery</span><strong>{strict.fallback ? `${(strict.fallback.rate * 100).toFixed(1)}%` : "—"}</strong><small>validated policy; n={strict.fallback?.n ?? "—"}</small></div>
              <div><span>Transport unavailable</span><strong>{strict.llm_transport_unavailable_count ?? 0}</strong><small>controlled local-service failures</small></div>
              <div><span>Mean latency</span><strong>{strict.mean_latency_seconds?.toFixed(2) ?? "—"}s</strong><small>recorded narrative generation</small></div>
            </div>
            <div className="rate-list">
              <div><strong>Format detected violations</strong><span>{rateLabel(strict.format)}</span></div>
              <div><strong>Completeness detected violations</strong><span>{rateLabel(strict.completeness)}</span></div>
              <div><strong>Grounding detected violations</strong><span>{rateLabel(strict.grounding)}</span></div>
              <div><strong>Direction detected violations</strong><span>{rateLabel(strict.direction)}</span></div>
            </div>
          </>
        ) : <p className="muted">No strict-arm explanation results were returned.</p>}
        {simple ? (
          <details className="simple-arm-details">
            <summary>Show simple-prompt comparison arm</summary>
            <div className="rate-list compact">
              <div><strong>Any detected violation</strong><span>{rateLabel(simple.any_detected_violation)}</span></div>
              <div><strong>Fallback</strong><span>{rateLabel(simple.fallback)}</span></div>
              <div><strong>Mean latency</strong><span>{simple.mean_latency_seconds?.toFixed(2) ?? "—"}s</span></div>
            </div>
          </details>
        ) : null}
      </section>

      <section className="results-section figure-section" aria-labelledby="pr-figure-title">
        <div className="results-section-heading">
          <div><span className="stage-number">03</span><div><h2 id="pr-figure-title">Recorded precision–recall curves</h2><p>Served from the Task 7.1 figure allowlist; React does not recompute it.</p></div></div>
        </div>
        <figure>
          <img alt="Recorded precision-recall curves for detector groups G0, G1, G2, G3, G6, and G7" src={api.figureUrl("pr_curves")} />
          <figcaption>
            Precision–recall curves from exact allowlisted detector runs. The table above is the accessible numeric alternative.
          </figcaption>
        </figure>
      </section>
    </div>
  );
}
