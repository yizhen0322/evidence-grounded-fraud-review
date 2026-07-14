import { useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { artifactReady, normalizeScenarios, ollamaState, provenanceEntries } from "../api/normalize";
import type { Mode, ProvenanceResponse } from "../api/types";
import { DemoContext, type DemoContextValue } from "./DemoContext";
import { ArrowIcon, ChartIcon, CloseIcon, FingerprintIcon, QueueIcon, RefreshIcon, ShieldIcon } from "./icons";
import { useRemoteData } from "./useRemoteData";

function ModeSwitch({ mode, setMode }: Pick<DemoContextValue, "mode" | "setMode">) {
  return (
    <div className="mode-switch" aria-label="Narrative mode">
      <button
        aria-pressed={mode === "recorded"}
        className={mode === "recorded" ? "is-active" : ""}
        onClick={() => setMode("recorded")}
        type="button"
      >
        Recorded
      </button>
      <button
        aria-pressed={mode === "live"}
        className={mode === "live" ? "is-active" : ""}
        onClick={() => setMode("live")}
        type="button"
      >
        Live replay
      </button>
    </div>
  );
}

function ProvenanceDrawer({
  open,
  close,
  provenance,
}: {
  open: boolean;
  close: () => void;
  provenance?: ProvenanceResponse;
}) {
  const entries = provenanceEntries(provenance);
  return (
    <>
      <button
        aria-hidden={!open}
        aria-label="Close provenance drawer"
        className={`drawer-scrim ${open ? "is-open" : ""}`}
        onClick={close}
        tabIndex={open ? 0 : -1}
        type="button"
      />
      <aside
        aria-hidden={!open}
        aria-label="Artifact provenance"
        className={`provenance-drawer ${open ? "is-open" : ""}`}
        inert={!open}
      >
        <div className="drawer-heading">
          <div>
            <span className="eyebrow">Verified source chain</span>
            <h2>Provenance</h2>
          </div>
          <button className="icon-button" aria-label="Close provenance drawer" onClick={close} type="button">
            <CloseIcon />
          </button>
        </div>
        <p className="drawer-intro">
          Recorded values are served from an immutable, hash-verified snapshot. Local filesystem paths are never exposed.
        </p>
        <div className="integrity-line">
          <span className={provenance?.source_chain_valid === false ? "signal is-danger" : "signal is-good"} />
          <strong>{provenance?.source_chain_valid === false ? "Source chain mismatch" : "Source chain verified"}</strong>
        </div>
        <dl className="provenance-list">
          {entries.map(([name, entry]) => (
            <div key={name}>
              <dt>{name.toUpperCase()}</dt>
              <dd>
                <span>{entry.run_id}</span>
                <code title={entry.manifest_sha256}>{entry.manifest_sha256.slice(0, 12)}…</code>
              </dd>
            </div>
          ))}
        </dl>
        {entries.length === 0 ? <p className="muted">Provenance details are loading.</p> : null}
        <div className="drawer-note">
          <strong>Same guardrail code</strong>
          <p>
            Relevant narrative source hashes {provenance?.source_code_compatible === false ? "do not match" : "match"} the evaluated G5 run.
          </p>
        </div>
      </aside>
    </>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("recorded");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const health = useRemoteData(api.health, []);
  const provenance = useRemoteData(api.provenance, []);
  const scenariosRemote = useRemoteData(api.scenarios, []);
  const scenarios = useMemo(() => normalizeScenarios(scenariosRemote.data), [scenariosRemote.data]);
  const navigate = useNavigate();
  const location = useLocation();
  const caseId = location.pathname.match(/^\/cases\/([^/]+)/)?.[1];
  const readiness = artifactReady(health.data);
  const ollama = ollamaState(health.data);

  const resetDemo = () => {
    setMode("recorded");
    const faithful = scenarios.find((item) => item.kind === "faithful" || item.key === "faithful");
    navigate(faithful ? `/cases/${faithful.case_id}` : "/queue");
  };

  const context = useMemo<DemoContextValue>(
    () => ({
      mode,
      setMode,
      health: health.data,
      provenance: provenance.data,
      scenarios,
      openProvenance: () => setDrawerOpen(true),
    }),
    [mode, health.data, provenance.data, scenarios],
  );

  return (
    <DemoContext.Provider value={context}>
      <div className="app-shell">
        <header className="app-header">
          <div className="brand-block">
            <div className="brand-mark" aria-hidden="true">FE</div>
            <div>
              <strong>Fraud Evidence Console</strong>
              <span>Frozen detector → SHAP evidence → local narrative</span>
            </div>
          </div>
          <nav aria-label="Primary navigation" className="primary-nav">
            <NavLink to="/queue"><QueueIcon /> Queue</NavLink>
            <NavLink to="/guardrails"><ShieldIcon /> Guardrail Lab</NavLink>
            <NavLink to="/results"><ChartIcon /> Results</NavLink>
          </nav>
          <div className="header-actions">
            <ModeSwitch mode={mode} setMode={setMode} />
            <button className="header-action" onClick={() => setDrawerOpen(true)} type="button">
              <FingerprintIcon /> Provenance
            </button>
            <button className="icon-button reset-button" aria-label="Reset demo" onClick={resetDemo} type="button">
              <RefreshIcon />
            </button>
          </div>
        </header>
        <div className="context-bar" aria-label="System status">
          <div>
            <span className={readiness === false ? "signal is-danger" : readiness === true ? "signal is-good" : "signal"} />
            <span>{readiness === false ? "Artifacts invalid" : readiness === true ? "Artifacts ready" : "Checking artifacts"}</span>
          </div>
          <div>
            <span className={ollama === "available" ? "signal is-good" : ollama === "unavailable" ? "signal is-warning" : "signal"} />
            <span>Ollama {ollama}</span>
          </div>
          <div className="context-mode">
            <strong>{mode === "recorded" ? "Recorded evidence" : "Live replay"}</strong>
            <span>{mode === "recorded" ? "Reportable frozen output" : "Demo-only; not a reported G5 result"}</span>
          </div>
          <div className="context-location">
            {caseId ? <><span>Selected case</span><code>{caseId}</code></> : <span>{location.pathname === "/results" ? "Research results" : location.pathname === "/guardrails" ? "Guardrail workspace" : "Flagged case queue"}</span>}
          </div>
        </div>
        <main className="app-main">
          {children}
        </main>
        <footer className="app-footer">
          <span>Privacy-conscious local deployment</span>
          <button type="button" onClick={() => setDrawerOpen(true)}>Inspect source chain <ArrowIcon size={14} /></button>
        </footer>
        <ProvenanceDrawer open={drawerOpen} close={() => setDrawerOpen(false)} provenance={provenance.data} />
      </div>
    </DemoContext.Provider>
  );
}
