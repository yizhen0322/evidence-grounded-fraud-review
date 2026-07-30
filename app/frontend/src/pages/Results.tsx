import { api } from "../api/client";
import { explanationArms } from "../api/normalize";
import type { DetectorResult, OperationalResultsResponse, RateEstimate, ResultsResponse } from "../api/types";
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
  const low = value.ci_low ?? value.lower;
  const high = value.ci_high ?? value.upper;
  const ci = low !== undefined && high !== undefined
    ? `95% CI ${(low * 100).toFixed(1)}–${(high * 100).toFixed(1)}%`
    : "95% interval unavailable";
  const construction = value.by_construction || value.label === "by_construction" ? " · by construction" : "";
  return `${percent} · n=${value.n} · ${ci}${construction}`;
}

function percent(value: unknown, digits = 1): string {
  return typeof value === "number" ? `${(value * 100).toFixed(digits)}%` : "—";
}

function numeric(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function countLabel(value: RateEstimate | undefined): string {
  if (!value) return "—";
  return `${Math.round(value.rate * value.n)}/${value.n}`;
}

function rateFromRaw(rate: number | undefined, n: number | undefined): RateEstimate | undefined {
  return rate !== undefined && n !== undefined ? { rate, n } : undefined;
}

function detectorRows(results: ResultsResponse): DetectorResult[] {
  const values = Array.isArray(results.detector_results) ? results.detector_results : [];
  return values.filter((item) => ["g0", "g1", "g2", "g3", "g6", "g7"].includes(item.group.toLowerCase()));
}

const DETECTOR_NAMES: Record<string, { name: string; detail: string }> = {
  g0: { name: "XGBoost baseline", detail: "Original features" },
  g1: { name: "XGBoost + SMOTE", detail: "Training-set oversampling" },
  g2: { name: "XGBoost + AE anomaly", detail: "Reconstruction-error feature" },
  g3: { name: "AE anomaly + SMOTE", detail: "Hybrid oversampling" },
  g6: { name: "Cost-sensitive XGBoost", detail: "Class-weighted training" },
  g7: { name: "XGBoost + AE latent", detail: "Learned latent features" },
};

function metricNumber(result: DetectorResult, metric: string): number | undefined {
  const value = result[`${metric}_mean`] ?? result[metric];
  return typeof value === "number" ? value : undefined;
}

function metricStd(result: DetectorResult, metric: string): number {
  const value = result[`${metric}_std`];
  return typeof value === "number" ? value : 0;
}

function strategyName(result: DetectorResult): string {
  return DETECTOR_NAMES[result.group.toLowerCase()]?.name ?? result.label ?? result.group.toUpperCase();
}

function F1BarChart({ detectors }: { detectors: DetectorResult[] }) {
  return (
    <section className="metric-chart-panel metric-chart-featured">
      <div className="metric-chart-heading">
        <div><span className="eyebrow">Primary comparison</span><h3>F1 score comparison</h3></div>
        <span>Mean ± SD · five seeds · scale 0–1</span>
      </div>
      <div aria-label="F1 score by detector strategy" className="metric-bar-chart" role="img">
        {detectors.map((result) => {
          const mean = metricNumber(result, "f1") ?? 0;
          const std = metricStd(result, "f1");
          const low = Math.max(0, mean - std);
          const high = Math.min(1, mean + std);
          return (
            <div className="metric-bar-row" key={`f1-${result.group}`}>
              <div className="metric-bar-label"><strong>{result.group.toUpperCase()}</strong><span>{strategyName(result)}</span></div>
              <div className="metric-bar-track">
                <span className="metric-bar-fill is-f1" style={{ width: `${mean * 100}%` }} />
                <span className="metric-error-range" style={{ left: `${low * 100}%`, width: `${(high - low) * 100}%` }} />
                <span className="metric-error-point" style={{ left: `${mean * 100}%` }} />
              </div>
              <output>{meanStd(result, "f1")}</output>
            </div>
          );
        })}
      </div>
      <p className="metric-chart-note">The chart makes the operating differences visible without claiming statistical superiority between overlapping runs.</p>
    </section>
  );
}

function DualMetricChart({
  detectors,
  title,
  ariaLabel,
  first,
  second,
  scale,
  format,
}: {
  detectors: DetectorResult[];
  title: string;
  ariaLabel: string;
  first: { metric: string; label: string; className: string };
  second: { metric: string; label: string; className: string };
  scale: number;
  format: (value: number) => string;
}) {
  return (
    <section className="metric-chart-panel">
      <div className="metric-chart-heading compact">
        <h3>{title}</h3>
        <div className="metric-chart-legend"><span className={first.className} />{first.label}<span className={second.className} />{second.label}</div>
      </div>
      <div aria-label={ariaLabel} className="dual-metric-chart" role="img">
        {detectors.map((result) => {
          const firstValue = metricNumber(result, first.metric) ?? 0;
          const secondValue = metricNumber(result, second.metric) ?? 0;
          return (
            <div className="dual-metric-row" key={`${ariaLabel}-${result.group}`}>
              <strong>{result.group.toUpperCase()}</strong>
              <div>
                <span className={`dual-bar ${first.className}`} style={{ width: `${Math.min(100, (firstValue / scale) * 100)}%` }} />
                <small>{first.label} {format(firstValue)}</small>
              </div>
              <div>
                <span className={`dual-bar ${second.className}`} style={{ width: `${Math.min(100, (secondValue / scale) * 100)}%` }} />
                <small>{second.label} {format(secondValue)}</small>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function PolicyRateChart({ arm }: { arm: ReturnType<typeof explanationArms>[number] }) {
  const rejectedRate = arm.fallback?.rate ?? arm.any_detected_violation?.rate ?? 0;
  const passRate = Math.max(0, Math.min(1, 1 - rejectedRate));
  const rows = [
    ["LLM output with detected violation", arm.any_detected_violation?.rate ?? 0, "is-warning"],
    ["Fallback delivery", arm.fallback?.rate ?? 0, "is-fallback"],
    ["Guardrail pass / LLM delivered", passRate, "is-pass"],
  ] as const;
  return (
    <div className="policy-rate-panel">
      <div className="metric-chart-heading compact">
        <div><h3>LLM delivery outcomes</h3><p>Candidate violations, deterministic fallback, and the share of LLM narratives delivered after all checks passed.</p></div>
        <span>Common scale 0–100%</span>
      </div>
      <div aria-label="Narrative policy violation, fallback, and pass rates" className="policy-rate-chart" role="img">
        {rows.map(([label, value, className]) => (
          <div className="policy-rate-row" key={label}>
            <span>{label}</span>
            <div><span className={className} style={{ width: `${value * 100}%` }} /></div>
            <strong>{(value * 100).toFixed(1)}%</strong>
          </div>
        ))}
      </div>
      <p className="metric-chart-note">Pass rate is the complementary delivered-output rate: 100% minus fallback delivery. Detailed violation categories remain listed below.</p>
    </div>
  );
}

function OperationalSemanticBand({ results }: { results?: OperationalResultsResponse }) {
  if (!results) return null;
  const test = results.metrics.test ?? {};
  const summary = results.explanation_summary;
  const calibration = results.validator_calibration;
  const rows = numeric(summary.rows) ?? numeric(summary.cases) ?? results.case_count;
  const fallbacks = numeric(summary.fallbacks)
    ?? (typeof summary.fallback_rate === "object"
      ? Math.round(summary.fallback_rate.rate * summary.fallback_rate.n)
      : undefined);
  const fallbackRate = typeof summary.fallback_rate === "number"
    ? summary.fallback_rate
    : typeof summary.fallback_rate === "object"
      ? summary.fallback_rate.rate
      : summary.fallback_rate_wilson?.rate;
  const accepted = rows !== undefined && fallbacks !== undefined ? rows - fallbacks : undefined;
  const fallbackEstimate = typeof summary.fallback_rate === "object"
    ? summary.fallback_rate
    : summary.fallback_rate_wilson ?? rateFromRaw(fallbackRate, rows);
  const transportEstimate = summary.transport_failure_rate;
  const validatorEstimate = summary.validator_failure_rate;
  const deterministicEstimate = summary.deterministic_delivered_detected_violation_rate;
  const latencySeconds = numeric(summary.llm_latency_ms_mean) !== undefined
    ? numeric(summary.llm_latency_ms_mean)! / 1000
    : undefined;
  const attacks = calibration?.attack_interception;
  const controls = calibration?.control_acceptance;
  const descriptors = summary.structural_descriptors;
  const corpusVersion = descriptors?.corpus_version
    ?? calibration?.corpus_version
    ?? (typeof calibration?.version === "string" ? calibration.version : undefined);
  const payloadFields = descriptors?.payload_fields?.join(", ") ?? "—";
  const evidenceFields = descriptors?.evidence_fields?.join(", ") ?? "—";
  return (
    <section className="deployed-point semantic-operational-band" aria-label="Primary semantic and operational evaluation">
      <div>
        <span className="eyebrow">Primary local-LLM evaluation context</span>
        <h2>S0 semantic and operational evidence</h2>
        <p>Readable synthetic transaction features make the raw SHAP, deterministic brief, guarded local-LLM candidate, validation decision, and fallback observable. S0 remains separate from the G0-G7 ULB detector benchmark.</p>
      </div>
      <dl>
        <div><dt>S0 Average Precision</dt><dd>{numeric(test.auc_pr)?.toFixed(3) ?? "—"}</dd></div>
        <div><dt>Recall / precision</dt><dd>{percent(test.recall)} / {percent(test.precision)}</dd></div>
        <div><dt>LLM brief accepted</dt><dd>{accepted ?? "—"}/{rows ?? "—"}</dd></div>
        <div><dt>Fallback</dt><dd>{fallbacks ?? "—"} · {percent(fallbackRate)}</dd></div>
        <div><dt>Latency</dt><dd>{latencySeconds?.toFixed(2) ?? "—"}s · n={summary.llm_latency_ms_n ?? "—"}</dd></div>
        <div><dt>Attack interception</dt><dd>{countLabel(attacks)}</dd></div>
      </dl>
      <div className="rate-list compact semantic-rate-list">
        <div><strong>Fallback delivery</strong><span>{rateLabel(fallbackEstimate)}</span></div>
        <div><strong>Transport failure</strong><span>{rateLabel(transportEstimate)}</span></div>
        <div><strong>Validator failure</strong><span>{rateLabel(validatorEstimate)}</span></div>
        <div><strong>Delivered deterministic violations</strong><span>{rateLabel(deterministicEstimate)}</span></div>
        <div><strong>Faithful controls accepted</strong><span>{controls ? `${countLabel(controls)} · ${rateLabel(controls)}` : "—"}</span></div>
        <div><strong>Corpus / top-k</strong><span>{corpusVersion ?? "—"} · top-k {descriptors?.top_k ?? "—"}</span></div>
        <div><strong>Payload fields</strong><span>{payloadFields}</span></div>
        <div><strong>Evidence fields</strong><span>{evidenceFields}</span></div>
      </div>
      <p className="semantic-band-note">
        Ollama receives only the coarse risk bucket plus ranked evidence keys, display labels, directions, ranks, and coarse value buckets; identifiers, exact amounts, detector scores, SHAP magnitudes, and labels are excluded. Semantic integrity ID: <code>{results.provenance.manifest_sha256.slice(0, 12)}…</code>
      </p>
    </section>
  );
}

export function Results() {
  const remote = useRemoteData(
    async () => {
      const [research, operational] = await Promise.all([
        api.results(),
        api.operationalResults().catch(() => undefined),
      ]);
      return { research, operational };
    },
    [],
  );
  const { openProvenance } = useDemoContext();

  if (remote.loading) return <LoadingState label="Loading validated performance results" />;
  if (remote.error) return <ErrorState error={remote.error} retry={remote.reload} />;
  if (!remote.data) return null;

  const detectors = detectorRows(remote.data.research);
  const arms = explanationArms(remote.data.research);
  const strict = arms.find((arm) => arm.arm === "strict") ?? arms[0];
  const simple = arms.find((arm) => arm.arm === "simple");
  const deployed = remote.data.research.detector_result_rows?.find((row) => row.group.toLowerCase() === "g6" && row.seed === 42);

  return (
    <div className="route-page route-enter">
      <section className="page-heading results-heading">
        <div>
          <span className="eyebrow">Research evidence</span>
          <h1>Evaluation Results</h1>
          <p>The primary result is how the local-LLM explanation layer behaves under deterministic validation and fallback. Detector benchmarking remains visible as supporting model evidence.</p>
        </div>
        <button className="button secondary" onClick={openProvenance} type="button"><FingerprintIcon /> Inspect evidence details</button>
      </section>

      <OperationalSemanticBand results={remote.data.operational} />

      <section aria-label="Evaluation boundary" className="assurance-ledger monitor-ledger">
        <div><span>Snapshot</span><strong>Verified performance snapshot</strong></div>
        <div><span>Primary question</span><strong>Can generated briefs remain faithful?</strong></div>
        <div><span>Explanation controls</span><strong>SHAP, validation, and fallback</strong></div>
        <div><span>Supporting evidence</span><strong>Six detector strategies</strong></div>
        <div><span>Monitoring scope</span><strong>Offline validation only</strong></div>
      </section>

      <section className="results-section explanation-results" aria-labelledby="explanation-results-title">
        <div className="results-section-heading">
          <div><span className="stage-number">01</span><div><h2 id="explanation-results-title">Explanation policy performance</h2><p>Detected violations, accepted local-LLM briefs, and fail-closed fallback outcomes.</p></div></div>
          <span className="result-tag is-explanation">Primary evaluation</span>
        </div>
        {strict ? (
          <>
            <div className="faithfulness-lead">
              <div><span>Validated narrative policy</span><strong>{strict.any_detected_violation ? `${(strict.any_detected_violation.rate * 100).toFixed(1)}%` : "—"}</strong><small>candidate outputs with a detected violation</small></div>
              <div><span>Fallback delivery</span><strong>{strict.fallback ? `${(strict.fallback.rate * 100).toFixed(1)}%` : "—"}</strong><small>validated policy; n={strict.fallback?.n ?? "—"}</small></div>
              <div><span>Transport unavailable</span><strong>{strict.llm_transport_unavailable_count ?? 0}</strong><small>controlled local-service failures</small></div>
              <div><span>Mean latency</span><strong>{strict.mean_latency_seconds?.toFixed(2) ?? "—"}s</strong><small>local explanation generation</small></div>
            </div>
            <PolicyRateChart arm={strict} />
            <div className="rate-list">
              <div><strong>Format detected violations</strong><span>{rateLabel(strict.format)}</span></div>
              <div><strong>Completeness detected violations</strong><span>{rateLabel(strict.completeness)}</span></div>
              <div><strong>Grounding detected violations</strong><span>{rateLabel(strict.grounding)}</span></div>
              <div><strong>Direction detected violations</strong><span>{rateLabel(strict.direction)}</span></div>
            </div>
          </>
        ) : <p className="muted">No validated narrative-policy results were returned.</p>}
        {simple ? (
          <details className="simple-arm-details">
            <summary>Show relaxed-policy comparison</summary>
            <div className="rate-list compact">
              <div><strong>Any detected violation</strong><span>{rateLabel(simple.any_detected_violation)}</span></div>
              <div><strong>Fallback</strong><span>{rateLabel(simple.fallback)}</span></div>
              <div><strong>Mean latency</strong><span>{simple.mean_latency_seconds?.toFixed(2) ?? "—"}s</span></div>
            </div>
          </details>
        ) : null}
      </section>

      {deployed ? (
        <section aria-label="Supporting model source" className="deployed-point">
          <div><span className="eyebrow">Supporting real-data detector source</span><h2>G6 seed 42 · cost-sensitive XGBoost</h2><p>This frozen ULB model supplies the anonymous SHAP evidence used by the original G4/G5 stress test. Detector selection supports the explanation study rather than forming a separate product claim.</p></div>
          <dl>
            <div><dt>Precision</dt><dd>{Number(deployed.test_precision).toFixed(3)}</dd></div>
            <div><dt>Recall</dt><dd>{Number(deployed.test_recall).toFixed(3)}</dd></div>
            <div><dt>F1</dt><dd>{Number(deployed.test_f1).toFixed(3)}</dd></div>
            <div><dt>False positive</dt><dd>{deployed.test_fp}</dd></div>
            <div><dt>Missed fraud</dt><dd>{deployed.test_fn}</dd></div>
          </dl>
        </section>
      ) : null}

      <section className="results-section" aria-labelledby="detector-results-title">
        <div className="results-section-heading">
          <div><span className="stage-number">02</span><div><h2 id="detector-results-title">Supporting detector benchmark</h2><p>ULB test metrics document how the frozen evidence source was selected. These models are supporting experiments, not separate deployed systems.</p></div></div>
          <span className="result-tag">Supporting evidence</span>
        </div>
        {detectors.length > 0 ? (
          <div className="metric-visual-grid">
            <F1BarChart detectors={detectors} />
            <DualMetricChart
              ariaLabel="Precision and recall by detector strategy"
              detectors={detectors}
              first={{ metric: "precision", label: "Precision", className: "is-precision" }}
              format={(value) => value.toFixed(3)}
              scale={1}
              second={{ metric: "recall", label: "Recall", className: "is-recall" }}
              title="Precision versus recall"
            />
            <DualMetricChart
              ariaLabel="False positives and false negatives by detector strategy"
              detectors={detectors}
              first={{ metric: "false_positives", label: "False positive", className: "is-fp" }}
              format={(value) => value.toFixed(1)}
              scale={Math.max(1, ...detectors.flatMap((result) => [metricNumber(result, "false_positives") ?? 0, metricNumber(result, "false_negatives") ?? 0]))}
              second={{ metric: "false_negatives", label: "Missed fraud", className: "is-fn" }}
              title="Error burden on the test set"
            />
          </div>
        ) : null}
        <div className="table-scroll">
          <table className="data-table results-table">
            <thead>
              <tr><th>Strategy</th><th>AUC-PR</th><th>ROC-AUC</th><th>Precision</th><th>Recall</th><th>F1</th><th>Precision@100</th><th>Recall@100</th><th>Inference</th></tr>
            </thead>
            <tbody>
              {detectors.map((result) => (
                <tr key={result.group}>
                  <td><strong>{DETECTOR_NAMES[result.group.toLowerCase()]?.name ?? "Detector strategy"}</strong><small>{DETECTOR_NAMES[result.group.toLowerCase()]?.detail ?? result.label}</small></td>
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

      <section className="results-section figure-section" aria-labelledby="pr-figure-title">
        <div className="results-section-heading">
          <div><span className="stage-number">03</span><div><h2 id="pr-figure-title">Detector appendix: precision-recall curves</h2><p>Verified curves for the supporting ULB detector strategies shown above.</p></div></div>
        </div>
        <figure>
          <img alt="Precision-recall curves for six detector training strategies" src={api.figureUrl("pr_curves")} />
          <figcaption>
            Precision–recall curves from the verified evaluation snapshot. The table above provides the numeric values.
          </figcaption>
        </figure>
      </section>

    </div>
  );
}
