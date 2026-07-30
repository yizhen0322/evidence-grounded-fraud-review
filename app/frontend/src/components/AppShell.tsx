import { useMemo, useState, type ReactNode } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { api } from "../api/client";
import { artifactReady, normalizeScenarios, ollamaState, provenanceEntries } from "../api/normalize";
import type { Mode, OperationalProvenanceResponse, ProvenanceResponse } from "../api/types";
import { DemoContext, type DemoContextValue } from "./DemoContext";
import { ArrowIcon, ChartIcon, CloseIcon, FingerprintIcon, QueueIcon, ShieldIcon } from "./icons";
import { useRemoteData } from "./useRemoteData";

function routeIdentity(pathname: string): { group: string; title: string; detail: string } {
  if (pathname.startsWith("/operational/cases/")) {
    return { group: "S0 Operational", title: "Case Review", detail: "Readable evidence, local-LLM comparison, and analyst action" };
  }
  if (pathname.startsWith("/research/cases/") || pathname.startsWith("/cases/")) {
    return { group: "ULB Benchmark", title: "Case Review", detail: "Anonymous real-data detector evidence and analyst action" };
  }
  if (pathname.startsWith("/assurance/narratives") || pathname === "/guardrails") {
    return { group: "Explanation Layer", title: "Explanation Assurance", detail: "Deterministic checks and fail-closed fallback" };
  }
  if (pathname.startsWith("/assurance/performance") || pathname === "/results") {
    return { group: "Research Evidence", title: "Evaluation Results", detail: "Local-LLM outcomes with supporting detector evidence" };
  }
  return { group: "Analyst Workbench", title: "Alert Queue", detail: "Model-flagged transactions awaiting review" };
}

function evidenceSourceLabel(name: string): string {
  const labels: Record<string, string> = {
    detector: "Detection model",
    g4: "Model attribution",
    g5: "Narrative policy",
    results: "Performance summary",
    s0: "Operational semantic run",
  };
  return labels[name.toLowerCase()] ?? "Evidence source";
}

function ProvenanceDrawer({
  open,
  close,
  provenance,
  loading,
  error,
}: {
  open: boolean;
  close: () => void;
  provenance?: ProvenanceResponse | OperationalProvenanceResponse;
  loading: boolean;
  error?: Error;
}) {
  const entries = provenanceEntries(provenance);
  const operational = provenance !== undefined && "run_id" in provenance;
  const verified = operational
    ? provenance.synthetic === true && provenance.group === "s0" && entries.length > 0
    : provenance?.source_chain_valid === true
      && provenance?.source_code_compatible === true
      && entries.length > 0;
  const invalid = operational
    ? false
    : provenance?.source_chain_valid === false
      || provenance?.source_code_compatible === false;
  const integrityLabel = verified
    ? operational ? "Operational semantic evidence verified" : "Source chain verified"
    : invalid
      ? "Source chain mismatch"
      : loading
        ? "Verification in progress"
        : "Verification unavailable";
  const integrityClass = verified ? "is-good" : invalid ? "is-danger" : "is-warning";
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
        aria-label="Evidence details"
        className={`provenance-drawer ${open ? "is-open" : ""}`}
        inert={!open}
      >
        <div className="drawer-heading">
          <div>
            <span className="eyebrow">Evidence integrity</span>
            <h2>Evidence integrity details</h2>
          </div>
          <button className="icon-button" aria-label="Close provenance drawer" onClick={close} type="button">
            <CloseIcon />
          </button>
        </div>
        <p className="drawer-intro">
          Model evidence is loaded from immutable, hash-verified snapshots. Analyst notes and decisions are stored separately.
        </p>
        <div className={`integrity-line ${integrityClass}`}>
          <span className={`signal ${integrityClass}`} />
          <strong>{integrityLabel}</strong>
        </div>
        {error ? <p className="muted">Evidence details could not be loaded. Treat this evidence state as unverified.</p> : null}
        <dl className="provenance-list">
          {entries.map(([name, entry]) => (
            <div key={name}>
              <dt>{evidenceSourceLabel(name)}</dt>
              <dd>
                <span>Verified snapshot</span>
                <code title={entry.manifest_sha256}>Integrity ID {entry.manifest_sha256.slice(0, 12)}…</code>
              </dd>
            </div>
          ))}
        </dl>
        {entries.length === 0 ? <p className="muted">Evidence details are loading.</p> : null}
        <div className="drawer-note">
          <strong>Evidence/workflow separation</strong>
          <p>Workflow notes and dispositions never modify model outputs or explanation evidence.</p>
        </div>
      </aside>
    </>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<Mode>("recorded");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const location = useLocation();
  const queryMode = new URLSearchParams(location.search).get("mode");
  const unifiedQueueRoute = location.pathname === "/queue";
  const operationalRoute = location.pathname.startsWith("/operational")
    || (location.pathname.startsWith("/assurance/narratives") && queryMode !== "research");
  const health = useRemoteData(api.health, []);
  const provenance = useRemoteData<ProvenanceResponse | OperationalProvenanceResponse>(
    () => {
      if (unifiedQueueRoute) {
        return Promise.all([
          api.provenance(),
          api.operationalResults().catch(() => undefined),
        ]).then(([research, operational]) => operational === undefined
          ? research
          : {
              artifacts: {
                ...Object.fromEntries(provenanceEntries(research)),
                s0: {
                  run_id: operational.provenance.run_id,
                  manifest_sha256: operational.provenance.manifest_sha256,
                  group: operational.provenance.group,
                },
              },
              source_chain_valid: research.source_chain_valid === true && operational.provenance.synthetic === true,
              source_code_compatible: research.source_code_compatible === true,
            });
      }
      return operationalRoute
        ? api.operationalResults().then((result) => result.provenance)
        : api.provenance();
    },
    [operationalRoute, unifiedQueueRoute],
  );
  const scenariosRemote = useRemoteData(api.scenarios, []);
  const summaryRemote = useRemoteData(
    () => {
      if (unifiedQueueRoute) {
        return Promise.all([
          api.workflowSummary(),
          api.operationalWorkflowSummary().catch(() => undefined),
        ]).then(([research, operational]) => ({
          total: research.total + (operational?.total ?? 0),
          counts: {
            unreviewed: research.counts.unreviewed + (operational?.counts.unreviewed ?? 0),
            in_review: research.counts.in_review + (operational?.counts.in_review ?? 0),
            needs_follow_up: research.counts.needs_follow_up + (operational?.counts.needs_follow_up ?? 0),
            review_complete: research.counts.review_complete + (operational?.counts.review_complete ?? 0),
          },
          recorded_fallback: research.recorded_fallback + (operational?.recorded_fallback ?? 0),
          evidence_fingerprint: operational
            ? `${research.evidence_fingerprint}:${operational.evidence_fingerprint}`
            : research.evidence_fingerprint,
        }));
      }
      return operationalRoute ? api.operationalWorkflowSummary() : api.workflowSummary();
    },
    [operationalRoute, unifiedQueueRoute],
  );
  const scenarios = useMemo(() => normalizeScenarios(scenariosRemote.data), [scenariosRemote.data]);
  const caseId = location.pathname.match(/^\/(?:operational|research|)\/?cases\/([^/]+)/)?.[1]
    ?? (operationalRoute ? new URLSearchParams(location.search).get("case_id") ?? undefined : undefined);
  const readiness = artifactReady(health.data);
  const ollama = ollamaState(health.data);
  const workflowState = health.data?.workflow_status ?? (health.loading ? "checking" : "unavailable");
  const identity = location.pathname === "/queue"
    ? {
        group: "Analyst Workbench",
        title: "Alert Queue",
        detail: "S0 explanation cases by default; ULB supporting benchmark available",
      }
    : operationalRoute && location.pathname.startsWith("/assurance/narratives")
      ? { group: "Explanation Layer", title: "Explanation Assurance", detail: "S0 semantic checks and deterministic fallback" }
      : routeIdentity(location.pathname);
  const currentProvenance = provenance.data;
  const operationalProvenance = currentProvenance !== undefined && "run_id" in currentProvenance;
  const provenanceVerified = operationalProvenance
    ? currentProvenance.synthetic === true && currentProvenance.group === "s0"
    : currentProvenance?.source_chain_valid === true
      && currentProvenance?.source_code_compatible === true;
  const provenanceInvalid = operationalProvenance
    ? false
    : currentProvenance?.source_chain_valid === false
      || currentProvenance?.source_code_compatible === false;
  const evidenceLabel = provenanceVerified
    ? operationalProvenance ? "Operational evidence verified" : "Evidence verified"
    : provenanceInvalid
      ? "Evidence mismatch"
      : provenance.loading
        ? "Checking evidence"
        : "Evidence unverified";

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
              <span>Guarded Explanation System</span>
            </div>
          </div>

          <nav aria-label="Primary navigation" className="primary-nav">
            <div className="nav-section">
              <span className="nav-section-label">Work</span>
              <NavLink title="Alert Queue" to="/queue">
                <QueueIcon />
              <span><strong>Alert Queue</strong><small>S0 default; ULB labelled</small></span>
              </NavLink>
            </div>
            <div className="nav-section">
              <span className="nav-section-label">Assurance</span>
              <NavLink title="Explanation Assurance" to="/assurance/narratives?mode=operational">
                <ShieldIcon />
                <span><strong>Explanation Assurance</strong><small>Guardrails and fallback</small></span>
              </NavLink>
              <NavLink title="Evaluation Results" to="/assurance/performance">
                <ChartIcon />
                <span><strong>Evaluation Results</strong><small>LLM first; detector supporting</small></span>
              </NavLink>
            </div>
          </nav>

          <div className="sidebar-integrity" aria-label="Local system state">
            <span className="prototype-label">LOCAL ANALYST SYSTEM</span>
            <div><span className={readiness === false ? "signal is-danger" : readiness === true ? "signal is-good" : "signal"} /><span>{readiness === false ? "Evidence invalid" : readiness === true ? "Evidence verified" : "Checking evidence"}</span></div>
            <div><span className={ollama === "available" ? "signal is-good" : ollama === "unavailable" ? "signal is-warning" : "signal"} /><span>Narrative service {ollama}</span></div>
            <div>
              <span className={workflowState === "ready" ? "signal is-good" : workflowState === "unavailable" ? "signal is-danger" : "signal"} />
              <span>Case workflow {workflowState}</span>
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
              <span className={`evidence-mode-label ${provenanceVerified ? "is-verified" : provenanceInvalid ? "is-invalid" : "is-checking"}`}>{evidenceLabel}</span>
              <button className="header-action" onClick={() => setDrawerOpen(true)} type="button">
                <FingerprintIcon /> Evidence details
              </button>
            </div>
          </header>

          <div className="context-bar" aria-label="Current workload">
            <div className="context-mode"><strong>{summaryRemote.data?.counts.unreviewed ?? "—"}</strong><span>unreviewed</span></div>
            <div><strong>{summaryRemote.data?.counts.in_review ?? "—"}</strong><span>in review</span></div>
            <div><strong>{summaryRemote.data?.counts.needs_follow_up ?? "—"}</strong><span>follow-up</span></div>
            <div><strong>{summaryRemote.data?.recorded_fallback ?? "—"}</strong><span>fallback briefs</span></div>
          </div>

          <main className="app-main">{children}</main>

          <footer className="app-footer">
            <span>Decision-support system · final routing remains a human responsibility</span>
            <button type="button" onClick={() => setDrawerOpen(true)}>Inspect evidence boundary <ArrowIcon size={14} /></button>
          </footer>
        </div>

        <ProvenanceDrawer
          open={drawerOpen}
          close={() => setDrawerOpen(false)}
          provenance={provenance.data}
          loading={provenance.loading}
          error={provenance.error}
        />
      </div>
    </DemoContext.Provider>
  );
}
