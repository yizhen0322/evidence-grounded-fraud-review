import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { CaseQueue } from "./pages/CaseQueue";
import { GuardrailLab } from "./pages/GuardrailLab";
import { Investigation } from "./pages/Investigation";
import { Results } from "./pages/Results";

function LegacyCaseRedirect() {
  const { caseId = "" } = useParams();
  return <Navigate replace to={`/research/cases/${encodeURIComponent(caseId)}`} />;
}

function UnifiedQueue() {
  return <CaseQueue />;
}

function LegacyQueueRedirect({ source }: { source: "operational" | "research" }) {
  const location = useLocation();
  const params = new URLSearchParams(location.search);
  params.set("source", source);
  return <Navigate replace to={`/queue?${params.toString()}`} />;
}

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/overview" element={<Navigate replace to="/queue" />} />
        <Route path="/queue" element={<UnifiedQueue />} />
        <Route path="/cases/:caseId" element={<LegacyCaseRedirect />} />
        <Route path="/operational/queue" element={<LegacyQueueRedirect source="operational" />} />
        <Route path="/operational/cases/:caseId" element={<Investigation mode="operational" />} />
        <Route path="/research/queue" element={<LegacyQueueRedirect source="research" />} />
        <Route path="/research/cases/:caseId" element={<Investigation mode="research" />} />
        <Route path="/assurance/narratives" element={<GuardrailLab />} />
        <Route path="/assurance/performance" element={<Results />} />
        <Route path="/guardrails" element={<Navigate replace to="/assurance/narratives?mode=operational" />} />
        <Route path="/results" element={<Navigate replace to="/assurance/performance" />} />
        <Route path="/" element={<Navigate replace to="/queue" />} />
        <Route path="*" element={<Navigate replace to="/queue" />} />
      </Routes>
    </AppShell>
  );
}
