import { useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api } from "../api/client";
import { artifactReady, normalizeScenarios, ollamaState, provenanceEntries } from "../api/normalize";
import type { Mode, ProvenanceResponse } from "../api/types";
import { DemoContext, type DemoContextValue } from "./DemoContext";
import { ArrowIcon, ChartIcon, CloseIcon, FingerprintIcon, QueueIcon, ShieldIcon } from "./icons";
import { useRemoteData } from "./useRemoteData";

function routeIdentity(pathname: string): { group: string; title: string; detail: string } {
  if (pathname.startsWith("/cases/")) {
    return { group: "Operations", title: "Investigation Workspace", detail: "Evidence review and provisional disposition" };
  }
  if (pathname.startsWith("/assurance/narratives") || pathname === "/guardrails") {
    return { group: "Model Assurance", title: "Narrative Assurance", detail: "Guardrail policy and fallback testing" };
  }
  if (pathname.startsWith("/assurance/performance") || pathname === "/results") {
    return { group: "Model Assurance", title: "Model & Policy Monitor", detail: "Recorded evaluation evidence" };
  }
  return { group: "Operations", title: "Work Queue", detail: "Review model-flagged cases" };
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
            <h2>Evidence provenance</h2>
          </div>
          <button className="icon-button" aria-label="Close provenance drawer" onClick={close} type="button">
            <CloseIcon />
          </button>
        </div>
        <p className="drawer-intro">
          Research evidence is served from immutable, hash-verified snapshots. Analyst workflow metadata is stored separately.
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
          <strong>Evidence/workflow separation</strong>
          <p>Workflow notes and dispositions never modify detector, G4, G5, or report artifacts.</p>
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
  const location = useLocation();
  const caseId = location.pathname.match(/^\/cases\/([^/]+)/)?.[1];
  const readiness = artifactReady(health.data);
  const ollama = ollamaState(health.data);
  const workflowState = health.data?.workflow_status ?? (health.loading ? "checking" : "unavailable");
  const identity = routeIdentity(location.pathname);

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
        <aside className="app-sidebar">
          <div className="brand-block">
            <div className="brand-mark" aria-hidden="true">FR</div>
            <div>
              <strong>Fraud Review</strong>
              <span>Analyst Workbench</span>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="primary-nav">
            <div className="nav-section">
              <span className="nav-section-label">Operations</span>
              <NavLink to="/queue">
                <QueueIcon />
                <span><strong>Work Queue</strong><small>Review flagged cases</small></span>
              </NavLink>
            </div>
            <div className="nav-section">
              <span className="nav-section-label">Model Assurance</span>
              <NavLink to="/assurance/narratives">
                <ShieldIcon />
                <span><strong>Narrative Assurance</strong><small>Guardrails and fallback</small></span>
              </NavLink>
              <NavLink to="/assurance/performance">
                <ChartIcon />
                <span><strong>Model & Policy</strong><small>Recorded evaluation</small></span>
              </NavLink>
            </div>
          </nav>

          <div className="sidebar-integrity" aria-label="Local system state">
            <span className="prototype-label">LOCAL FYP PROTOTYPE</span>
            <div><span className={readiness === false ? "signal is-danger" : readiness === true ? "signal is-good" : "signal"} /><span>{readiness === false ? "Evidence invalid" : readiness === true ? "Evidence verified" : "Checking evidence"}</span></div>
            <div><span className={ollama === "available" ? "signal is-good" : ollama === "unavailable" ? "signal is-warning" : "signal"} /><span>Ollama {ollama}</span></div>
            <div>
              <span className={workflowState === "ready" ? "signal is-good" : workflowState === "unavailable" ? "signal is-danger" : "signal"} />
              <span>Workflow store {workflowState}</span>
            </div>
          </div>
        </aside>

        <div className="app-frame">
          <header className="app-header">
            <div className="command-context">
              <span>{identity.group}</span>
              <strong>{identity.title}</strong>
              <small>{caseId ? `Case ${caseId}` : identity.detail}</small>
            </div>
            <div className="header-actions">
              <span className="evidence-mode-label">RECORDED EVIDENCE</span>
              <button className="header-action" onClick={() => setDrawerOpen(true)} type="button">
                <FingerprintIcon /> Provenance
              </button>
            </div>
          </header>

          <div className="context-bar" aria-label="System status">
            <div className="context-mode">
              <strong>Immutable evidence plane</strong>
              <span>Detector, G4, G5 and report artifacts are read-only</span>
            </div>
            <div className="context-location">
              <span>Local workflow plane</span>
              <strong>Notes and provisional decisions only</strong>
            </div>
          </div>

          <main className="app-main">{children}</main>

          <footer className="app-footer">
            <span>Local analyst decision-support prototype · not a deployed fraud-decision system</span>
            <button type="button" onClick={() => setDrawerOpen(true)}>Inspect evidence boundary <ArrowIcon size={14} /></button>
          </footer>
        </div>

        <ProvenanceDrawer open={drawerOpen} close={() => setDrawerOpen(false)} provenance={provenance.data} />
      </div>
    </DemoContext.Provider>
  );
}
