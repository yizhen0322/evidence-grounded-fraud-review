import type { WorkflowStatus } from "../api/types";

export const WORKFLOW_LABELS: Record<WorkflowStatus, string> = {
  unreviewed: "Unreviewed",
  in_review: "In review",
  needs_follow_up: "Needs follow-up",
  review_complete: "Review complete",
};

export function workflowLabel(status: WorkflowStatus): string {
  return WORKFLOW_LABELS[status];
}
