import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import type { AttackPreset, GuardrailDemoResponse } from "../api/types";
import { useDemoContext } from "../components/DemoContext";
import { AlertIcon, ArrowIcon, RefreshIcon, ShieldIcon } from "../components/icons";
import { GuardrailBadges } from "../components/StatusBadge";

const PRESETS: Array<{
  value: AttackPreset;
  label: string;
  detail: string;
  expected: string;
}> = [
  {
    value: "direction_flip",
    label: "Direction flip",
    detail: "Reverse one recorded contribution direction.",
    expected: "Direction must FAIL",
  },
  {
    value: "unlisted_feature",
    label: "Unlisted feature",
    detail: "Inject a feature absent from this case evidence.",
    expected: "Grounding must FAIL",
  },
  {
    value: "template_corruption",
    label: "Template corruption",
    detail: "Remove or rename a required narrative section.",
    expected: "Format must FAIL",
  },
];

export function GuardrailLab() {
  const { scenarios } = useDemoContext();
  const [params, setParams] = useSearchParams();
  const attackCase = scenarios.find((item) => item.kind === "attack" || item.key === "attack");
  const [caseId, setCaseId] = useState(() => Number(params.get("case_id") ?? attackCase?.case_id ?? 42009));
  const [preset, setPreset] = useState<AttackPreset>("direction_flip");
  const [result, setResult] = useState<GuardrailDemoResponse>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(false);
  const selectedPreset = useMemo(() => PRESETS.find((item) => item.value === preset)!, [preset]);
  const availableCases = useMemo(() => {
    const candidates = scenarios.filter((item) =>
      item.kind === "attack" || item.kind === "faithful" || item.key === "attack" || item.key === "faithful",
    );
    const unique = [...new Map(candidates.map((item) => [item.case_id, item])).values()];
    return unique.length > 0 ? unique : [{ case_id: 42009, description: "Verified attack-compatible case" }];
  }, [scenarios]);

  useEffect(() => {
    if (!params.get("case_id") && attackCase) setCaseId(attackCase.case_id);
  }, [attackCase, params]);

  const runValidation = async () => {
    setLoading(true);
    setError(undefined);
    try {
      setResult(await api.guardrailDemo(caseId, preset));
    } catch (reason) {
      setError(reason instanceof Error ? reason : new Error("The deterministic validator demo could not run."));
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    const nextCase = attackCase?.case_id ?? 42009;
    setCaseId(nextCase);
    setPreset("direction_flip");
    setResult(undefined);
    setError(undefined);
    setParams({ case_id: String(nextCase) }, { replace: true });
  };

  return (
    <div className="route-page route-enter">
      <section className="page-heading guardrail-heading">
        <div>
          <span className="eyebrow">Model Assurance</span>
          <h1>Narrative Assurance</h1>
          <p>Controlled policy tests use recorded evidence and the real <code>validate_narrative()</code> implementation.</p>
        </div>
        <div className="lab-principle">
          <ShieldIcon size={24} />
          <span><strong>Fail closed, then fall back</strong><small>Assurance testing · not a reported G5 run.</small></span>
        </div>
      </section>

      <section aria-label="Narrative assurance boundary" className="assurance-ledger">
        <div><span>Validator</span><strong>Real source implementation</strong></div>
        <div><span>Evidence</span><strong>Recorded and provenance-bound</strong></div>
        <div><span>Delivery policy</span><strong>Reject → reason-code fallback</strong></div>
        <div><span>Persistence</span><strong>Controlled mutations are not saved</strong></div>
      </section>

      <div className="lab-layout">
        <aside className="lab-controls" aria-label="Guardrail attack controls">
          <div className="section-heading-line">
            <div><span className="eyebrow">Controlled test</span><h2>Select a policy challenge</h2></div>
            <span className="stage-number">01</span>
          </div>
          <label className="control-field">
            <span>Attack-compatible case</span>
            <select value={caseId} onChange={(event) => {
              const value = Number(event.target.value);
              setCaseId(value);
              setParams({ case_id: String(value) }, { replace: true });
              setResult(undefined);
            }}>
              {availableCases.map((item) => <option key={item.case_id} value={item.case_id}>Case {item.case_id}</option>)}
            </select>
          </label>
          <fieldset className="preset-fieldset">
            <legend>Mutation preset</legend>
            {PRESETS.map((item, index) => (
              <label className={preset === item.value ? "preset-option is-selected" : "preset-option"} key={item.value}>
                <input
                  checked={preset === item.value}
                  name="preset"
                  onChange={() => { setPreset(item.value); setResult(undefined); }}
                  type="radio"
                  value={item.value}
                />
                <span className="preset-number">0{index + 1}</span>
                <span><strong>{item.label}</strong><small>{item.detail}</small><em>{item.expected}</em></span>
              </label>
            ))}
          </fieldset>
          <div className="lab-actions">
            <button className="button primary" disabled={loading} onClick={runValidation} type="button">
              {loading ? "Validating…" : "Run assurance test"}
            </button>
            <button className="button text-button" onClick={reset} type="button"><RefreshIcon /> Reset</button>
          </div>
          <p className="control-footnote">The browser submits only <code>case_id</code> and an allowlisted preset. This assurance path cannot accept arbitrary text.</p>
        </aside>

        <section className="lab-output" aria-labelledby="lab-output-title">
          <div className="section-heading-line">
            <div><span className="eyebrow">Policy trace</span><h2 id="lab-output-title">Validation decision</h2></div>
            <span className="stage-number">02</span>
          </div>
          {!result && !error ? (
            <div className="lab-awaiting">
              <div className="lab-glyph" aria-hidden="true"><span /><span /><span /></div>
              <strong>{selectedPreset.label} is ready</strong>
              <p>Run the preset to compare the faithful recorded text with its deterministic mutation.</p>
            </div>
          ) : null}
          {error ? (
            <div className="degraded-state" role="alert"><AlertIcon /><div><strong>Validation unavailable</strong><p>{error.message}</p></div></div>
          ) : null}
          {result ? (
            <div className="lab-result" aria-live="polite">
              <div className="comparison-grid">
                <article>
                  <span className="comparison-label is-original">Original faithful narrative</span>
                  <pre>{result.original_text}</pre>
                </article>
                <article>
                  <span className="comparison-label is-tampered">Tampered narrative · {selectedPreset.label}</span>
                  <pre>{result.tampered_text}</pre>
                </article>
              </div>
              <div className="validator-verdict">
                <div>
                  <span className="eyebrow">Real validator decision</span>
                  <h3>{result.fallback ? "Rejected → fallback active" : "Unexpectedly accepted"}</h3>
                  <p>{result.fallback_reason?.replaceAll("_", " ") ?? "Four independent checks were recomputed."}</p>
                </div>
                <span className={result.fallback ? "verdict-mark is-rejected" : "verdict-mark is-accepted"}>
                  {result.fallback ? "REJECT" : "ACCEPT"}
                </span>
              </div>
              <GuardrailBadges checks={result.checks} reasons={result.check_reasons ?? result.failure_reasons} />
              <div className="fallback-output">
                <AlertIcon />
                <div><strong>Deterministic fallback delivered</strong><p>{result.final_text}</p></div>
              </div>
              <Link className="inline-link" to={`/cases/${result.case_id}`}>Return to Investigation Workspace <ArrowIcon size={14} /></Link>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
