import { useCallback, useEffect, useState } from "react";

export interface RemoteState<T> {
  data?: T;
  error?: Error;
  loading: boolean;
  reload: () => void;
}

export function useRemoteData<T>(loader: () => Promise<T>, dependencies: readonly unknown[] = []): RemoteState<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<Error>();
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);

  const reload = useCallback(() => setRevision((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(undefined);
    loader()
      .then((value) => {
        if (!controller.signal.aborted) setData(value);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason : new Error("The recorded data could not be loaded."));
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
    // Loader identity is intentionally controlled by the caller's dependency list.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencies, revision]);

  return { data, error, loading, reload };
}
