import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChartRenderer } from "@/components/chart-renderer";
import { Button } from "@/components/ui/button";
import { Slider } from "@/components/ui/slider";
import { DataTable, Empty, Panel, RequestState, Stats } from "@/components/workbench";
import { ApiError, get, post } from "@/lib/api";
import { useQueryError } from "@/lib/home-data";
import { classLabel, formatNumber, formatPercent, useDebouncedApiQuery } from "@/lib/workbench";
import { BIN_OPTIONS, type EvaluateResponse, type LiveBinsRequest, type LiveBinsResponse, type LiveCbirRequest, type MetaResponse } from "@/types/api";
import type { Criteria } from "./feature-controls";

function Evaluation({ data, meta }: { data: EvaluateResponse; meta: MetaResponse | undefined }) {
  const classes = data.classes.map((cls) => classLabel(meta, cls));
  return <div className="lab-stack">
    <Stats items={[
      { label: "P@" + data.protocol.k + " makro", value: formatPercent(data.macro_precision_at_k) },
      { label: "Akurasi kNN", value: formatPercent(data.knn_accuracy) },
      { label: "Citra uji", value: formatNumber(data.protocol.n_queries) },
      { label: "Basis latih", value: formatNumber(data.protocol.db_size) },
      ...(data.elapsed_ms === undefined ? [] : [{ label: "Waktu", value: formatNumber(data.elapsed_ms) + " ms" }]),
    ]} />
    <ChartRenderer spec={{ kind: "bar", title: "Precision@" + data.protocol.k + " per kelas",
      x: data.per_class.map((row) => classLabel(meta, row.cls)),
      series: [{ name: "P@" + data.protocol.k, y: data.per_class.map((row) => row.precision_at_k) }] }} />
    <ChartRenderer spec={{ kind: "heatmap", title: "Matriks kebingungan",
      z: data.confusion_matrix, x_labels: classes, y_labels: classes, x_label: "Prediksi", y_label: "Kelas asli" }} />
  </div>;
}

export function EvalPanel({ criteria, meta }: { criteria: Criteria; meta: MetaResponse | undefined }) {
  const [requested, setRequested] = useState<Criteria>();
  const evaluation = useQuery({
    queryKey: ["evaluate", requested], enabled: Boolean(requested),
    queryFn: ({ signal }) => get<EvaluateResponse>("/cbir/evaluate", requested, signal),
  });
  useQueryError("cbir-evaluate", "Evaluasi tidak dapat dimuat.", evaluation.error);
  const error = evaluation.error;
  const unavailable = error instanceof ApiError && error.code === "NOT_PRECOMPUTED";
  const combinations = error instanceof ApiError ? error.details?.available : undefined;
  const available = Array.isArray(combinations)
    ? combinations.filter((value: unknown): value is string => typeof value === "string") : [];
  return <Panel title="Evaluasi tersimpan" id="evaluasi">
    <p className="dim">P@k dan akurasi pada data uji dengan basis data latih.</p>
    <div className="lab-actions"><Button type="button" variant="outline" disabled={!meta || evaluation.isFetching}
      onClick={() => setRequested(criteria)}>Tampilkan evaluasi</Button>
      {requested && <span className="mono dim">{requested.mode} · {requested.metric} · {requested.bins} bin</span>}
    </div>
    {unavailable ? <div className="lab-stack">
      <Empty>Evaluasi untuk kombinasi ini belum dihitung. Gunakan percobaan langsung atau pilih kombinasi lain.</Empty>
      {available.length > 0 && <details><summary>Lihat kombinasi yang tersedia</summary>
        <ul className="lab-available">{available.map((item) => <li key={item}>{item}</li>)}</ul>
      </details>}
    </div> : <RequestState pending={Boolean(requested) && evaluation.isPending} error={evaluation.error}
      empty="Tampilkan evaluasi untuk membaca hasil konfigurasi aktif.">
      {evaluation.data && <Evaluation data={evaluation.data} meta={meta} />}
    </RequestState>}
  </Panel>;
}

export function LivePanel({ criteria, meta, k }: { criteria: Criteria; meta: MetaResponse | undefined; k: number }) {
  const [active, setActive] = useState<"cbir" | "bins" | null>(null);
  const [dbSize, setDbSize] = useState(30);
  const [queryCount, setQueryCount] = useState(5);
  const numClasses = Math.max(meta?.classes.length ?? 10, 1);
  const maxDatabase = Math.min(60, Math.floor((meta?.limits.live_max_db ?? 600) / numClasses));
  const maxQueries = Math.min(10, Math.floor((meta?.limits.live_max_queries ?? 100) / numClasses));
  const supportsBins = Boolean(meta?.feature_modes.find((item) => item.mode === criteria.mode)?.supports_bins);
  const workload = { db_per_class: Math.min(dbSize, maxDatabase), queries_per_class: Math.min(queryCount, maxQueries) };
  const cbirBody: LiveCbirRequest = { ...criteria, ...workload, k };
  const binsBody: LiveBinsRequest = { mode: criteria.mode, metric: criteria.metric, ...workload, bins_list: [...(meta?.bins_options ?? BIN_OPTIONS)] };
  const cbir = useDebouncedApiQuery(["live", "cbir", cbirBody], active === "cbir",
    (signal) => post<EvaluateResponse, LiveCbirRequest>("/live/cbir", cbirBody, signal));
  const bins = useDebouncedApiQuery(["live", "bins", binsBody], active === "bins" && supportsBins,
    (signal) => post<LiveBinsResponse, LiveBinsRequest>("/live/bins", binsBody, signal));
  useQueryError("live-cbir", "Percobaan langsung gagal.", active === "cbir" ? cbir.error : null);
  useQueryError("live-bins", "Perbandingan bin gagal.", active === "bins" && supportsBins ? bins.error : null);

  return <Panel title="Percobaan langsung" id="percobaan-langsung">
    <p className="dim">Ubah ukuran sampel per kelas untuk membandingkan hasil pada konfigurasi CBIR aktif.</p>
    <div className="lab-fields">
      <div className="lab-field"><span className="mono dim">Citra latih per kelas · {workload.db_per_class}</span>
        <Slider className="lab-slider" aria-label="Citra latih per kelas" min={5} max={maxDatabase} value={[workload.db_per_class]}
          onValueChange={([value]) => { if (value !== undefined) setDbSize(value); }} />
      </div>
      <div className="lab-field"><span className="mono dim">Citra uji per kelas · {workload.queries_per_class}</span>
        <Slider className="lab-slider" aria-label="Citra uji per kelas" min={1} max={maxQueries} value={[workload.queries_per_class]}
          onValueChange={([value]) => { if (value !== undefined) setQueryCount(value); }} />
      </div>
    </div>
    <div className="lab-actions">
      <Button type="button" disabled={!meta || (active === "cbir" && cbir.waiting)} aria-pressed={active === "cbir"} variant={active === "cbir" ? "default" : "outline"}
        onClick={() => { if (active === "cbir") void cbir.refetch(); else setActive("cbir"); }}>Uji CBIR langsung</Button>
      <Button type="button" disabled={!supportsBins || (active === "bins" && bins.waiting)} aria-pressed={active === "bins"} variant={active === "bins" ? "default" : "outline"}
        onClick={() => { if (active === "bins") void bins.refetch(); else setActive("bins"); }}>Bandingkan jumlah bin</Button>
    </div>
    {active === "cbir" ? <RequestState pending={cbir.waiting} error={cbir.error} empty="Belum ada sampel uji.">
      {cbir.data && <Evaluation data={cbir.data} meta={meta} />}
    </RequestState> : active === "bins" && supportsBins ?
      <RequestState pending={bins.waiting} error={bins.error} empty="Belum ada hasil perbandingan bin.">
        {bins.data && <>
          <ChartRenderer spec={bins.data.chart} />
          <DataTable columns={["Bin", "Dimensi", "P@k makro", "Waktu per kueri (ms)"]}
            rows={bins.data.points.map((row) => [row.bins, row.dim, formatPercent(row.macro_precision_at_k), row.search_ms_per_query])} />
        </>}
      </RequestState> : <Empty>{active === "bins" ? "Perbandingan jumlah bin tersedia untuk mode histogram." : "Pilih salah satu pengujian."}</Empty>}
  </Panel>;
}
