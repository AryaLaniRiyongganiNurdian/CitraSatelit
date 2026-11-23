import { useEffect } from "react";
import { toast } from "sonner";
import type { ExperimentResult } from "@/types/api";

const integer = new Intl.NumberFormat("id-ID");
const percentage = new Intl.NumberFormat("id-ID", { style: "percent", maximumFractionDigits: 2 });

export function formatInteger(value: number) {
  return integer.format(value);
}

export function formatAccuracy(value: number) {
  return percentage.format(value);
}

export function bestC2(result: ExperimentResult | undefined) {
  let best: { method: string; accuracy: number } | null = null;
  for (const table of result?.tables ?? []) {
    const methodAt = table.columns.findIndex((item) => item.trim().toLowerCase() === "metode");
    const accuracyAt = table.columns.findIndex((item) => item.trim().toLowerCase() === "akurasi");
    if (methodAt < 0 || accuracyAt < 0) continue;
    for (const row of table.rows) {
      const method = row[methodAt];
      const accuracy = row[accuracyAt];
      if (typeof method === "string" && typeof accuracy === "number" && Number.isFinite(accuracy)
          && accuracy >= 0 && accuracy <= 1 && (!best || accuracy > best.accuracy)) {
        best = { method, accuracy };
      }
    }
  }
  return best;
}

export function useQueryError(id: string, title: string, error: Error | null) {
  useEffect(() => {
    if (error) toast.error(title, { id, description: error.message });
  }, [error, id, title]);
}
