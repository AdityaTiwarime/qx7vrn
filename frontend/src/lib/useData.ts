import { useEffect, useState } from "react";

import { api, type Accuracy, type Query, type Series } from "./api";

export interface DataState {
  series?: Series;
  accuracy?: Accuracy;
  loading: boolean;
  error?: string;
}

/** Loads chart data and accuracy for a query; cancels stale requests when the query changes. */
export function useData(q: Query): DataState {
  const [state, setState] = useState<DataState>({ loading: true });
  const key = JSON.stringify(q);

  useEffect(() => {
    const ctrl = new AbortController();
    setState((s) => ({ ...s, loading: true, error: undefined }));
    Promise.all([api.series(q, ctrl.signal), api.accuracy(q, ctrl.signal)])
      .then(([series, accuracy]) => setState({ series, accuracy, loading: false }))
      .catch((e: unknown) => {
        if (ctrl.signal.aborted) return;
        setState((s) => ({ ...s, loading: false, error: e instanceof Error ? e.message : String(e) }));
      });
    return () => ctrl.abort();
  }, [key]);

  return state;
}
