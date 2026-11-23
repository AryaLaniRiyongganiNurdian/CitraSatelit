import { Button } from "@/components/ui/button";
import { Choice, NumberField, type Option } from "@/components/workbench";
import { BIN_OPTIONS, type BinCount, type FeatureMode, type ImageMeta, type MetaResponse, type Metric, type SearchRequest } from "@/types/api";

export const defaults = { mode: "rgb", bins: 32, metric: "chi2", k: 5 } satisfies MetaResponse["defaults"];
export type Criteria = Pick<SearchRequest, "mode" | "bins" | "metric">;
export type Settings = Criteria & { k: number | ""; database: "all" | "train" };

export function FeatureControls({ settings, onChange, onSubmit, meta, image, busy }: {
  settings: Settings; onChange: (settings: Settings) => void; onSubmit: () => void;
  meta: MetaResponse | undefined; image: ImageMeta | null; busy: boolean;
}) {
  const info = meta?.feature_modes.find((item) => item.mode === settings.mode);
  const moment = info?.kind === "moment";
  const modes: Option<FeatureMode>[] = meta?.feature_modes.map((item) => ({
    value: item.mode, label: item.label, disabled: Boolean(image && !image.has_ms && item.needs_multispectral),
  })) ?? [];
  const metrics: Option<Metric>[] = meta?.metrics.filter((item) => info?.metrics.includes(item.metric))
    .map((item) => ({ value: item.metric, label: item.label })) ?? [];
  const unsupported = Boolean(image && info?.needs_multispectral && !image.has_ms);

  return <form className="lab-stack" onSubmit={(event) => { event.preventDefault(); onSubmit(); }}>
    <div className="lab-fields">
      <Choice label="Mode fitur" value={settings.mode} options={modes} disabled={!modes.length} onChange={(mode) => {
        const nextMode = meta?.feature_modes.find((item) => item.mode === mode);
        if (!nextMode) return;
        onChange({ ...settings, mode, metric: nextMode.kind === "moment" ? "euclid" :
          nextMode.metrics.includes(settings.metric) ? settings.metric : nextMode.metrics[0] ?? "euclid" });
      }} />
      <Choice<BinCount> label="Jumlah bin" value={moment ? defaults.bins : settings.bins}
        options={(meta?.bins_options ?? BIN_OPTIONS).map((bin) => ({ value: bin, label: String(bin) }))}
        disabled={!info?.supports_bins} onChange={(bins) => onChange({ ...settings, bins })} />
      <Choice label="Metrik" value={moment ? "euclid" : settings.metric} options={metrics} disabled={moment || !metrics.length}
        onChange={(metric) => onChange({ ...settings, metric })} />
      <NumberField label="Jumlah hasil (k)" min={1} max={meta?.dataset.n_total || undefined} required
        value={settings.k} onChange={(event) => onChange({ ...settings, k: event.currentTarget.value === "" ? "" : event.currentTarget.valueAsNumber })} />
      <Choice label="Basis data" value={settings.database} options={[
        { value: "all", label: "Semua citra" }, { value: "train", label: "Data latih" },
      ]} onChange={(database) => onChange({ ...settings, database })} />
    </div>
    <div className="lab-actions">
      <Button type="submit" disabled={!image || !info || unsupported || busy || settings.k === ""}>Cari citra serupa</Button>
      {unsupported && <small className="dim">Mode ini membutuhkan citra multispektral.</small>}
      {moment && <small className="dim">Mode momen memakai Euclidean dan mengabaikan jumlah bin.</small>}
    </div>
  </form>;
}
