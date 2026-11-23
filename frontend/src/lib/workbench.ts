import { hashKey, useMutation, useQuery, type QueryKey } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { useInspector, type InspectorSource } from "@/contexts";
import { ApiError, get } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import type { ClassName, Inspector, MetaResponse } from "@/types/api";

export function useMeta() {
  const meta = useQuery({ queryKey: ["meta"], queryFn: ({ signal }) => get<MetaResponse>("/meta", undefined, signal) });
  useQueryError("meta", "Ringkasan dataset tidak dapat dimuat.", meta.error);
  return meta;
}

export function classLabel(meta: MetaResponse | undefined, cls: ClassName | null) {
  return cls === null ? "Kelas tidak diketahui" : meta?.class_labels_id[cls] ?? cls;
}

const decimal = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 6 });
const percent = new Intl.NumberFormat("id-ID", { style: "percent", maximumFractionDigits: 2 });
const distance = new Intl.NumberFormat("id-ID", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

export function formatNumber(value: number | null | undefined) {
  return value == null ? "—" : decimal.format(value);
}

export function formatPercent(value: number | null | undefined) {
  return value == null ? "—" : percent.format(value);
}

export function formatDistance(value: number) {
  return distance.format(value);
}

export function isSessionNotFound(error: unknown) {
  return error instanceof ApiError && error.code === "SESSION_NOT_FOUND";
}

export function useInspectorResult(page: InspectorSource, inspector: Inspector | undefined, updatedAt?: number) {
  const { setLatest } = useInspector();
  useEffect(() => {
    if (inspector) setLatest(page, inspector);
  }, [inspector, page, setLatest, updatedAt]);
}

export function useApiMutation<T, V>(mutationFn: (value: V) => Promise<T>, options: {
  onSuccess?: (data: T, value: V) => void;
  onError?: (error: Error) => void;
  success?: string;
  failure: string;
}) {
  const mutation = useMutation({ mutationFn });

  function run(value: V) {
    mutation.mutate(value, {
      onSuccess: (data, input) => {
        options.onSuccess?.(data, input);
        if (options.success) toast.success(options.success);
      },
      onError: (error) => {
        options.onError?.(error);
        toast.error(options.failure, { description: error.message });
      },
    });
  }

  return { ...mutation, run };
}

export function useDebouncedApiQuery<T>(queryKey: QueryKey, active: boolean, queryFn: (signal: AbortSignal) => Promise<T>) {
  const signature = hashKey(queryKey);
  const [readyKey, setReadyKey] = useState<string>();
  useEffect(() => {
    setReadyKey(undefined);
    if (!active) return;
    const timeout = setTimeout(() => setReadyKey(signature), 400);
    return () => clearTimeout(timeout);
  }, [active, signature]);
  // TanStack Query aborts the previous request through its AbortController when its key loses this observer.
  const query = useQuery({
    queryKey: active ? queryKey : ["inactive", ...queryKey],
    enabled: active && readyKey === signature,
    queryFn: ({ signal }) => queryFn(signal),
  });
  return { ...query, waiting: active && (readyKey !== signature || query.isFetching) };
}
