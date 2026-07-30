import { createContext, useContext } from "react";
import type { DemoScenario, HealthResponse, Mode, OperationalProvenanceResponse, ProvenanceResponse } from "../api/types";

export interface DemoContextValue {
  mode: Mode;
  setMode: (mode: Mode) => void;
  health?: HealthResponse;
  provenance?: ProvenanceResponse | OperationalProvenanceResponse;
  scenarios: DemoScenario[];
  openProvenance: () => void;
}

export const DemoContext = createContext<DemoContextValue | null>(null);

export function useDemoContext(): DemoContextValue {
  const value = useContext(DemoContext);
  if (!value) throw new Error("useDemoContext must be used inside AppShell");
  return value;
}
