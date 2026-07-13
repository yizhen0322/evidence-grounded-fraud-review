import { AlertIcon, RefreshIcon } from "./icons";

export function LoadingState({ label = "Loading verified artifacts" }: { label?: string }) {
  return (
    <div className="page-state" role="status" aria-live="polite">
      <span className="loading-mark" aria-hidden="true" />
      <div>
        <strong>{label}</strong>
        <p>Reading the immutable dashboard snapshot.</p>
      </div>
    </div>
  );
}

export function ErrorState({ error, retry }: { error: Error; retry?: () => void }) {
  return (
    <div className="page-state is-error" role="alert">
      <AlertIcon size={22} />
      <div>
        <strong>Recorded evidence is unavailable</strong>
        <p>{error.message}</p>
      </div>
      {retry ? (
        <button className="button secondary" type="button" onClick={retry}>
          <RefreshIcon size={15} /> Retry
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, detail }: { title: string; detail: string }) {
  return (
    <div className="page-state is-empty">
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
    </div>
  );
}
