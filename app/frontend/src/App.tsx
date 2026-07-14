import { Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { CaseQueue } from "./pages/CaseQueue";
import { GuardrailLab } from "./pages/GuardrailLab";
import { Investigation } from "./pages/Investigation";
import { Results } from "./pages/Results";

export default function App() {
  return (
    <AppShell>
      <Routes>
        <Route path="/queue" element={<CaseQueue />} />
        <Route path="/cases/:caseId" element={<Investigation />} />
        <Route path="/assurance/narratives" element={<GuardrailLab />} />
        <Route path="/assurance/performance" element={<Results />} />
        <Route path="/guardrails" element={<Navigate replace to="/assurance/narratives" />} />
        <Route path="/results" element={<Navigate replace to="/assurance/performance" />} />
        <Route path="/" element={<Navigate replace to="/queue" />} />
        <Route path="*" element={<Navigate replace to="/queue" />} />
      </Routes>
    </AppShell>
  );
}
