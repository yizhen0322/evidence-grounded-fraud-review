import type { CheckState, GuardrailCheckName } from "../api/types";
import { AlertIcon, CheckIcon } from "./icons";

const CHECK_LABELS: Record<GuardrailCheckName, string> = {
  format: "Format",
  completeness: "Completeness",
  grounding: "Grounding",
  direction: "Direction",
};

export function StatusBadge({
  state,
  label,
  reason,
  compact = false,
}: {
  state: CheckState;
  label: string;
  reason?: string | null;
  compact?: boolean;
}) {
  const stateClass = state === "PASS" ? "is-pass" : state === "FAIL" ? "is-fail" : "is-neutral";
  return (
    <span className={`status-badge ${stateClass}${compact ? " is-compact" : ""}`} title={reason ?? undefined}>
      {state === "PASS" ? <CheckIcon size={14} /> : <AlertIcon size={14} />}
      <span>{label}</span>
      <strong>{state.replace("_", " ")}</strong>
    </span>
  );
}

export function GuardrailBadges({
  checks,
  reasons,
}: {
  checks?: Partial<Record<GuardrailCheckName, CheckState>> | null;
  reasons?: Partial<Record<GuardrailCheckName, string | null>>;
}) {
  return (
    <div className="check-grid" aria-label="Guardrail checks">
      {(Object.keys(CHECK_LABELS) as GuardrailCheckName[]).map((name) => (
        <div className="check-item" key={name}>
          <StatusBadge state={checks?.[name] ?? "NOT_RUN"} label={CHECK_LABELS[name]} reason={reasons?.[name]} />
          {reasons?.[name] ? <p>{reasons[name]}</p> : null}
        </div>
      ))}
    </div>
  );
}
